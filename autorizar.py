"""Autoriza um canal do YouTube para os agentes.

Uso:  python autorizar.py engenhoso
      python autorizar.py gta6
      python autorizar.py engenhoso --novo   (descarta o acesso atual e autoriza de novo)

Abre o navegador padrão; escolha a conta/canal certo e permita.
O token fica em credenciais/token_<canal>.json e o resumo do canal em canais/<canal>/canal.json.
"""
import json
import sys
from pathlib import Path

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

RAIZ = Path(__file__).resolve().parent
CRED = RAIZ / "credenciais"
SCOPES = [
    "https://www.googleapis.com/auth/youtube",              # ler, subir, editar título/thumb/status
    "https://www.googleapis.com/auth/yt-analytics.readonly",  # views, retenção, tempo assistido
]


def credenciais(canal: str) -> Credentials:
    token = CRED / f"token_{canal}.json"
    creds = None
    if token.exists():
        creds = Credentials.from_authorized_user_file(str(token), SCOPES)
    if creds and creds.valid:
        return creds
    if creds and creds.expired and creds.refresh_token:
        creds.refresh(Request())
    else:
        flow = InstalledAppFlow.from_client_secrets_file(str(CRED / "client_secret.json"), SCOPES)
        creds = flow.run_local_server(port=0, prompt="consent", access_type="offline",
                                      authorization_prompt_message="Abrindo o navegador: {url}",
                                      success_message="Canal autorizado. Pode fechar esta aba.")
    token.write_text(creds.to_json(), encoding="utf-8")
    return creds


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    if len(args) != 1 or args[0] not in ("engenhoso", "gta6"):
        sys.exit("uso: python autorizar.py engenhoso|gta6 [--novo]")
    canal = args[0]
    if "--novo" in sys.argv:  # força abrir o navegador e gerar um acesso novo
        (CRED / f"token_{canal}.json").unlink(missing_ok=True)
    yt = build("youtube", "v3", credentials=credenciais(canal))
    r = yt.channels().list(part="snippet,statistics,status,contentDetails", mine=True).execute()
    if not r.get("items"):
        sys.exit("Essa conta não tem canal. Autorize de novo escolhendo o canal certo.")
    c = r["items"][0]
    resumo = {
        "id": c["id"],
        "titulo": c["snippet"]["title"],
        "url": f"https://www.youtube.com/channel/{c['id']}",
        "inscritos": c["statistics"].get("subscriberCount"),
        "videos": c["statistics"].get("videoCount"),
        "views": c["statistics"].get("viewCount"),
        "made_for_kids": c["status"].get("madeForKids"),
        "uploads_playlist": c["contentDetails"]["relatedPlaylists"]["uploads"],
    }
    destino = RAIZ / "canais" / canal
    destino.mkdir(parents=True, exist_ok=True)
    (destino / "canal.json").write_text(json.dumps(resumo, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(resumo, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
