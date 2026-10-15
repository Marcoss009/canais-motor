"""Shorts de texto neon + narração (pré-lançamento do GTA VI, sem gameplay). Custo zero.

Uso: python motor_gta/slides.py episodios/gta6/p001.json [--fila]
Roteiro: {"id","titulo","descricao","tags","nicho","slides":[{"fala","texto","sub","numero","selo","destaque","fonte","tam"}],
          "miniatura":{"slide":0}}
Só fatos oficiais; ponha a fonte no slide ("fonte") e na descrição.
"""
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
sys.path.insert(0, str(RAIZ / "motor_kids"))
from lib.comum import FILA, config, novo_item  # noqa: E402
from render import SR, falar, freq, nota  # noqa: E402  (voz com cache e síntese de notas)

W, H, FPS = 1080, 1920, 30


def trilha(segundos, bpm=96):
    """Synthwave simples: baixo pulsado + acordes Am-F-C-G."""
    b = 60 / bpm
    acordes = [("A", ["A", "C", "E"]), ("F", ["F", "A", "C"]), ("C", ["C", "E", "G"]), ("G", ["G", "B", "D"])]
    out = np.zeros(int((segundos + 3) * SR), dtype=np.float32)
    t, i = 0.0, 0
    while t < segundos:
        raiz, tri = acordes[i % 4]
        for k in range(8):
            s = nota(freq(raiz, 2), b * 0.45, 0.20, "baixo")
            st = int((t + k * b / 2) * SR)
            out[st:st + len(s)] += s[:len(out) - st]
        for n in tri:
            s = nota(freq(n, 4), b * 4, 0.05, "baixo")
            st = int(t * SR)
            out[st:st + len(s)] += s[:len(out) - st]
        t += b * 4
        i += 1
    return out[:int(segundos * SR)]


def main():
    arq = Path(sys.argv[1])
    ep = json.loads(arq.read_text(encoding="utf-8"))
    cfg = config()
    voz = cfg["canais"]["gta6"]["voz"]
    pasta = FILA / "gta6" / ep["id"]
    pasta.mkdir(parents=True, exist_ok=True)
    # linha do tempo
    t, blocos, faixas = 0.25, [], []
    for i, s in enumerate(ep["slides"]):
        a = falar(s["fala"], voz)
        d = len(a) / SR
        blocos.append((t, t + d + 0.35, i))
        faixas.append((t + 0.1, a))
        t += d + 0.35
    total = t + 0.3
    voz_tr = np.zeros(int(total * SR) + SR, dtype=np.float32)
    for ini, a in faixas:
        s = int(ini * SR)
        voz_tr[s:s + len(a)] += a
    mus = np.pad(trilha(total), (0, len(voz_tr) - int(total * SR)))
    mix = voz_tr * 1.1 + mus * 0.35
    mix = (mix / (np.max(np.abs(mix)) or 1) * 0.89)[:int(total * SR)]
    wav = pasta / "audio.wav"
    with wave.open(str(wav), "wb") as w:
        w.setnchannels(1), w.setsampwidth(2), w.setframerate(SR)
        w.writeframes((mix * 32767).astype(np.int16).tobytes())
    video = pasta / "video.mp4"
    ff = subprocess.Popen([cfg["ffmpeg"], "-y", "-loglevel", "error", "-f", "image2pipe", "-framerate", str(FPS),
                           "-i", "-", "-i", str(wav), "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "20",
                           "-preset", "medium", "-af", "loudnorm=I=-14:TP=-1.5:LRA=11", "-ar", "48000",
                           "-c:a", "aac", "-b:a", "160k", "-shortest", "-movflags", "+faststart", str(video)],
                          stdin=subprocess.PIPE)
    from playwright.sync_api import sync_playwright
    with sync_playwright() as p:
        nav = p.chromium.launch()
        pg = nav.new_page(viewport={"width": W, "height": H})
        pg.goto((AQUI / "slides.html").as_uri())
        for f in range(int(total * FPS)):
            tt = f / FPS
            ini, fim, i = next((b for b in blocos if b[0] <= tt < b[1]), blocos[-1])
            pg.evaluate("s => render(s)", {"W": W, "H": H, "slide": ep["slides"][i], "tg": tt,
                                           "ts": tt - ini, "tf": (tt - ini) / (fim - ini)})
            ff.stdin.write(pg.screenshot(type="jpeg", quality=90))
        # miniatura (1280x720) a partir do slide escolhido
        pg.set_viewport_size({"width": 1280, "height": 720})
        sl = ep["slides"][ep.get("miniatura", {}).get("slide", 0)]
        pg.evaluate("s => render(s)", {"W": 1280, "H": 720, "slide": {**sl, "fonte": None}, "tg": 1,
                                       "ts": 3, "tf": 1})
        pg.screenshot(path=str(pasta / "thumb.png"))
        nav.close()
    ff.stdin.close()
    ff.wait()
    wav.unlink(missing_ok=True)
    shutil.copy(arq, pasta / "roteiro.json")
    print(f"OK: {video} ({total:.1f}s)")
    if "--fila" in sys.argv:
        novo_item("gta6", ep["id"], "short", ep["titulo"], ep["descricao"], ep.get("tags", []),
                  video, pasta / "thumb.png", ep.get("nicho"), roteiro=str(pasta / "roteiro.json"))
        print("Registrado na fila (estado: pronto).")


if __name__ == "__main__":
    main()
