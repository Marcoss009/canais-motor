"""Configuração, fila de vídeos e log - compartilhado por todos os scripts."""
import datetime as dt
import json
import os
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
FILA = RAIZ / "fila"
DADOS = RAIZ / "dados"

# Estados de um item da fila, na ordem:
#   pronto      -> renderizado, esperando subir
#   enviado     -> subiu como privado, esperando sua aprovação
#   aprovado    -> você aprovou; o agente agenda no próximo horário livre
#   agendado    -> o YouTube vai publicar sozinho no horário (publica_em)
#   publicado   -> está no ar
#   recusado    -> você recusou; o agente refaz na próxima rodada
#   manual      -> aprovado, mas o YouTube travou em privado (projeto sem auditoria): suba pelo Studio
ESTADOS = ["pronto", "enviado", "aprovado", "agendado", "publicado", "recusado", "manual"]


SEM_JANELA = 0x08000000 if os.name == "nt" else 0  # CREATE_NO_WINDOW só existe no Windows


def config():
    """config.json; no Linux (GitHub Actions) o ffmpeg/ffprobe vêm do PATH."""
    import shutil
    c = json.loads((RAIZ / "config.json").read_text(encoding="utf-8"))
    for k in ("ffmpeg", "ffprobe"):
        if not os.path.exists(c.get(k, "")):
            c[k] = shutil.which(k) or k
    return c


def env(chave, padrao=None):
    arq = RAIZ / ".env"
    if arq.exists():
        for linha in arq.read_text(encoding="utf-8").splitlines():
            if "=" in linha and not linha.strip().startswith("#"):
                k, v = linha.split("=", 1)
                if k.strip() == chave:
                    return v.strip().strip('"')
    return os.environ.get(chave, padrao)


def agora():
    return dt.datetime.now().isoformat(timespec="seconds")


def log(canal, msg):
    DADOS.mkdir(exist_ok=True)
    linha = f"{agora()} [{canal}] {msg}"
    print(linha)
    with open(DADOS / "agente.log", "a", encoding="utf-8") as f:
        f.write(linha + "\n")


def itens(canal=None, estado=None):
    out = []
    if not FILA.exists():
        return out
    for arq in sorted(FILA.glob("*/*/item.json")):
        it = json.loads(arq.read_text(encoding="utf-8"))
        it["_pasta"] = str(arq.parent)
        for k in ("video", "thumb", "roteiro"):  # caminho gravado em outra máquina (Windows x nuvem)
            if it.get(k) and not Path(it[k]).exists():
                alt = arq.parent / Path(it[k].replace("\\", "/")).name
                if alt.exists():
                    it[k] = str(alt)
        if (canal is None or it["canal"] == canal) and (estado is None or it["estado"] == estado):
            out.append(it)
    return out


def salvar(item):
    pasta = Path(item["_pasta"]) if "_pasta" in item else FILA / item["canal"] / item["id"]
    pasta.mkdir(parents=True, exist_ok=True)
    item = {k: v for k, v in item.items() if k != "_pasta"}
    item["atualizado"] = agora()
    (pasta / "item.json").write_text(json.dumps(item, ensure_ascii=False, indent=2), encoding="utf-8")
    item["_pasta"] = str(pasta)
    return item


def novo_item(canal, id_, formato, titulo, descricao, tags, video, thumb, nicho, roteiro=None):
    """Registra um vídeo pronto na fila. video/thumb são caminhos dentro da pasta do item."""
    return salvar({
        "id": id_, "canal": canal, "formato": formato, "estado": "pronto",
        "titulo": titulo, "descricao": descricao, "tags": tags,
        "video": str(video), "thumb": str(thumb) if thumb else None,
        "nicho": nicho, "roteiro": roteiro, "criado": agora(), "youtube_id": None,
        "historico": [],
    })


def mudar(item, estado, nota=""):
    item["historico"].append({"quando": agora(), "de": item["estado"], "para": estado, "nota": nota})
    item["estado"] = estado
    return salvar(item)
