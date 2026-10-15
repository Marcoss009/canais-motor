"""Roda a fila: lê aprovações, sobe vídeos prontos (privado), pede aprovação e agenda os aprovados.

Uso: python publicar.py          (roda a cada 15 min pelo Agendador do Windows)
Só agenda o que está 'aprovado'. Com config.json -> aprovacao_automatica = true (modo independente, pedido do dono
em 15/10/2026) o vídeo é aprovado sozinho ao subir; o dono ainda pode recusar pelo Estúdio até o horário.
Cada item pode trazer "slot" (horário desejado: longo 19:00, Short 20:00); senão usa o próximo horário livre.
"""
import datetime as dt
import os
import subprocess
import time
from pathlib import Path

from googleapiclient.errors import HttpError

from lib import telegram
from lib.comum import DADOS, config, itens, log, mudar, salvar
from lib.yt import TokenVencido, enviar, thumbnail, api


def previa_leve(item):
    """Telegram aceita até 50 MB por bot; gera 480p se precisar."""
    video = Path(item["video"])
    if video.stat().st_size < 45 * 1024 * 1024:
        return video
    leve = video.with_name("previa_480p.mp4")
    if not leve.exists():
        subprocess.run([config()["ffmpeg"], "-y", "-loglevel", "error", "-i", str(video),
                        "-vf", "scale=-2:480", "-c:v", "libx264", "-crf", "30", "-preset", "veryfast",
                        "-c:a", "aac", "-b:a", "96k", str(leve)], check=True)
    return leve


def proximo_horario(canal, formato=None):
    """Próximo horário livre do canal (horarios_formato[formato] ou horarios), sem repetir um já agendado."""
    cfg = config()["canais"][canal]
    horarios = (cfg.get("horarios_formato") or {}).get(formato) or cfg["horarios"]
    ocupados = {it.get("publica_em") for it in itens(canal) if it["estado"] in ("agendado", "publicado")}
    agora = dt.datetime.now().astimezone()
    for d in range(0, 30):
        dia = (agora + dt.timedelta(days=d)).date()
        for h in horarios:
            hh, mm = map(int, h.split(":"))
            quando = dt.datetime.combine(dia, dt.time(hh, mm)).astimezone()
            if quando > agora + dt.timedelta(minutes=30) and quando.isoformat() not in ocupados:
                return quando.isoformat()
    return None


def aplicar_thumb(it):
    """Miniatura personalizada exige canal verificado por telefone; tenta de novo a cada rodada até dar certo."""
    if not it.get("thumb") or it.get("thumb_ok") or not it.get("youtube_id"):
        return
    try:
        thumbnail(it["canal"], it["youtube_id"], it["thumb"])
        it["thumb_ok"] = True
        salvar(it)
        log(it["canal"], f"{it['id']}: miniatura aplicada")
    except HttpError as e:
        if not it.get("thumb_aviso"):
            it["thumb_aviso"] = True
            salvar(it)
            log(it["canal"], f"{it['id']}: miniatura recusada ({e.resp.status}) - verifique o canal em youtube.com/verify")


def ler_aprovacoes():
    for dec, canal, id_ in telegram.respostas():
        for it in itens(canal, "enviado"):
            if it["id"] == id_:
                mudar(it, "aprovado" if dec == "ok" else "recusado", "via Telegram")
                log(canal, f"{id_}: {'aprovado' if dec == 'ok' else 'recusado'} pelo Telegram")


def subir_prontos():
    for it in itens(estado="pronto"):
        canal = it["canal"]
        cfg = config()["canais"][canal]
        vid = enviar(canal, it["video"], it["titulo"], it["descricao"], it["tags"],
                     cfg["para_criancas"], cfg["categoria"])
        it["youtube_id"] = vid
        it = mudar(it, "enviado", f"youtube_id={vid} (privado)")  # grava já: nunca subir duas vezes
        aplicar_thumb(it)
        log(canal, f"{it['id']}: enviado como privado -> https://youtu.be/{vid}")
        if config().get("aprovacao_automatica"):
            mudar(it, "aprovado", "aprovação automática (modo independente)")
            log(canal, f"{it['id']}: aprovado automaticamente (modo independente)")
        elif not telegram.pedir_aprovacao(it, previa_leve(it)):
            log(canal, f"{it['id']}: aguardando aprovação no painel (Telegram não configurado)")


def agendar_aprovados():
    for it in itens(estado="aprovado"):
        canal = it["canal"]
        quando = None
        if it.get("slot"):  # horário pedido pela produção diária (19:00 longo / 20:00 Short)
            pedido = dt.datetime.fromisoformat(it["slot"])
            ocupado = any(o.get("publica_em") == it["slot"] for o in itens(canal) if o["id"] != it["id"])
            if pedido > dt.datetime.now().astimezone() + dt.timedelta(minutes=10) and not ocupado:
                quando = it["slot"]
        quando = quando or proximo_horario(canal, it.get("formato"))
        yt = api(canal)
        st = yt.videos().list(part="status", id=it["youtube_id"]).execute()["items"][0]["status"]
        st.update(privacyStatus="private", publishAt=dt.datetime.fromisoformat(quando)
                  .astimezone(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.000Z"))
        try:
            # a resposta do update já traz o status gravado; reler logo depois às vezes volta sem publishAt
            depois = yt.videos().update(part="status", body={"id": it["youtube_id"], "status": st}).execute()["status"]
        except HttpError as e:
            log(canal, f"{it['id']}: YouTube recusou o agendamento ({e.resp.status}) - tento de novo na próxima rodada")
            continue
        if depois.get("publishAt"):
            it["publica_em"] = quando
            mudar(it, "agendado", f"vai ao ar em {quando}")
            log(canal, f"{it['id']}: agendado para {quando}")
            telegram.avisar(f"[{canal}] agendado para {quando[:16].replace('T', ' ')}: {it['titulo']}")
        else:
            log(canal, f"{it['id']}: YouTube não aceitou o horário - tento de novo na próxima rodada")


def marcar_publicados():
    """Passado o horário, confere no YouTube. Público = publicado. Ainda privado 30 min depois = travado
    pela falta de auditoria da API -> 'manual' (subir pelo Studio)."""
    agora = dt.datetime.now().astimezone()
    for it in itens(estado="agendado"):
        quando = dt.datetime.fromisoformat(it["publica_em"]) if it.get("publica_em") else None
        if not quando or quando > agora:
            continue
        st = api(it["canal"]).videos().list(part="status", id=it["youtube_id"]).execute()["items"][0]["status"]
        if st["privacyStatus"] == "public":
            mudar(it, "publicado")
            log(it["canal"], f"{it['id']}: no ar -> https://youtu.be/{it['youtube_id']}")
        elif agora - quando > dt.timedelta(minutes=30):
            mudar(it, "manual", "passou do horário e o YouTube manteve privado (projeto da API sem auditoria)")
            log(it["canal"], f"{it['id']}: travado em privado (sem auditoria) - subir pelo Studio")
            telegram.avisar(f"[{it['canal']}] '{it['titulo']}' passou do horário e continua privado "
                            "(falta a auditoria da API). Está no painel para subir pelo Studio.")


def main():
    # trava: a tarefa de 15 em 15 min e o painel podem chamar ao mesmo tempo (subiria em dobro)
    trava = DADOS / "publicar.lock"
    DADOS.mkdir(exist_ok=True)
    try:
        fd = os.open(trava, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
    except FileExistsError:
        if time.time() - trava.stat().st_mtime < 3 * 3600:  # um upload grande pode demorar
            return
        trava.unlink(missing_ok=True)  # trava velha de um processo que morreu
        fd = os.open(trava, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
    os.write(fd, str(os.getpid()).encode())
    os.close(fd)
    try:
        ler_aprovacoes()
        subir_prontos()
        for it in itens():
            if it["estado"] in ("enviado", "aprovado", "agendado", "publicado", "manual"):
                aplicar_thumb(it)
        agendar_aprovados()
        marcar_publicados()
    except TokenVencido as e:
        log("geral", f"PRECISA REAUTORIZAR: {e}")
        telegram.avisar(f"⚠️ {e}")
    finally:
        trava.unlink(missing_ok=True)


if __name__ == "__main__":
    main()
