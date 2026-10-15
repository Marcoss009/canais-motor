"""Coleta pública para o /yt-viral: busca temas, pega os canais que aparecem e os últimos vídeos de cada um.

Uso: python pesquisa.py engenhoso "musica infantil cores" "aprender numeros infantil" ...
Saída: dados/<canal>/pesquisa/<data>.json no formato do swipe.py
       [{"channel","title","views","url","duration"}]
Só listagens públicas (yt-dlp --flat-playlist), nunca a conta logada.
"""
import datetime as dt
import json
import subprocess
import sys
from collections import Counter

from lib.comum import DADOS

# Sem lang=pt de propósito: em português "794 mi de visualizações" vira 794 no yt-dlp.
YTDLP = [sys.executable, "-m", "yt_dlp", "--flat-playlist", "-J", "--no-warnings"]


def ytdlp(url):
    r = subprocess.run(YTDLP + [url], capture_output=True, text=True, encoding="utf-8", timeout=300)
    if r.returncode != 0:
        return {}
    return json.loads(r.stdout)


def main():
    canal, buscas = sys.argv[1], sys.argv[2:]
    canais = Counter()
    nomes = {}
    for q in buscas:
        for e in ytdlp(f"ytsearch25:{q}").get("entries", []) or []:
            cid = e.get("channel_id")
            if cid:
                canais[cid] += 1
                nomes[cid] = e.get("channel") or e.get("uploader") or cid
    saida = []
    for cid, _ in canais.most_common(18):
        for aba in ("videos", "shorts"):
            d = ytdlp(f"https://www.youtube.com/channel/{cid}/{aba}")
            for e in (d.get("entries") or [])[:20]:
                if e.get("view_count") is None:
                    continue
                saida.append({"channel": nomes[cid] + (" [shorts]" if aba == "shorts" else ""),
                              "title": e.get("title"), "views": e["view_count"],
                              "url": e.get("url") or f"https://youtu.be/{e.get('id')}",
                              "duration": e.get("duration") or (45 if aba == "shorts" else 0)})
    pasta = DADOS / canal / "pesquisa"
    pasta.mkdir(parents=True, exist_ok=True)
    arq = pasta / f"{dt.date.today()}.json"
    arq.write_text(json.dumps(saida, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"{len(saida)} vídeos de {len(set(s['channel'] for s in saida))} listas -> {arq}")


if __name__ == "__main__":
    main()
