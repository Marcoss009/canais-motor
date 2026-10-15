"""Renderiza um episódio do SuperKids (custo zero): roteiro JSON -> voz neural -> animação SVG -> MP4.

Uso: python motor_kids/render.py episodios/ep001.json [--fila]
     --fila  registra o vídeo pronto na fila de publicação (fila/kids/<id>/)

Roteiro (ver motor_kids/exemplo.json):
  {"id","formato":"short|longo","titulo","descricao","tags":[],"nicho",
   "cenas":[{"tipo":"abertura|contar|cor|forma|animal|letra|pergunta|final", ...campos, "falas":[...]}],
   "miniatura":{"texto","objetos":[{"objeto","cor"}]}}
Cada fala vira um "passo" da cena (ex.: em 'contar', fala 1 revela o 1º objeto).
"""
import asyncio
import hashlib
import json
import shutil
import subprocess
import sys
import wave
from pathlib import Path

import numpy as np

AQUI = Path(__file__).resolve().parent
RAIZ = AQUI.parent
sys.path.insert(0, str(RAIZ))
from lib.comum import FILA, config, novo_item  # noqa: E402

SR = 24000
CACHE = AQUI / "cache_voz"
TAMANHOS = {"short": (1080, 1920, 30), "longo": (1920, 1080, 30)}
PAUSA_FALA, PAUSA_PASSO, ENTRADA, SAIDA = 0.45, 0.30, 0.35, 0.55


# ---------------- voz ----------------
async def _tts(texto, voz, destino):
    import edge_tts
    await edge_tts.Communicate(texto, voz, rate="+0%", pitch="+12Hz").save(str(destino))


def falar(texto, voz):
    """Gera (com cache) e devolve as amostras float32 mono 24 kHz."""
    CACHE.mkdir(exist_ok=True)
    h = hashlib.sha1(f"{voz}|{texto}".encode()).hexdigest()[:16]
    mp3 = CACHE / f"{h}.mp3"
    if not mp3.exists():
        for tentativa in range(3):
            try:
                asyncio.run(_tts(texto, voz, mp3))
                break
            except Exception:
                if tentativa == 2:
                    raise
    return decodificar(mp3)


def decodificar(arq):
    r = subprocess.run([config()["ffmpeg"], "-loglevel", "error", "-i", str(arq), "-f", "s16le",
                        "-ac", "1", "-ar", str(SR), "-"], capture_output=True, check=True)
    return np.frombuffer(r.stdout, dtype=np.int16).astype(np.float32) / 32768.0


# ---------------- música e efeitos (gerados, sem direitos autorais) ----------------
NOTAS = {"C": 0, "D": 2, "E": 4, "F": 5, "G": 7, "A": 9, "B": 11}


def freq(nome, oit):
    return 440.0 * 2 ** ((NOTAS[nome] + 12 * (oit - 4) - 9) / 12)


def nota(f, dur, vol, timbre="marimba"):
    t = np.arange(int(dur * SR)) / SR
    if timbre == "marimba":
        s = np.sin(2 * np.pi * f * t) + 0.25 * np.sin(2 * np.pi * f * 4 * t) * np.exp(-t * 30)
        env = np.exp(-t * 6)
    else:  # baixo
        s = np.sin(2 * np.pi * f * t)
        env = np.exp(-t * 3)
    a = min(len(t), int(0.005 * SR))
    env[:a] *= np.linspace(0, 1, a)
    return (s * env * vol).astype(np.float32)


def musica(segundos, bpm=112):
    """Loop alegre I-V-vi-IV em Dó maior, arpejo de marimba + baixo."""
    batida = 60 / bpm
    acordes = [("C", ["C", "E", "G"]), ("G", ["G", "B", "D"]), ("A", ["A", "C", "E"]), ("F", ["F", "A", "C"])]
    out = np.zeros(int((segundos + 2) * SR), dtype=np.float32)
    t, i = 0.0, 0
    padrao = [0, 1, 2, 1, 0, 2, 1, 2]
    while t < segundos:
        raiz, triade = acordes[i % 4]
        ini = int(t * SR)
        b = nota(freq(raiz, 2), batida * 4, 0.22, "baixo")
        out[ini:ini + len(b)] += b[:len(out) - ini]
        for k, p in enumerate(padrao):
            n = triade[p]
            oit = 5 if NOTAS[n] >= NOTAS[triade[0]] else 6
            s = nota(freq(n, oit), batida * 0.9, 0.12)
            st = int((t + k * batida / 2) * SR)
            if st < len(out):
                out[st:st + len(s)] += s[:len(out) - st]
        t += batida * 4
        i += 1
    return out[:int(segundos * SR)]


def efeito_pop(vol=0.35):
    t = np.arange(int(0.12 * SR)) / SR
    f = 500 + 900 * t / 0.12
    return (np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * 28) * vol).astype(np.float32)


def efeito_tada(vol=0.3):
    out = np.zeros(int(0.9 * SR), dtype=np.float32)
    for k, (n, o) in enumerate([("C", 5), ("E", 5), ("G", 5), ("C", 6)]):
        s = nota(freq(n, o), 0.7, vol)
        st = int(k * 0.08 * SR)
        out[st:st + len(s)] += s[:len(out) - st]
    return out


# ---------------- linha do tempo ----------------
def montar(ep, voz):
    """Devolve (trilha float32, eventos) onde eventos = [{cena, passo, ini, fim, fala_ini, fala_fim}]."""
    eventos, falas_audio = [], []
    t = 0.0
    for ci, cena in enumerate(ep["cenas"]):
        t += ENTRADA
        for pi, fala in enumerate(cena["falas"]):
            amostras = falar(fala, voz)
            dur = len(amostras) / SR
            eventos.append({"cena": ci, "passo": pi, "ini": t, "fala_ini": t, "fala_fim": t + dur})
            falas_audio.append((t, amostras))
            t += dur + (PAUSA_PASSO if cena["tipo"] in ("contar", "cor") and pi > 0 else PAUSA_FALA)
        t += SAIDA
        eventos.append({"cena": ci, "passo": None, "ini": t})  # marcador de fim de cena
    total = t + 0.4
    voz_tr = np.zeros(int(total * SR) + SR, dtype=np.float32)
    for ini, a in falas_audio:
        s = int(ini * SR)
        voz_tr[s:s + len(a)] += a
    # efeitos: pop quando um objeto aparece, tada no fim de contagem/pergunta
    sfx = np.zeros_like(voz_tr)
    for ev in eventos:
        if ev["passo"] is None:
            continue
        cena = ep["cenas"][ev["cena"]]
        p = ev["passo"]
        som = None
        if cena["tipo"] in ("contar", "cor") and 1 <= p <= cena.get("n", len(cena.get("objetos", [])) or 99):
            som = efeito_pop()
        elif (cena["tipo"] == "contar" and p == cena["n"] + 1) or (cena["tipo"] == "pergunta" and p == 1) \
                or (cena["tipo"] == "esconde" and p == 2):
            som = efeito_tada()
        elif cena["tipo"] == "esconde" and p == 1:
            som = efeito_pop(0.25)
        if som is not None:
            s = int(ev["ini"] * SR)
            sfx[s:s + len(som)] += som[:len(sfx) - s]
    # música com "ducking": abaixa quando tem voz
    mus = musica(total)
    mus = np.pad(mus, (0, len(voz_tr) - len(mus)))
    env = np.convolve(np.abs(voz_tr), np.ones(int(0.25 * SR)) / int(0.25 * SR), mode="same")
    duck = np.where(env > 0.01, 0.35, 1.0).astype(np.float32)
    duck = np.convolve(duck, np.ones(int(0.2 * SR)) / int(0.2 * SR), mode="same")
    mix = voz_tr * 1.0 + sfx + mus * 0.5 * duck
    mix = mix[:int(total * SR)]
    pico = np.max(np.abs(mix)) or 1
    mix = mix / pico * 0.89
    return mix, voz_tr[:int(total * SR)], eventos, total


def boca_por_quadro(voz_tr, fps, n):
    passo = SR / fps
    rms = np.array([np.sqrt(np.mean(voz_tr[int(i * passo):int((i + 1) * passo)] ** 2) + 1e-12) for i in range(n)])
    ref = np.percentile(rms[rms > 0.005], 90) if np.any(rms > 0.005) else 1
    b = np.clip(rms / ref, 0, 1)
    return np.convolve(b, [0.25, 0.5, 0.25], mode="same")


def estado_no_tempo(t, eventos):
    """Cena, passo, tempo na cena, tempo no passo e se está falando."""
    atual = None
    ini_cena = {}
    for ev in eventos:
        ini_cena.setdefault(ev["cena"], ev["ini"])
        if ev["ini"] <= t and ev["passo"] is not None:
            atual = ev
        elif ev["ini"] > t:
            break
    if atual is None:
        atual = eventos[0]
    ci = atual["cena"]
    # começo real da cena = começo da 1ª fala menos a entrada
    primeira = next(e for e in eventos if e["cena"] == ci and e["passo"] == 0)
    tc = t - (primeira["ini"] - ENTRADA)
    falando = atual["fala_ini"] <= t <= atual["fala_fim"]
    return ci, atual["passo"], max(tc, 0), max(t - atual["ini"], 0), falando


# ---------------- render ----------------
def renderizar(ep, saida_dir):
    cfg = config()
    voz = ep.get("voz") or cfg["canais"]["kids"]["voz"]
    W, H, fps = TAMANHOS[ep["formato"]]
    mix, voz_tr, eventos, total = montar(ep, voz)
    saida_dir.mkdir(parents=True, exist_ok=True)
    wav = saida_dir / "audio.wav"
    with wave.open(str(wav), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes((np.clip(mix, -1, 1) * 32767).astype(np.int16).tobytes())
    n = int(total * fps)
    bocas = boca_por_quadro(voz_tr, fps, n)
    video = saida_dir / "video.mp4"
    ff = subprocess.Popen([cfg["ffmpeg"], "-y", "-loglevel", "error", "-f", "image2pipe", "-framerate", str(fps),
                           "-i", "-", "-i", str(wav), "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "20",
                           "-preset", "medium", "-r", str(fps), "-af", "loudnorm=I=-15:TP=-1.5:LRA=11",
                           "-ar", "48000", "-c:a", "aac", "-b:a", "160k", "-shortest",
                           "-movflags", "+faststart", str(video)], stdin=subprocess.PIPE)
    from playwright.sync_api import sync_playwright
    with sync_playwright() as p:
        nav = p.chromium.launch()
        pg = nav.new_page(viewport={"width": W, "height": H})
        pg.goto((AQUI / "cena.html").as_uri())
        for f in range(n):
            t = f / fps
            ci, passo, tc, tp, falando = estado_no_tempo(t, eventos)
            st = {"W": W, "H": H, "cena": ep["cenas"][ci], "passo": passo, "tc": tc, "tp": tp,
                  "tg": t, "boca": float(bocas[f]), "falando": falando}
            pg.evaluate("s => render(s)", st)
            ff.stdin.write(pg.screenshot(type="jpeg", quality=90))
            if f % (fps * 10) == 0:
                print(f"  {t:5.1f}s / {total:.1f}s", flush=True)
        # miniatura 1280x720
        thumb = saida_dir / "thumb.png"
        pg.set_viewport_size({"width": 1280, "height": 720})
        mini = {"tipo": "miniatura", **ep.get("miniatura", {"texto": ep["titulo"][:18]})}
        pg.evaluate("s => render(s)", {"W": 1280, "H": 720, "cena": mini, "passo": 0, "tc": 9, "tp": 9,
                                       "tg": 0, "boca": 0, "falando": False})
        pg.screenshot(path=str(thumb))
        nav.close()
    ff.stdin.close()
    ff.wait()
    wav.unlink(missing_ok=True)
    return video, thumb, total


def main():
    arq = Path(sys.argv[1])
    ep = json.loads(arq.read_text(encoding="utf-8"))
    pasta = FILA / "kids" / ep["id"]
    print(f"Renderizando {ep['id']} ({ep['formato']})...")
    video, thumb, total = renderizar(ep, pasta)
    shutil.copy(arq, pasta / "roteiro.json")
    print(f"OK: {video} ({total:.1f}s)  thumb: {thumb}")
    if "--fila" in sys.argv:
        novo_item("kids", ep["id"], ep["formato"], ep["titulo"], ep["descricao"], ep.get("tags", []),
                  video, thumb, ep.get("nicho"), roteiro=str(pasta / "roteiro.json"))
        print("Registrado na fila (estado: pronto).")


if __name__ == "__main__":
    main()
