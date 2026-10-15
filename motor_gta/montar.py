"""Monta um vídeo do GTAzando a partir dos clipes do PS5 (custo zero, sem a sua voz).

Uso: python motor_gta/montar.py episodios/gta6/g001.json [--fila]

Roteiro:
  {"id","formato":"short|longo","titulo","descricao","tags","nicho",
   "gancho": "TEXTO GRANDE DOS 2 PRIMEIROS SEGUNDOS",
   "trechos": [{"arquivo":"canais/gta6/entrada/x.mp4","ini":12.0,"fim":19.5,
                "texto":"legenda curta na tela","narracao":"fala da voz de IA (opcional)"}],
   "miniatura": {"tempo": [indice_trecho, segundo], "texto": "ATÉ 3 PALAVRAS"}}
Short = 1080x1920 (jogo no meio, fundo desfocado). Longo = 1920x1080.
Áudio: som do jogo; com narração o jogo abaixa para 25%. Grave com a RÁDIO DESLIGADA (música gera claim).
"""
import asyncio
import hashlib
import json
import shutil
import subprocess
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))
from lib.comum import FILA, config, novo_item  # noqa: E402

FONTE = "C\\:/Windows/Fonts/ariblk.ttf"
CACHE = Path(__file__).resolve().parent / "cache_voz"


def ff(*args):
    subprocess.run([config()["ffmpeg"], "-y", "-loglevel", "error", *map(str, args)], check=True)


def duracao(arq):
    r = subprocess.run([config()["ffprobe"], "-v", "error", "-show_entries", "format=duration", "-of", "json",
                        str(arq)], capture_output=True, text=True, check=True)
    return float(json.loads(r.stdout)["format"]["duration"])


def narrar(texto, voz):
    import edge_tts
    CACHE.mkdir(exist_ok=True)
    arq = CACHE / (hashlib.sha1(f"{voz}|{texto}".encode()).hexdigest()[:16] + ".mp3")
    if not arq.exists():
        asyncio.run(edge_tts.Communicate(texto, voz, rate="+8%").save(str(arq)))
    return arq


def quebrar(texto, max_c):
    linhas, atual = [], ""
    for p in texto.split():
        if len(atual) + len(p) + 1 > max_c and atual:
            linhas.append(atual)
            atual = p
        else:
            atual = f"{atual} {p}".strip()
    return "\n".join(linhas + [atual])


def texto_arq(pasta, nome, texto):
    a = pasta / nome
    a.write_text(texto, encoding="utf-8")
    return str(a).replace("\\", "/").replace(":", "\\:")


def trecho(t, i, ep, pasta, voz):
    short = ep["formato"] == "short"
    W, H = (1080, 1920) if short else (1920, 1080)
    ini, fim = float(t["ini"]), float(t["fim"])
    dur = fim - ini
    src = RAIZ / t["arquivo"]
    filtros = []
    if short:
        filtros.append(f"[0:v]split[a][b];[a]scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H},"
                       f"boxblur=24:2,eq=brightness=-0.15[fundo];[b]scale={W}:-2[jogo];"
                       f"[fundo][jogo]overlay=0:(H-h)/2[v0]")
    else:
        filtros.append(f"[0:v]scale={W}:{H}:force_original_aspect_ratio=decrease,"
                       f"pad={W}:{H}:(ow-iw)/2:(oh-ih)/2[v0]")
    ult = "v0"
    tam = 74 if short else 64
    if i == 0 and ep.get("gancho"):
        g = texto_arq(pasta, f"gancho.txt", quebrar(ep["gancho"].upper(), 16 if short else 28))
        y = "h*0.12" if short else "h*0.08"
        filtros.append(f"[{ult}]drawtext=fontfile='{FONTE}':textfile='{g}':fontsize={tam + 22}:fontcolor=#FFD400:"
                       f"borderw=8:bordercolor=black:x=(w-tw)/2:y={y}:line_spacing=-6:text_align=C:enable='lt(t,2.6)'[vg]")
        ult = "vg"
    if t.get("texto"):
        tx = texto_arq(pasta, f"t{i}.txt", quebrar(t["texto"].upper(), 18 if short else 34))
        y = "h*0.74" if short else "h*0.80"
        quando = "gte(t,2.6)" if i == 0 and ep.get("gancho") else "gte(t,0)"
        filtros.append(f"[{ult}]drawtext=fontfile='{FONTE}':textfile='{tx}':fontsize={tam}:fontcolor=white:"
                       f"borderw=7:bordercolor=black:x=(w-tw)/2:y={y}:line_spacing=-6:text_align=C:enable='{quando}'[vt]")
        ult = "vt"
    entradas = ["-ss", ini, "-t", dur, "-i", src]
    if t.get("narracao"):
        n = narrar(t["narracao"], voz)
        entradas += ["-i", n]
        filtros.append("[0:a]volume=0.25[jogo_a];[1:a]adelay=150|150,volume=1.6[voz];"
                       "[jogo_a][voz]amix=inputs=2:duration=first:normalize=0[a]")
    else:
        filtros.append("[0:a]volume=1.0[a]")
    saida = pasta / f"_trecho{i:02d}.mp4"
    ff(*entradas, "-filter_complex", ";".join(filtros), "-map", f"[{ult}]", "-map", "[a]",
       "-r", 30, "-c:v", "libx264", "-crf", 20, "-preset", "medium", "-pix_fmt", "yuv420p",
       "-c:a", "aac", "-ar", 48000, "-ac", 2, "-b:a", "160k", saida)
    return saida


def montar(ep, pasta):
    voz = config()["canais"]["gta6"]["voz"]
    pasta.mkdir(parents=True, exist_ok=True)
    partes = [trecho(t, i, ep, pasta, voz) for i, t in enumerate(ep["trechos"])]
    lista = pasta / "_lista.txt"
    lista.write_text("".join(f"file '{p.name}'\n" for p in partes), encoding="utf-8")
    video = pasta / "video.mp4"
    ff("-f", "concat", "-safe", 0, "-i", lista, "-af", "loudnorm=I=-14:TP=-1.5:LRA=11", "-c:v", "copy",
       "-c:a", "aac", "-ar", 48000, "-b:a", "160k", "-movflags", "+faststart", video)
    # miniatura: quadro escolhido + texto grande
    mi = ep.get("miniatura", {})
    ti, seg = mi.get("tempo", [0, 1.0])
    t0 = ep["trechos"][ti]
    thumb = pasta / "thumb.jpg"
    txt = texto_arq(pasta, "thumb.txt", quebrar(mi.get("texto", ep["titulo"][:20]).upper(), 14))
    ff("-ss", float(t0["ini"]) + seg, "-i", RAIZ / t0["arquivo"], "-frames:v", 1, "-vf",
       f"scale=1280:720:force_original_aspect_ratio=increase,crop=1280:720,eq=saturation=1.35:contrast=1.1,"
       f"drawtext=fontfile='{FONTE}':textfile='{txt}':fontsize=110:fontcolor=#FFD400:borderw=10:"
       f"bordercolor=black:x=40:y=h-th-50:line_spacing=6", thumb)
    for p in partes + [lista] + list(pasta.glob("*.txt")):
        p.unlink(missing_ok=True)
    return video, thumb


def main():
    arq = Path(sys.argv[1])
    ep = json.loads(arq.read_text(encoding="utf-8"))
    pasta = FILA / "gta6" / ep["id"]
    video, thumb = montar(ep, pasta)
    shutil.copy(arq, pasta / "roteiro.json")
    print(f"OK: {video} ({duracao(video):.1f}s)  thumb: {thumb}")
    if "--fila" in sys.argv:
        novo_item("gta6", ep["id"], ep["formato"], ep["titulo"], ep["descricao"], ep.get("tags", []),
                  video, thumb, ep.get("nicho"), roteiro=str(pasta / "roteiro.json"))
        print("Registrado na fila (estado: pronto).")


if __name__ == "__main__":
    main()
