"""Aprovação pelo celular via bot do Telegram.

Configuração (uma vez): crie o bot no @BotFather, cole TELEGRAM_TOKEN=... no .env e mande "oi" pro bot.
O chat_id é descoberto sozinho na primeira mensagem e salvo em dados/telegram.json.
Sem token, tudo continua funcionando pelo painel (http://localhost:8787).
"""
import json

import requests

from .comum import DADOS, env

API = "https://api.telegram.org/bot{}/{}"


def _token():
    return env("TELEGRAM_TOKEN")


def ativo():
    return bool(_token()) and _chat() is not None


def _estado():
    arq = DADOS / "telegram.json"
    return json.loads(arq.read_text(encoding="utf-8")) if arq.exists() else {}


def _gravar(est):
    DADOS.mkdir(exist_ok=True)
    (DADOS / "telegram.json").write_text(json.dumps(est), encoding="utf-8")


def _chamar(metodo, **kw):
    files = kw.pop("files", None)
    r = requests.post(API.format(_token(), metodo), data=kw, files=files, timeout=120)
    r.raise_for_status()
    return r.json()["result"]


def _chat():
    est = _estado()
    if est.get("chat_id"):
        return est["chat_id"]
    if not _token():
        return None
    for u in _chamar("getUpdates", timeout=0):
        msg = u.get("message")
        if msg:
            est["chat_id"] = msg["chat"]["id"]
            _gravar(est)
            _chamar("sendMessage", chat_id=est["chat_id"],
                    text="Conectado! Vou te mandar aqui cada vídeo pronto para você aprovar.")
            return est["chat_id"]
    return None


def avisar(texto):
    if ativo():
        _chamar("sendMessage", chat_id=_chat(), text=texto[:4000])


def pedir_aprovacao(item, previa):
    """Manda a prévia (vídeo leve) com botões ✅/❌. callback_data = 'ok|canal|id' ou 'nao|canal|id'."""
    if not ativo():
        return False
    teclado = {"inline_keyboard": [[
        {"text": "✅ Publicar", "callback_data": f"ok|{item['canal']}|{item['id']}"},
        {"text": "❌ Refazer", "callback_data": f"nao|{item['canal']}|{item['id']}"},
    ]]}
    legenda = f"[{item['canal']}] {item['formato']}\n{item['titulo']}\n\nNicho: {item.get('nicho', '-')}"
    with open(previa, "rb") as f:
        _chamar("sendVideo", chat_id=_chat(), caption=legenda[:1000],
                reply_markup=json.dumps(teclado), files={"video": f})
    return True


def respostas():
    """Lê os cliques nos botões desde a última leitura. Retorna [(decisao, canal, id)]."""
    if not ativo():
        return []
    est = _estado()
    ups = _chamar("getUpdates", offset=est.get("offset", 0), timeout=0)
    out = []
    for u in ups:
        est["offset"] = u["update_id"] + 1
        cb = u.get("callback_query")
        if cb and str(cb["message"]["chat"]["id"]) == str(_chat()):
            dec, canal, id_ = cb["data"].split("|", 2)
            out.append((dec, canal, id_))
            _chamar("answerCallbackQuery", callback_query_id=cb["id"],
                    text="Publicando!" if dec == "ok" else "Ok, vou refazer.")
    _gravar(est)
    return out
