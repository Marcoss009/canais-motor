"""Estúdio de voz grátis: voz neural (edge-tts, sem custo) + timbre próprio de cada canal (cadeia ffmpeg).

A "persona" de cada canal fica em config.json -> canais.<canal>.persona:
  {"voz": "pt-BR-AntonioNeural", "rate": "+6%", "pitch": "-2Hz", "timbre": "trailer"}

Marcas aceitas no texto da fala (o roteiro do guia usa):
  [pausa]        respiro de 0,45 s
  [pausa longa]  silêncio de 0,9 s (antes de uma revelação)
  qualquer outra [marca] é ignorada na fala

narrar(falas, persona) -> (audio float32 mono 48 kHz, [(ini, fim) de cada fala], [(ini, fim, palavra)])
"""
import asyncio
import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path

import numpy as np

AQUI = Path(__file__).resolve().parent
sys.path.insert(0, str(AQUI.parent))
from lib.comum import config  # noqa: E402

SR = 48000
CACHE = AQUI / "cache_voz"
PAUSAS = {"pausa": 0.45, "pausa longa": 0.75}
ENTRE_FALAS = 0.32

# Timbres: acabamento de estúdio leve. SEM mudança de tom (rubberband): era o que deixava a voz metálica/robótica.
# O tom vem da própria voz neural (parâmetro pitch da persona). Todos preservam a duração.
TIMBRES = {
    # presença de rádio, compressão moderada - narrador gamer
    "trailer": ("highpass=f=60,equalizer=f=140:t=q:w=1:g=1.5,equalizer=f=3000:t=q:w=1.2:g=1.2,"
                "deesser=i=0.25,acompressor=threshold=-20dB:ratio=2.2:attack=8:release=140:makeup=1.6"),
    # quente e próximo, compressão suave - documentário/explicador
    "doc": ("highpass=f=65,equalizer=f=200:t=q:w=1:g=1.2,equalizer=f=2800:t=q:w=1.2:g=0.8,deesser=i=0.2,"
            "acompressor=threshold=-20dB:ratio=1.8:attack=10:release=160:makeup=1.3"),
    "limpo": "highpass=f=60,acompressor=threshold=-20dB:ratio=1.8:attack=10:release=150:makeup=1.2",
}


async def _tts(texto, voz, rate, pitch, mp3):
    import edge_tts
    palavras = []
    com = edge_tts.Communicate(texto, voz, rate=rate, pitch=pitch, boundary="WordBoundary")
    with open(mp3, "wb") as f:
        async for ch in com.stream():
            if ch["type"] == "audio":
                f.write(ch["data"])
            elif ch["type"] == "WordBoundary":
                ini = ch["offset"] / 1e7
                palavras.append((ini, ini + ch["duration"] / 1e7, ch["text"]))
    return palavras


def decodificar(arq, filtro=None):
    cmd = [config()["ffmpeg"], "-loglevel", "error", "-i", str(arq)]
    if filtro:
        cmd += ["-af", filtro]
    r = subprocess.run(cmd + ["-f", "s16le", "-ac", "1", "-ar", str(SR), "-"], capture_output=True, check=True)
    return np.frombuffer(r.stdout, dtype=np.int16).astype(np.float32) / 32768.0


def _trecho(texto, p):
    """Sintetiza (com cache) um trecho sem marcas. Devolve (amostras, palavras relativas)."""
    CACHE.mkdir(exist_ok=True)
    chave = f"{p['voz']}|{p.get('rate', '+0%')}|{p.get('pitch', '+0Hz')}|{texto}"
    h = hashlib.sha1(chave.encode()).hexdigest()[:16]
    mp3, js = CACHE / f"{h}.mp3", CACHE / f"{h}.json"
    if not (mp3.exists() and js.exists()):
        for tentativa in range(4):
            try:
                pal = asyncio.run(asyncio.wait_for(
                    _tts(texto, p["voz"], p.get("rate", "+0%"), p.get("pitch", "+0Hz"), mp3), timeout=45))
                js.write_text(json.dumps(pal, ensure_ascii=False), encoding="utf-8")
                break
            except Exception as e:  # inclui conexão pendurada (timeout)
                print(f"  voz: tentativa {tentativa + 1} falhou ({type(e).__name__})")
                if tentativa == 3:
                    raise
    return decodificar(mp3), json.loads(js.read_text(encoding="utf-8"))


def partes(fala):
    """'a [pausa] b [pausa longa] c' -> [('fala', 'a… b'), ('pausa', 0.75), ('fala', 'c')]

    A cena inteira é falada numa tirada só (entonação natural); [pausa] vira reticências, que a voz neural
    respeita. Só [pausa longa] corta a frase e insere silêncio de verdade (efeito dramático)."""
    out = []
    for pedaco in re.split(r"(\[\s*pausa longa\s*\])", fala, flags=re.I):
        if re.fullmatch(r"\[\s*pausa longa\s*\]", pedaco.strip(), flags=re.I):
            out.append(("pausa", PAUSAS["pausa longa"]))
            continue
        txt = re.sub(r"\s*\[\s*pausa\s*\]\s*", "… ", pedaco, flags=re.I)
        txt = re.sub(r"\[[^\]]*\]", "", txt)  # outras marcas não são faladas
        txt = re.sub(r"\s+", " ", txt).strip()
        txt = re.sub(r"([.!?,;:])…", lambda m: m.group(1), txt)  # "frase.… outra" -> "frase. outra"
        if txt:
            out.append(("fala", txt))
    return out


def texto_limpo(fala):
    return " ".join(t for k, t in partes(fala) if k == "fala")


def narrar(falas, persona):
    pedacos, tempos, palavras = [], [], []
    t = 0.35
    pedacos.append(np.zeros(int(t * SR), np.float32))
    for fala in falas:
        ini = t
        for tipo, val in partes(fala):
            if tipo == "pausa":
                pedacos.append(np.zeros(int(val * SR), np.float32))
                t += val
                continue
            a, pal = _trecho(val, persona)
            # corta o silêncio que o edge-tts deixa no fim, mantendo 60 ms
            fim_util = (pal[-1][1] + 0.06) if pal else len(a) / SR
            a = a[:int(min(len(a) / SR, fim_util) * SR)]
            palavras += [(t + i, t + f, w) for i, f, w in pal]
            pedacos.append(a)
            t += len(a) / SR
        tempos.append((ini, t))
        pedacos.append(np.zeros(int(ENTRE_FALAS * SR), np.float32))
        t += ENTRE_FALAS
    pedacos.append(np.zeros(int(0.6 * SR), np.float32))
    bruto = np.concatenate(pedacos)
    return masterizar(bruto, persona.get("timbre", "limpo")), tempos, palavras


def masterizar(a, timbre):
    """Aplica o timbre do canal (duração preservada)."""
    import tempfile
    filtro = TIMBRES.get(timbre, TIMBRES["limpo"])
    with tempfile.TemporaryDirectory() as d:
        ent = Path(d) / "v.wav"
        salvar_wav(ent, a)
        out = decodificar(ent, filtro)
    if len(out) < len(a):
        out = np.pad(out, (0, len(a) - len(out)))
    return out[:len(a)]


def salvar_wav(arq, a, canais=1):
    import wave
    a = np.clip(a, -1, 1)
    with wave.open(str(arq), "wb") as w:
        w.setnchannels(canais)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes((a * 32767).astype(np.int16).tobytes())


if __name__ == "__main__":
    # amostra: python motor_pro/voz.py gta6 "texto [pausa] mais texto" saida.wav
    canal, texto, saida = sys.argv[1], sys.argv[2], sys.argv[3]
    a, _, _ = narrar([texto], config()["canais"][canal]["persona"])
    salvar_wav(saida, a)
    print("OK", saida, f"{len(a) / SR:.1f}s")
