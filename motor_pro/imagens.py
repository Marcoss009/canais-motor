"""Imagens grátis e liberadas, com crédito automático na descrição.

Fontes, nesta ordem:
  1. Wikimedia Commons (sem chave, sem limite apertado) - só CC0, domínio público e CC BY (sem "SA"/"ND"/"NC")
  2. Openverse (reserva; anônimo = 20 buscas/min e 200/dia) - CC0, domínio público e CC BY

buscar(consulta, usados) -> {"id", "arquivo", "credito"} ou None
Arquivo local (gameplay do PS5, print próprio): consulta "arquivo:C:/caminho/foto.jpg".
"""
import hashlib
import html
import json
import re
import time
import urllib.parse
import urllib.request
from pathlib import Path

AQUI = Path(__file__).resolve().parent
CACHE = AQUI / "cache_img"
UA = {"User-Agent": "AgentesDeCanal/1.0 (canal do YouTube; imagens com credito)"}

# nada de conteúdo adulto, violência real, armas, política ou drogas
BLOQUEIO = {"sexy", "nude", "naked", "nudity", "strip", "stripper", "gentlemen", "adult", "erotic", "bikini",
            "lingerie", "playboy", "madonna", "sinful", "xxx", "porn", "hooters", "soldier", "soldiers",
            "military", "army", "gun", "guns", "rifle", "weapon", "war", "blood", "dead", "corpse", "accident",
            "crash", "police", "arrest", "protest", "trump", "biden", "bolsonaro", "lula", "nazi", "drugs",
            "cocaine", "marijuana", "cannabis", "beer", "drunk", "funeral", "victim", "killed", "officer", "officers", "trooper", "sheriff", "patrol", "mugshot", "ceremony", "inauguration", "president", "minister", "governor",
            "mayor", "politician", "senator", "wedding", "portrait"}
VAZIAS = {"the", "a", "of", "in", "and", "at", "on", "de", "da", "do", "view", "old", "with"}


def _get(url):
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=40) as r:
        return r.read()


def _cache_json(nome, gerar):
    CACHE.mkdir(exist_ok=True)
    js = CACHE / f"{nome}_{hashlib.sha1(nome.encode()).hexdigest()[:4]}.json"
    if js.exists():
        return json.loads(js.read_text(encoding="utf-8"))
    res = gerar()
    if res is not None:
        js.write_text(json.dumps(res, ensure_ascii=False), encoding="utf-8")
    return res or []


def _limpa(txt):
    return html.unescape(re.sub(r"<[^>]+>", "", txt or "")).strip()


def _licenca_ok(lic):
    lic = (lic or "").upper()
    if any(x in lic for x in ("SA", "ND", "NC", "GFDL", "FAIR")):
        return None
    if "CC0" in lic or "PUBLIC DOMAIN" in lic or lic.startswith("PD"):
        return "domínio público" if "CC0" not in lic else "CC0"
    if lic.startswith("CC BY"):
        return lic.replace("CC BY", "CC BY").strip()
    return None


# ---------------- Wikimedia Commons ----------------
def commons(consulta):
    def gerar():
        paginas = []
        for offset in (0, 50, 100):
            qs = urllib.parse.urlencode({
                "action": "query", "format": "json", "generator": "search", "gsrnamespace": 6,
                "gsrsearch": f"{consulta} filetype:bitmap", "gsrlimit": 50, "gsroffset": offset,
                "prop": "imageinfo", "iiprop": "url|size|extmetadata|mime", "iiurlwidth": 1920})
            try:
                d = json.loads(_get(f"https://commons.wikimedia.org/w/api.php?{qs}"))
            except Exception as e:
                print("  commons falhou:", e)
                break
            for pg in d.get("query", {}).get("pages", {}).values():
                pg["index"] = pg.get("index", 99) + offset
                paginas.append(pg)
            if "continue" not in d:
                break
        if not paginas:
            return None
        d = {"query": {"pages": {str(i): pg for i, pg in enumerate(paginas)}}}
        out = []
        for p in sorted(d.get("query", {}).get("pages", {}).values(), key=lambda x: x.get("index", 99)):
            ii = (p.get("imageinfo") or [{}])[0]
            m = ii.get("extmetadata", {})
            lic = _licenca_ok(m.get("LicenseShortName", {}).get("value"))
            if not lic or ii.get("mime") not in ("image/jpeg", "image/png"):
                continue
            if ii.get("width", 0) < 1000 or ii.get("height", 0) < 560 or ii["width"] < ii["height"]:
                continue
            titulo = re.sub(r"^File:|\.\w+$", "", p["title"])
            desc = _limpa(m.get("ImageDescription", {}).get("value"))[:300]
            cats = _limpa(m.get("Categories", {}).get("value"))
            out.append({"id": "c" + str(p["pageid"]), "url": ii.get("thumburl") or ii["url"], "titulo": titulo,
                        "texto": f"{titulo} {desc} {cats}", "autor": _limpa(m.get("Artist", {}).get("value"))[:80],
                        "licenca": lic, "fonte": "Wikimedia Commons"})
        return out
    return _cache_json("c_" + re.sub(r"\W+", "_", consulta.lower())[:60], gerar)


# ---------------- Openverse (reserva) ----------------
def openverse(consulta):
    def gerar():
        qs = urllib.parse.urlencode({"q": consulta, "license": "cc0,pdm,by", "page_size": 40,
                                     "aspect_ratio": "wide", "mature": "false"})
        for espera in (0, 20, 45):
            time.sleep(espera)
            try:
                d = json.loads(_get(f"https://api.openverse.org/v1/images/?{qs}"))
                time.sleep(3.2)  # 20/min
                break
            except Exception as e:
                print(f"  openverse: {e}")
                if getattr(e, "code", None) in (401, 403):  # bloqueou o anônimo: não insiste
                    return None
        else:
            return None
        nomes = {"cc0": "CC0", "pdm": "domínio público", "by": "CC BY"}
        return [{"id": r["id"], "url": r["url"], "titulo": r.get("title") or "foto",
                 "texto": (r.get("title") or "") + " " + " ".join(t.get("name", "") for t in r.get("tags") or []),
                 "autor": (r.get("creator") or "")[:80], "licenca": nomes.get(r["license"], r["license"].upper()),
                 "fonte": r.get("source", "Openverse")}
                for r in d.get("results", []) if (r.get("width") or 0) >= 1000 and (r.get("height") or 0) >= 560
                and not r.get("mature")]
    return _cache_json("o_" + re.sub(r"\W+", "_", consulta.lower())[:60], gerar)


def _palavras(txt):
    return set(w.strip(".,:;!?()[]\"'").lower() for w in re.split(r"[\s_\-/]+", txt))


def relevantes(consulta, res):
    """Ordena por quantas palavras da busca aparecem no título/descrição; descarta o que não bate ou é bloqueado."""
    alvo = [w for w in consulta.lower().split() if w not in VAZIAS]
    nota = []
    for pos, r in enumerate(res):
        ws = _palavras(r["texto"])
        if ws & BLOQUEIO:
            continue
        acertos = sum(1 for w in alvo if w in ws or any(x.startswith(w) for x in ws))
        if acertos >= max(1, (len(alvo) + 1) // 2):
            nota.append((-acertos, pos, r))
    return [r for _, _, r in sorted(nota, key=lambda x: (x[0], x[1]))]


def buscar(consulta, usados=()):
    if consulta.startswith("arquivo:"):
        return {"arquivo": consulta[8:], "credito": None}
    for fonte in (commons, openverse):
        for r in relevantes(consulta, fonte(consulta)):
            if r["id"] in usados:
                continue
            ext = ".png" if r["url"].lower().endswith(".png") else ".jpg"
            arq = CACHE / f"{re.sub(r'[^0-9A-Za-z-]', '', str(r['id']))}{ext}"
            if not arq.exists():
                try:
                    arq.write_bytes(_get(r["url"]))
                except Exception:
                    continue
                if arq.stat().st_size < 30_000:
                    arq.unlink()
                    continue
            autor = r["autor"] or "autor desconhecido"
            return {"id": r["id"], "arquivo": str(arq),
                    "credito": f"\"{r['titulo'][:70]}\" — {autor} ({r['licenca']}), via {r['fonte']}"}
    return None
