"""Coleta diária: estatísticas dos canais, desempenho por nicho e recomendação de troca.

Uso: python coletar.py            (todos os canais)
     python coletar.py engenhoso
"""
import datetime as dt
import json
import sys

from lib import nicho, telegram
from lib.comum import DADOS, config, itens, log
from lib.yt import TokenVencido, diario, estatisticas_canal, metricas_por_video, videos


def coletar(canal):
    regras = config()["regras_nicho"]
    vids = videos(canal)
    try:
        ana = {m["video"]: m for m in metricas_por_video(canal)}
    except Exception as e:  # canal novo: Analytics ainda sem dados
        log(canal, f"analytics indisponível ({e.__class__.__name__}); seguindo só com views públicas")
        ana = {}
    da_fila = {it["youtube_id"]: it for it in itens(canal) if it.get("youtube_id")}
    nicho_por_id = {k: v.get("nicho") for k, v in da_fila.items()}
    try:
        serie = diario(canal)
    except Exception as e:
        log(canal, f"série diária indisponível ({e.__class__.__name__})")
        serie = []
    hoje = dt.datetime.now(dt.timezone.utc)
    lista = []
    for v in vids:
        pub = dt.datetime.fromisoformat(v["publicado"].replace("Z", "+00:00"))
        a = ana.get(v["id"], {})
        lista.append({**v,
                      "nicho": nicho_por_id.get(v["id"]),
                      "formato": da_fila.get(v["id"], {}).get("formato"),
                      "idade_dias": (hoje - pub).days,
                      "maduro": (hoje - pub).days >= regras["dias_maturacao"],
                      "minutos_assistidos": a.get("estimatedMinutesWatched"),
                      "pct_assistido": a.get("averageViewPercentage"),
                      "inscritos_ganhos": a.get("subscribersGained")})
    pasta = DADOS / canal
    (pasta / "historico").mkdir(parents=True, exist_ok=True)
    maduros = sorted(v["views"] for v in lista if v["maduro"])
    mediana = maduros[len(maduros) // 2] if maduros else None
    for v in lista:  # quantas vezes a mediana do canal (o "múltiplo" que decide o nicho)
        v["multiplo"] = round(v["views"] / mediana, 2) if mediana else None
    canal_agora = estatisticas_canal(canal)
    resumo = {"coletado": dt.datetime.now().isoformat(timespec="seconds"),
              "inscritos": canal_agora["inscritos"], "views_canal": canal_agora["views"],
              "mediana_views": mediana, "diario": serie,
              "total_videos": len(lista), "total_views": sum(v["views"] for v in lista),
              "videos": sorted(lista, key=lambda x: x["publicado"], reverse=True)}
    (pasta / "metricas.json").write_text(json.dumps(resumo, ensure_ascii=False, indent=2), encoding="utf-8")
    (pasta / "historico" / f"{dt.date.today()}.json").write_text(
        json.dumps({"views": resumo["total_views"], "videos": len(lista), "inscritos": canal_agora["inscritos"],
                    "por_video": {v["id"]: v["views"] for v in lista}}), encoding="utf-8")
    est = nicho.avaliar(canal, lista)
    rec = est["recomendacao"]
    log(canal, f"{len(lista)} vídeos, {resumo['total_views']} views; nicho: {rec['acao']} - {rec['porque']}")
    if rec["acao"] == "trocar":
        telegram.avisar(f"[{canal}] Recomendação de troca de nicho: {rec['porque']}")
    return resumo


def limpar_antigos(dias=30):
    """Política de privacidade: cópias locais de dados da API com mais de 30 dias são apagadas."""
    limite = dt.datetime.now().timestamp() - dias * 86400
    for arq in list(DADOS.glob("*/historico/*.json")) + list(DADOS.glob("*/pesquisa/*.json")):
        if arq.stat().st_mtime < limite:
            arq.unlink()


def main():
    limpar_antigos()
    canais = sys.argv[1:] or list(config()["canais"])
    for c in canais:
        try:
            coletar(c)
        except TokenVencido as e:
            log(c, f"PRECISA REAUTORIZAR: {e}")
            telegram.avisar(f"⚠️ {e}")


if __name__ == "__main__":
    main()
