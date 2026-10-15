"""Acesso ao YouTube (Data API v3 + Analytics) para os agentes."""
import datetime as dt
import json
from pathlib import Path

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from googleapiclient.http import MediaFileUpload

RAIZ = Path(__file__).resolve().parent.parent
CRED = RAIZ / "credenciais"


class TokenVencido(Exception):
    """O refresh token morreu (app em modo Teste vence em 7 dias). Rodar autorizar.py <canal>."""


def _creds(canal):
    arq = CRED / f"token_{canal}.json"
    if not arq.exists():
        raise TokenVencido(f"sem token para '{canal}' - rode: python autorizar.py {canal}")
    c = Credentials.from_authorized_user_file(str(arq))
    if not c.valid:
        try:
            c.refresh(Request())
        except Exception as e:  # invalid_grant = token vencido/revogado
            raise TokenVencido(f"token de '{canal}' venceu ({e}) - rode: python autorizar.py {canal}")
        arq.write_text(c.to_json(), encoding="utf-8")
    return c


def api(canal):
    return build("youtube", "v3", credentials=_creds(canal), cache_discovery=False)


def analytics(canal):
    return build("youtubeAnalytics", "v2", credentials=_creds(canal), cache_discovery=False)


def canal_info(canal):
    return json.loads((RAIZ / "canais" / canal / "canal.json").read_text(encoding="utf-8"))


def videos(canal, limite=200):
    """Todos os vídeos do canal com estatísticas públicas."""
    yt = api(canal)
    up = canal_info(canal)["uploads_playlist"]
    ids, token = [], None
    while len(ids) < limite:
        try:
            r = yt.playlistItems().list(part="contentDetails", playlistId=up, maxResults=50,
                                        pageToken=token).execute()
        except HttpError as e:
            if e.resp.status == 404:  # canal sem nenhum vídeo ainda
                return []
            raise
        ids += [i["contentDetails"]["videoId"] for i in r.get("items", [])]
        token = r.get("nextPageToken")
        if not token:
            break
    out = []
    for i in range(0, len(ids), 50):
        r = yt.videos().list(part="snippet,statistics,status,contentDetails",
                             id=",".join(ids[i:i + 50])).execute()
        for v in r["items"]:
            out.append({
                "id": v["id"],
                "titulo": v["snippet"]["title"],
                "publicado": v["snippet"]["publishedAt"],
                "duracao": v["contentDetails"]["duration"],
                "privacidade": v["status"]["privacyStatus"],
                "views": int(v["statistics"].get("viewCount", 0)),
                "likes": int(v["statistics"].get("likeCount", 0)),
            })
    return out


def metricas_por_video(canal, dias=90):
    """Views, minutos assistidos, % médio assistido e inscritos ganhos por vídeo (Analytics)."""
    ya = analytics(canal)
    fim = dt.date.today()
    ini = fim - dt.timedelta(days=dias)
    r = ya.reports().query(ids="channel==MINE", startDate=str(ini), endDate=str(fim),
                           metrics="views,estimatedMinutesWatched,averageViewPercentage,subscribersGained",
                           dimensions="video", sort="-views", maxResults=200).execute()
    cols = [c["name"] for c in r.get("columnHeaders", [])]
    return [dict(zip(cols, linha)) for linha in r.get("rows", [])]


def estatisticas_canal(canal):
    """Inscritos, views e nº de vídeos do canal agora (channels.list)."""
    c = api(canal).channels().list(part="statistics", mine=True).execute()["items"][0]["statistics"]
    return {"inscritos": int(c.get("subscriberCount", 0)), "views": int(c.get("viewCount", 0)),
            "videos": int(c.get("videoCount", 0))}


def diario(canal, dias=28):
    """Série diária do canal (Analytics): views, minutos, inscritos ganhos/perdidos."""
    fim = dt.date.today()
    ini = fim - dt.timedelta(days=dias)
    r = analytics(canal).reports().query(ids="channel==MINE", startDate=str(ini), endDate=str(fim),
                                        metrics="views,estimatedMinutesWatched,subscribersGained,subscribersLost",
                                        dimensions="day", sort="day").execute()
    cols = [c["name"] for c in r.get("columnHeaders", [])]
    return [dict(zip(cols, linha)) for linha in r.get("rows", [])]


def enviar(canal, arquivo, titulo, descricao, tags, para_criancas, categoria="1",
           publicar_em=None, privacidade="private"):
    """Sobe o vídeo. Projeto sem auditoria: o YouTube trava em privado de qualquer jeito."""
    yt = api(canal)
    status = {"privacyStatus": privacidade, "selfDeclaredMadeForKids": para_criancas,
              "embeddable": True}
    if publicar_em:  # agenda: precisa ir como private + publishAt
        status.update(privacyStatus="private", publishAt=publicar_em)
    body = {"snippet": {"title": titulo[:100], "description": descricao[:5000], "tags": tags[:30],
                        "categoryId": categoria, "defaultLanguage": "pt-BR",
                        "defaultAudioLanguage": "pt-BR"},
            "status": status}
    req = yt.videos().insert(part="snippet,status", body=body,
                             media_body=MediaFileUpload(str(arquivo), chunksize=8 * 1024 * 1024,
                                                        resumable=True))
    # vídeo longo (~700 MB): a conexão cai às vezes no meio. O envio é retomável, então tenta de novo
    # o mesmo pedaço com espera crescente, em vez de recomeçar tudo na próxima rodada da fila.
    import ssl
    import time
    from googleapiclient.errors import HttpError
    resp, falhas = None, 0
    while resp is None:
        try:
            _, resp = req.next_chunk(num_retries=3)
            falhas = 0
        except (ssl.SSLError, ConnectionError, TimeoutError, OSError) as e:
            falhas += 1
            if falhas > 12:
                raise
            print(f"  envio: conexão caiu ({type(e).__name__}), tentativa {falhas}/12")
            time.sleep(min(60, 5 * falhas))
        except HttpError as e:
            if e.resp.status not in (500, 502, 503, 504):
                raise
            falhas += 1
            if falhas > 12:
                raise
            time.sleep(min(60, 5 * falhas))
    return resp["id"]


def thumbnail(canal, video_id, imagem):
    api(canal).thumbnails().set(videoId=video_id, media_body=MediaFileUpload(str(imagem))).execute()


def tornar_publico(canal, video_id):
    """Retorna True se ficou público; False se o YouTube manteve privado (projeto sem auditoria)."""
    yt = api(canal)
    v = yt.videos().list(part="status", id=video_id).execute()["items"][0]
    st = v["status"]
    st["privacyStatus"] = "public"
    st.pop("publishAt", None)
    yt.videos().update(part="status", body={"id": video_id, "status": st}).execute()
    agora = yt.videos().list(part="status", id=video_id).execute()["items"][0]["status"]
    return agora["privacyStatus"] == "public"
