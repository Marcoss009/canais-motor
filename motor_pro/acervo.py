"""Acervo de cenas OFICIAIS (trailers e vídeos publicados pelos próprios donos: Rockstar, Netflix, NASA...).

Regras (uso em comentário/crítica, art. 46 III da Lei 9.610 e fair use):
  - só baixa de canal da lista acervo/fontes_oficiais.json (ou canal verificado, com justificativa)
  - trechos de no máximo 6 s, SEM o áudio original (narração e trilha são nossas)
  - no máximo 45% do vídeo com cena oficial; crédito na tela e na descrição
  - vazamento, gameplay de terceiros e reupload de trailer inteiro: proibidos

Uso:
  python motor_pro/acervo.py listar gta6                      # últimos vídeos dos canais oficiais do canal
  python motor_pro/acervo.py baixar gta6 <url-ou-id>          # baixa (só vídeo) + folha de quadros
  python motor_pro/acervo.py folha <id>                       # refaz a folha de quadros (a cada 2 s)
  python motor_pro/acervo.py cortar <id> <inicio> <dur>       # gera o trecho (o render.py chama sozinho)
"""
import json
import os
import re
import subprocess
import sys
from pathlib import Path

AQUI = Path(__file__).resolve().parent
RAIZ = AQUI.parent
sys.path.insert(0, str(RAIZ))
from lib.comum import config  # noqa: E402

ACERVO = RAIZ / "acervo"
MAX_TRECHO = 6.0
YTDLP = [sys.executable, "-m", "yt_dlp", "--no-warnings"]


def fontes():
    return json.loads((ACERVO / "fontes_oficiais.json").read_text(encoding="utf-8"))


def ff():
    return config()["ffmpeg"]


def _repo():
    return os.environ.get("GITHUB_REPOSITORY") or config().get("repo_github")


def _gh(*args):
    """gh CLI (local: login do dono; nuvem: GITHUB_TOKEN). Devolve True se deu certo."""
    import shutil as _sh
    gh = _sh.which("gh")
    if not gh or not _repo():
        return False
    r = subprocess.run([gh, *args, "-R", _repo()], capture_output=True, text=True, encoding="utf-8")
    return r.returncode == 0


def publicar_no_release(p):
    """Guarda o vídeo oficial no release 'acervo' do GitHub (a nuvem busca de lá; o YouTube costuma barrar
    download a partir de servidores)."""
    nome = f"{p.parent.name}__{p.name}.mp4"
    tmp = p / nome
    if not (p / "video.mp4").exists():
        return False
    shutil_copy = __import__("shutil").copyfile
    shutil_copy(p / "video.mp4", tmp)
    _gh("release", "create", "acervo", "--title", "Acervo de cenas oficiais", "--notes",
        "Vídeos oficiais (só vídeo, sem áudio) usados em trechos curtos de comentário. Não é redistribuição.")
    ok = _gh("release", "upload", "acervo", str(tmp), "--clobber")
    tmp.unlink(missing_ok=True)
    return ok


def garantir_video(p):
    """Na nuvem o vídeo não vem no repositório: busca no release 'acervo'."""
    if (p / "video.mp4").exists():
        return
    nome = f"{p.parent.name}__{p.name}.mp4"
    if _gh("release", "download", "acervo", "-p", nome, "-D", str(p), "--clobber") and (p / nome).exists():
        (p / nome).rename(p / "video.mp4")
        return
    url = json.loads((p / "info.json").read_text(encoding="utf-8")).get("webpage_url")
    subprocess.run(YTDLP + ["-f", "bv*[vcodec^=avc1][height<=1080]/bv*[height<=1080]", "-o", str(p / "video.%(ext)s"),
                            "--remux-video", "mp4", url], check=True, capture_output=True)


def pasta(vid):
    for p in ACERVO.glob(f"*/{vid}"):
        if (p / "info.json").exists():
            return p
    raise SystemExit(f"vídeo {vid} não está no acervo (rode: acervo.py baixar <canal> {vid})")


def listar(canal):
    out = []
    for f in fontes()[canal]:
        try:
            r = subprocess.run(YTDLP + ["--flat-playlist", "-J", "--playlist-items", "1-15", f"{f['url']}/videos"],
                               capture_output=True, text=True, encoding="utf-8", timeout=90)
        except subprocess.TimeoutExpired:
            print(f"  {f['nome']}: demorou demais, pulei")
            continue
        d = json.loads(r.stdout or "{}")
        for e in (d.get("entries") or [])[:15]:
            out.append({"fonte": f["nome"], "id": e["id"], "titulo": e.get("title"), "views": e.get("view_count"),
                        "no_acervo": any(ACERVO.glob(f"*/{e['id']}/video.mp4"))})
    for o in out:
        print(f"{o['id']}  {'[acervo] ' if o['no_acervo'] else ''}{o['fonte']}: {o['titulo']} ({o['views'] or 0:,} views)")
    return out


def baixar(canal, url):
    if not url.startswith("http"):
        url = f"https://www.youtube.com/watch?v={url}"
    r = subprocess.run(YTDLP + ["-J", "--skip-download", url], capture_output=True, text=True, encoding="utf-8",
                       timeout=180)
    if r.returncode != 0:
        msg = (r.stderr or "").strip().splitlines()[-1:] or ["?"]
        raise SystemExit(f"não consegui ler o vídeo: {msg[0]}  (restrição de idade/região = pule este vídeo)")
    info = json.loads(r.stdout)
    oficiais = {f["channel_id"]: f["nome"] for f in fontes().get(canal, [])}
    if info.get("channel_id") not in oficiais:
        raise SystemExit(f"RECUSADO: '{info.get('channel')}' ({info.get('channel_id')}) não está em "
                         f"acervo/fontes_oficiais.json para '{canal}'. Só canal oficial do dono do conteúdo.")
    destino = ACERVO / canal / info["id"]
    destino.mkdir(parents=True, exist_ok=True)
    if not (destino / "video.mp4").exists():
        subprocess.run(YTDLP + ["-f", "bv*[vcodec^=avc1][height<=1080]/bv*[height<=1080]", "-o",
                                str(destino / "video.%(ext)s"), "--remux-video", "mp4", url], check=True,
                       capture_output=True)
    meta = {k: info.get(k) for k in ("id", "title", "channel", "channel_id", "upload_date", "duration",
                                      "webpage_url", "description")}
    meta["fonte"] = oficiais[info["channel_id"]]
    meta["description"] = (meta.get("description") or "")[:1500]
    (destino / "info.json").write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
    folha(info["id"])
    if publicar_no_release(destino):
        print("  guardado no release 'acervo' do GitHub (a nuvem usa de lá)")
    print(f"OK {destino}  ({meta['fonte']}: {meta['title']}, {meta['duration']} s)")
    print(f"Folha de quadros: {destino / 'folha.jpg'}")
    return destino


def folha(vid, passo=2.0):
    """Folha de contato com o tempo de cada quadro, para o curador escolher as cenas."""
    from PIL import Image, ImageDraw
    p = pasta(vid)
    tmp = p / "_quadros"
    tmp.mkdir(exist_ok=True)
    for f in tmp.glob("*.jpg"):
        f.unlink()
    subprocess.run([ff(), "-v", "error", "-i", str(p / "video.mp4"), "-vf", f"fps=1/{passo},scale=320:-2",
                    str(tmp / "q%04d.jpg")], check=True)
    qs = sorted(tmp.glob("q*.jpg"))
    cols, tw, th = 8, 320, 180
    linhas = (len(qs) + cols - 1) // cols
    img = Image.new("RGB", (cols * tw, linhas * (th + 18)), "white")
    d = ImageDraw.Draw(img)
    for i, q in enumerate(qs):
        x, y = i % cols * tw, i // cols * (th + 18)
        im = Image.open(q)
        im.thumbnail((tw - 2, th))
        img.paste(im, (x + 1, y))
        t = i * passo + passo / 2  # o filtro fps pega o quadro do meio de cada intervalo
        d.text((x + 4, y + th + 2), f"{int(t // 60)}:{t % 60:04.1f}  ({t:.0f}s)", fill="black")
    img.save(p / "folha.jpg", quality=82)
    for q in qs:
        q.unlink()
    tmp.rmdir()
    return p / "folha.jpg"


def _corte_tarjas(video, ini):
    """Detecta as tarjas pretas (formato cinema) para recortar."""
    r = subprocess.run([ff(), "-v", "info", "-ss", str(ini), "-t", "3", "-i", str(video), "-vf",
                        "cropdetect=24:2:0", "-f", "null", "-"], capture_output=True, text=True,
                       encoding="utf-8", errors="replace")
    achados = re.findall(r"crop=(\d+):(\d+):(\d+):(\d+)", r.stderr)
    return achados[-1] if achados else None


def cortar(vid, ini, dur):
    """Trecho de até 6 s, sem áudio, sem tarjas, 1920x1080 (cover). Devolve (arquivo, info)."""
    p = pasta(vid)
    info = json.loads((p / "info.json").read_text(encoding="utf-8"))
    ini, dur = float(ini), min(float(dur), MAX_TRECHO)
    if not (p / "trechos" / f"{ini:07.2f}_{dur:.2f}.mp4").exists():
        garantir_video(p)
    saida = p / "trechos" / f"{ini:07.2f}_{dur:.2f}.mp4"
    if not saida.exists():
        saida.parent.mkdir(exist_ok=True)
        vf = []
        c = _corte_tarjas(p / "video.mp4", ini)
        if c and int(c[1]) < 1000:  # tem tarja: recorta a área útil
            vf.append(f"crop={c[0]}:{c[1]}:{c[2]}:{c[3]}")
        vf += ["scale=1920:1080:force_original_aspect_ratio=increase", "crop=1920:1080", "fps=30"]
        subprocess.run([ff(), "-v", "error", "-y", "-ss", f"{ini:.2f}", "-t", f"{dur:.2f}", "-i", str(p / "video.mp4"),
                        "-an", "-vf", ",".join(vf), "-c:v", "libx264", "-crf", "17", "-preset", "veryfast",
                        "-pix_fmt", "yuv420p", str(saida)], check=True)
    return saida, info


if __name__ == "__main__":
    a = sys.argv[1:]
    if not a:
        print(__doc__)
    elif a[0] == "listar":
        listar(a[1])
    elif a[0] == "baixar":
        baixar(a[1], a[2])
    elif a[0] == "folha":
        print(folha(a[1]))
    elif a[0] == "cortar":
        print(cortar(a[1], a[2], a[3])[0])
