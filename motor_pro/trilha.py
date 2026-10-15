"""Trilha sonora gerada por código (sem direitos autorais, sem Content ID) + efeitos de transição.

estilos: "synthwave" (GTA, Vice City anos 80) e "ambiente" (documentário/explicador).
"""
import numpy as np

SR = 48000
NOTAS = {"C": 0, "C#": 1, "D": 2, "D#": 3, "E": 4, "F": 5, "F#": 6, "G": 7, "G#": 8, "A": 9, "A#": 10, "B": 11}


def hz(nome, oit):
    return 440.0 * 2 ** ((NOTAS[nome] + 12 * (oit - 4) - 9) / 12)


def _env(n, a, r):
    e = np.ones(n, np.float32)
    na, nr = min(n, int(a * SR)), min(n, int(r * SR))
    if na:
        e[:na] = np.linspace(0, 1, na)
    if nr:
        e[-nr:] *= np.linspace(1, 0, nr)
    return e


def _lp(x, alfa):
    """passa-baixa de um polo (deixa o timbre macio)."""
    y = np.empty_like(x)
    acc = 0.0
    for i in range(0, len(x), 4096):  # vetorizado por blocos via filtro IIR simples
        bloco = x[i:i + 4096]
        out = np.empty_like(bloco)
        for j, v in enumerate(bloco):
            acc += alfa * (v - acc)
            out[j] = acc
        y[i:i + 4096] = out
    return y


def saw(f, dur, harm=10):
    t = np.arange(int(dur * SR)) / SR
    s = np.zeros_like(t, dtype=np.float32)
    for k in range(1, harm + 1):
        s += (np.sin(2 * np.pi * f * k * t) / k).astype(np.float32)
    return s * 0.55


def seno(f, dur):
    t = np.arange(int(dur * SR)) / SR
    return np.sin(2 * np.pi * f * t).astype(np.float32)


def kick(vol=0.9):
    n = int(0.32 * SR)
    t = np.arange(n) / SR
    f = 50 + 90 * np.exp(-t * 28)
    return (np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * 9) * vol).astype(np.float32)


def caixa(vol=0.35, rng=np.random.default_rng(3)):
    n = int(0.2 * SR)
    t = np.arange(n) / SR
    return ((rng.standard_normal(n) * 0.7 + np.sin(2 * np.pi * 190 * t)) * np.exp(-t * 22) * vol).astype(np.float32)


def chimbal(vol=0.12, rng=np.random.default_rng(5)):
    n = int(0.05 * SR)
    r = rng.standard_normal(n).astype(np.float32)
    r = np.diff(r, prepend=0)  # agudo
    return r * np.exp(-np.arange(n) / SR * 90) * vol


def _soma(out, s, t):
    i = int(t * SR)
    if i >= len(out):
        return
    m = min(len(s), len(out) - i)
    out[i:i + m] += s[:m]


def gerar(estilo, segundos):
    out = np.zeros(int((segundos + 4) * SR), np.float32)
    if estilo == "synthwave":
        bpm, prog = 100, [("A", "C", "E"), ("F", "A", "C"), ("C", "E", "G"), ("G", "B", "D")]
    else:
        bpm, prog = 84, [("C", "E", "G"), ("A", "C", "E"), ("F", "A", "C"), ("G", "B", "D")]
    b = 60 / bpm
    compasso = 4 * b
    # cache de timbres por acorde (gera uma vez, repete)
    cache = {}
    for ci, acorde in enumerate(prog):
        pad = sum(saw(hz(n, 3 if estilo == "synthwave" else 4), compasso, 6) for n in acorde) * 0.12
        pad = _lp(pad, 0.06 if estilo == "synthwave" else 0.04) * _env(len(pad), 0.4, 0.5)
        baixo = []
        for k in range(8):
            s = saw(hz(acorde[0], 1 if estilo == "synthwave" else 2), b * 0.45, 5)
            baixo.append(_lp(s, 0.12) * _env(len(s), 0.005, 0.12) * 0.5)
        arp = []
        if estilo != "synthwave":
            for k in range(8):
                n = acorde[k % 3]
                s = seno(hz(n, 5), b * 0.9) * 0.6 + seno(hz(n, 6), b * 0.9) * 0.12
                arp.append(s * np.exp(-np.arange(len(s)) / SR * 5).astype(np.float32) * 0.16)
        cache[ci] = (pad, baixo, arp)
    kk, cx, hh = kick(), caixa(), chimbal()
    t, i = 0.0, 0
    while t < segundos + 2:
        pad, baixo, arp = cache[i % len(prog)]
        _soma(out, pad, t)
        intro = i < 2  # 2 compassos só de pad
        for k in range(8):
            if not intro:
                _soma(out, baixo[k] * (1 if estilo == "synthwave" else 0.6), t + k * b / 2)
                _soma(out, hh * (1 if k % 2 else 0.6), t + k * b / 2)
            if arp:
                _soma(out, arp[k], t + k * b / 2)
        if not intro:
            for k in range(4):
                if k in (0, 2):
                    _soma(out, kk * (1 if estilo == "synthwave" else 0.6), t + k * b)
                elif estilo == "synthwave":
                    _soma(out, cx, t + k * b)
        t += compasso
        i += 1
    out = out[:int(segundos * SR)]
    out *= _env(len(out), 1.5, 3.0)
    return out / (np.max(np.abs(out)) or 1)


def whoosh(dur=0.45, vol=0.22, rng=np.random.default_rng(11)):
    n = int(dur * SR)
    r = rng.standard_normal(n).astype(np.float32)
    # ruído com filtro que "abre" e fecha
    alfa = np.concatenate([np.linspace(0.02, 0.5, n // 2), np.linspace(0.5, 0.02, n - n // 2)])
    y, acc = np.empty_like(r), 0.0
    for j in range(n):
        acc += alfa[j] * (r[j] - acc)
        y[j] = acc
    return y * np.sin(np.linspace(0, np.pi, n)).astype(np.float32) * vol / (np.max(np.abs(y)) or 1)


def _media(x, j):
    """média móvel centrada em O(n) (np.convolve seria quadrático em vídeo longo)."""
    c = np.concatenate([[0.0], np.cumsum(x, dtype=np.float64)])
    i = np.arange(len(x))
    a, b = np.clip(i - j // 2, 0, len(x)), np.clip(i + j - j // 2, 0, len(x))
    return ((c[b] - c[a]) / j).astype(np.float32)


def mixar(voz, musica, cortes, vol_musica=0.16):
    """voz + música com ducking (abaixa a música quando há fala) + whoosh nas trocas de cena."""
    n = len(voz)
    musica = np.pad(musica, (0, max(0, n - len(musica))))[:n]
    # envelope da voz (janela de 50 ms), suavizado
    j = int(0.05 * SR)
    env = np.sqrt(_media(voz ** 2, j))
    fala = _media((env > 0.02).astype(np.float32), int(0.35 * SR))
    ganho = vol_musica * (1 - 0.55 * np.clip(fala, 0, 1))
    mix = voz + musica * ganho
    w = whoosh()
    for c in cortes:
        _soma(mix, w, max(0, c - 0.2))
    return mix / (np.max(np.abs(mix)) or 1) * 0.92
