"""Folha de contato de um clipe: um quadro a cada N segundos com o tempo escrito, para o agente escolher trechos.

Uso: python motor_gta/quadros.py canais/gta6/entrada/clipe.mp4 [--cada 3]
Saída: canais/gta6/entrada/_quadros/<clipe>.jpg  +  imprime a duração e o pico de volume por trecho
"""
import json
import subprocess
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))
from lib.comum import config  # noqa: E402


def duracao(arq):
    r = subprocess.run([config()["ffprobe"], "-v", "error", "-show_entries", "format=duration", "-of", "json",
                        str(arq)], capture_output=True, text=True, check=True)
    return float(json.loads(r.stdout)["format"]["duration"])


def picos(arq, janela):
    """Volume médio (dB) por janela - explosões/batidas aparecem como picos."""
    r = subprocess.run([config()["ffmpeg"], "-hide_banner", "-i", str(arq), "-af",
                        f"asetnsamples=n={int(48000 * janela)},astats=metadata=1:reset=1,"
                        "ametadata=print:key=lavfi.astats.Overall.RMS_level", "-f", "null", "-"],
                       capture_output=True, text=True)
    vals = [float(l.split("=")[1]) for l in r.stderr.splitlines() if "RMS_level=" in l and "inf" not in l]
    return vals


def main():
    arq = Path(sys.argv[1])
    cada = float(sys.argv[sys.argv.index("--cada") + 1]) if "--cada" in sys.argv else 3.0
    dur = duracao(arq)
    out = arq.parent / "_quadros"
    out.mkdir(exist_ok=True)
    folha = out / f"{arq.stem}.jpg"
    n = int(dur // cada) + 1
    cols = 6
    fonte = "C\\:/Windows/Fonts/arialbd.ttf"
    vf = (f"fps=1/{cada},scale=320:-1,drawtext=fontfile='{fonte}':text='%{{pts\\:hms}}':x=6:y=6:"
          f"fontsize=22:fontcolor=yellow:box=1:boxcolor=black@0.6,tile={cols}x{(n + cols - 1) // cols}")
    subprocess.run([config()["ffmpeg"], "-y", "-loglevel", "error", "-i", str(arq), "-vf", vf,
                    "-frames:v", "1", str(folha)], check=True)
    print(f"{arq.name}: {dur:.1f}s -> {folha}")
    p = picos(arq, cada)
    if p:
        top = sorted(range(len(p)), key=lambda i: p[i], reverse=True)[:5]
        print("trechos mais barulhentos (início s, dB):", [(round(i * cada, 1), round(p[i], 1)) for i in sorted(top)])


if __name__ == "__main__":
    main()
