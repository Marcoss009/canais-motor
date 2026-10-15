"""Painel de controle dos agentes: http://localhost:8787

Uso: python painel.py     (abre o navegador sozinho)
Mostra os canais, o nicho atual e a recomendação, a fila com prévia e os botões de aprovar/refazer.
"""
import json
import mimetypes
import subprocess
import sys
import threading
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from lib import nicho
from lib.comum import DADOS, FILA, RAIZ, config, itens, mudar

PAGINA = RAIZ / "painel" / "index.html"


def estado():
    cfg = config()
    canais = {}
    for c, cc in cfg["canais"].items():
        info_arq = RAIZ / "canais" / c / "canal.json"
        met_arq = DADOS / c / "metricas.json"
        met = json.loads(met_arq.read_text(encoding="utf-8")) if met_arq.exists() else {}
        canais[c] = {
            "nome": cc["nome"],
            "info": json.loads(info_arq.read_text(encoding="utf-8")) if info_arq.exists() else None,
            "token": (RAIZ / "credenciais" / f"token_{c}.json").exists(),
            "coletado": met.get("coletado"),
            "views": met.get("views_canal", met.get("total_views", 0)),
            "videos": met.get("total_videos", 0),
            "inscritos": met.get("inscritos"),
            "mediana_views": met.get("mediana_views"),
            "diario": met.get("diario", []),
            "lista": met.get("videos", []),
            "nicho": nicho.ler(c),
            "plano": _ler(RAIZ / "canais" / c / "plano.md"),
        }
    log = (DADOS / "agente.log")
    linhas = log.read_text(encoding="utf-8").splitlines()[-40:] if log.exists() else []
    fila = [{k: v for k, v in it.items() if k != "_pasta"} | {"pasta": Path(it["_pasta"]).name}
            for it in itens()]
    return {"canais": canais, "fila": fila, "log": linhas[::-1]}


def _ler(p):
    return p.read_text(encoding="utf-8") if p.exists() else ""


class H(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def _json(self, obj, code=200):
        b = json.dumps(obj, ensure_ascii=False).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(b)))
        self.end_headers()
        self.wfile.write(b)

    def do_GET(self):
        u = urlparse(self.path)
        if u.path == "/":
            b = PAGINA.read_bytes()
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(b)
        elif u.path == "/api/estado":
            self._json(estado())
        elif u.path == "/arquivo":
            # só serve arquivos de dentro da pasta fila/
            p = Path(parse_qs(u.query).get("p", [""])[0]).resolve()
            if FILA.resolve() not in p.parents or not p.is_file():
                return self._json({"erro": "arquivo fora da fila"}, 404)
            self._servir(p)
        else:
            self._json({"erro": "não encontrado"}, 404)

    def _servir(self, p):
        tam = p.stat().st_size
        tipo = mimetypes.guess_type(p.name)[0] or "application/octet-stream"
        rng = self.headers.get("Range")
        ini, fim = 0, tam - 1
        if rng and rng.startswith("bytes="):
            a, b = rng[6:].split("-")
            ini = int(a or 0)
            fim = int(b) if b else tam - 1
            self.send_response(206)
            self.send_header("Content-Range", f"bytes {ini}-{fim}/{tam}")
        else:
            self.send_response(200)
        self.send_header("Content-Type", tipo)
        self.send_header("Accept-Ranges", "bytes")
        self.send_header("Content-Length", str(fim - ini + 1))
        self.end_headers()
        with open(p, "rb") as f:
            f.seek(ini)
            resto = fim - ini + 1
            while resto > 0:
                bloco = f.read(min(1 << 20, resto))
                if not bloco:
                    break
                try:
                    self.wfile.write(bloco)
                except (BrokenPipeError, ConnectionResetError):
                    return
                resto -= len(bloco)

    def do_POST(self):
        u = urlparse(self.path)
        corpo = json.loads(self.rfile.read(int(self.headers.get("Content-Length", 0)) or b"{}") or "{}")
        if u.path == "/api/decidir":
            for it in itens(corpo["canal"]):
                if it["id"] == corpo["id"] and it["estado"] == "enviado":
                    mudar(it, "aprovado" if corpo["ok"] else "recusado", "via painel")
                    threading.Thread(target=_rodar, args=("publicar.py",), daemon=True).start()
                    return self._json({"ok": True})
            return self._json({"erro": "item não está aguardando decisão"}, 400)
        if u.path == "/api/rodar":
            script = {"coletar": "coletar.py", "publicar": "publicar.py"}.get(corpo.get("o"))
            if not script:
                return self._json({"erro": "script desconhecido"}, 400)
            threading.Thread(target=_rodar, args=(script,), daemon=True).start()
            return self._json({"ok": True})
        self._json({"erro": "não encontrado"}, 404)


def _rodar(script):
    subprocess.run([sys.executable, str(RAIZ / script)], cwd=RAIZ,
                   env={**__import__("os").environ, "PYTHONIOENCODING": "utf-8"})


def main():
    porta = config()["painel_porta"]
    srv = ThreadingHTTPServer(("127.0.0.1", porta), H)
    url = f"http://localhost:{porta}"
    print(f"Painel em {url}  (Ctrl+C para fechar)")
    if "--sem-navegador" not in sys.argv:
        webbrowser.open(url)
    srv.serve_forever()


if __name__ == "__main__":
    main()
