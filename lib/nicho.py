"""Estado de nicho de cada canal e a regra de troca.

Regra (config.json -> regras_nicho):
- O canal tem UM nicho principal; Shorts de teste exploram outros nichos.
- Desempenho de um vídeo = views / mediana de views do canal (só vídeos com >= dias_maturacao).
- Um nicho de teste vence quando os últimos N vídeos dele (videos_seguidos_para_trocar) ficam todos
  >= multiplo_vencedor. Aí ele vira o principal e o antigo vira teste.
- Nada é julgado antes de o canal ter minimo_videos_para_julgar vídeos maduros.
"""
import json
import statistics

from .comum import DADOS, agora, config


def arquivo(canal):
    return DADOS / canal / "nicho.json"


def ler(canal):
    a = arquivo(canal)
    if a.exists():
        return json.loads(a.read_text(encoding="utf-8"))
    return {"principal": None, "testes": [], "historico": [], "recomendacao": None}


def gravar(canal, est):
    a = arquivo(canal)
    a.parent.mkdir(parents=True, exist_ok=True)
    a.write_text(json.dumps(est, ensure_ascii=False, indent=2), encoding="utf-8")


def definir(canal, principal=None, testes=None, motivo=""):
    est = ler(canal)
    if principal and principal != est["principal"]:
        est["historico"].append({"quando": agora(), "de": est["principal"], "para": principal,
                                 "motivo": motivo})
        est["principal"] = principal
    if testes is not None:
        est["testes"] = [t for t in testes if t != est["principal"]]
    gravar(canal, est)
    return est


def avaliar(canal, videos_com_nicho):
    """videos_com_nicho: [{'views', 'maduro', 'nicho', 'publicado'}]. Atualiza a recomendação."""
    r = config()["regras_nicho"]
    est = ler(canal)
    maduros = [v for v in videos_com_nicho if v["maduro"]]
    if len(maduros) < r["minimo_videos_para_julgar"]:
        est["recomendacao"] = {"acao": "esperar",
                               "porque": f"{len(maduros)} vídeo(s) maduro(s); preciso de "
                                         f"{r['minimo_videos_para_julgar']} para julgar."}
        est["placar"] = {}
        gravar(canal, est)
        return est
    mediana = statistics.median(v["views"] for v in maduros) or 1
    placar = {}
    for v in sorted(maduros, key=lambda x: x["publicado"]):
        if not v.get("nicho"):
            continue
        p = placar.setdefault(v["nicho"], {"videos": 0, "multiplos": []})
        p["videos"] += 1
        p["multiplos"].append(round(v["views"] / mediana, 2))
    for p in placar.values():
        p["mediana_multiplo"] = round(statistics.median(p["multiplos"]), 2)
    est["placar"] = placar
    est["mediana_views_canal"] = mediana

    rec = {"acao": "manter", "porque": f"nenhum teste bateu {r['multiplo_vencedor']}x em "
                                       f"{r['videos_seguidos_para_trocar']} seguidos."}
    n = r["videos_seguidos_para_trocar"]
    for nome, p in placar.items():
        if nome == est["principal"]:
            continue
        ultimos = p["multiplos"][-n:]
        if len(ultimos) == n and all(m >= r["multiplo_vencedor"] for m in ultimos):
            rec = {"acao": "trocar", "para": nome,
                   "porque": f"últimos {n} vídeos de '{nome}' fizeram {ultimos} x a mediana do canal."}
            break
    princ = placar.get(est["principal"])
    if rec["acao"] == "manter" and princ and len(princ["multiplos"]) >= n \
            and statistics.median(princ["multiplos"][-n:]) < 0.5:
        rec = {"acao": "testar_mais", "porque": f"nicho principal '{est['principal']}' caiu para "
                                                f"{princ['multiplos'][-n:]} x a mediana; dobrar os testes."}
    est["recomendacao"] = rec
    gravar(canal, est)
    return est
