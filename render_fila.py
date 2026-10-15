"""Operador de render: renderiza os pedidos que os agentes deixam em producao/pedidos/, um por vez.

Roda a cada 10 min pelo Agendador do Windows (AgentesYouTube\\Render) - não depende do app Claude aberto.
Pedido = producao/pedidos/<qualquer>.json:
  {"roteiro": "episodios/gta6/v002-....json", "slot": "2026-10-15T19:00:00-03:00", "canal": "gta6",
   "formato": "longo", "criado": "...", "por": "yt-editor"}
Sucesso -> producao/feitos/ (o vídeo entra na fila com o slot; o publicar.py sobe e agenda).
Falha   -> producao/erros/ com o log (o agente da próxima rodada corrige).
Ordem: o slot mais cedo primeiro.
"""
import json
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

from lib.comum import DADOS, RAIZ, SEM_JANELA, agora, log

PROD = RAIZ / "producao"
TRAVA = DADOS / "render.lock"
ENV = {**os.environ, "PYTHONIOENCODING": "utf-8", "PYTHONUTF8": "1"}


def travar():
    DADOS.mkdir(exist_ok=True)
    try:
        fd = os.open(TRAVA, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
    except FileExistsError:
        try:
            pid = int(TRAVA.read_text() or 0)
        except ValueError:
            pid = 0
        if vivo(pid) and time.time() - TRAVA.stat().st_mtime < 4 * 3600:
            return False
        TRAVA.unlink(missing_ok=True)
        fd = os.open(TRAVA, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
    os.write(fd, str(os.getpid()).encode())
    os.close(fd)
    return True


def vivo(pid):
    if not pid:
        return False
    if os.name != "nt":
        try:
            os.kill(pid, 0)
            return True
        except OSError:
            return False
    r = subprocess.run(["tasklist", "/fi", f"PID eq {pid}", "/fo", "csv", "/nh"], capture_output=True, text=True,
                       creationflags=SEM_JANELA)
    return "python" in r.stdout.lower()


def main():
    for d in ("pedidos", "feitos", "erros"):
        (PROD / d).mkdir(parents=True, exist_ok=True)
    pedidos = []
    alvo = sys.argv[sys.argv.index("--pedido") + 1] if "--pedido" in sys.argv else None  # nuvem: 1 pedido por job
    for p in (PROD / "pedidos").glob("*.json"):
        if alvo and p.name != Path(alvo).name:
            continue
        try:
            pedidos.append((json.loads(p.read_text(encoding="utf-8")), p))
        except Exception:
            continue
    if not pedidos or not travar():
        return
    try:
        pedidos.sort(key=lambda x: (x[0].get("slot") or "9", x[1].name))
        ped, arq = pedidos[0]
        rot = RAIZ / ped["roteiro"]
        logf = DADOS / f"_render_{rot.stem}.log"
        log(ped.get("canal", "?"), f"render iniciado: {rot.stem} (sai às {(ped.get('slot') or '?')[11:16]})")
        args = [sys.executable, "-u", str(RAIZ / "motor_pro" / "render.py"), str(rot), "--fila"]
        if ped.get("slot"):
            args += ["--slot", ped["slot"]]
        with open(logf, "w", encoding="utf-8") as f:
            r = subprocess.run(args, cwd=RAIZ, env=ENV, stdout=f, stderr=subprocess.STDOUT,
                               creationflags=SEM_JANELA)
        ped["fim"] = agora()
        ped["log"] = str(logf)
        if r.returncode == 0:
            destino = PROD / "feitos" / arq.name
            log(ped.get("canal", "?"), f"render ok: {rot.stem} -> fila (o publicar.py sobe e agenda)")
        else:
            destino = PROD / "erros" / arq.name
            cauda = logf.read_text(encoding="utf-8", errors="replace").strip().splitlines()[-3:]
            ped["erro"] = " | ".join(cauda)
            log(ped.get("canal", "?"), f"RENDER FALHOU: {rot.stem}: {ped['erro'][:200]}")
        destino.write_text(json.dumps(ped, ensure_ascii=False, indent=2), encoding="utf-8")
        arq.unlink(missing_ok=True)
        if r.returncode == 0:  # já sobe na hora, sem esperar a próxima rodada da fila
            cmd = [sys.executable, str(RAIZ / "publicar.py")]
            if os.environ.get("GITHUB_ACTIONS"):  # na nuvem o job acaba junto: sobe e agenda antes de sair
                subprocess.run(cmd, cwd=RAIZ, env=ENV)
            else:
                subprocess.Popen(cmd, cwd=RAIZ, env=ENV, creationflags=SEM_JANELA)
        return r.returncode
    finally:
        TRAVA.unlink(missing_ok=True)


if __name__ == "__main__":
    sys.exit(main() or 0)
