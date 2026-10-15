"""Estúdio - o app de controle dos canais (Engenhoso + GTAzando).

Abre numa janela própria (Edge em modo app: sem abas nem barra de endereço) e mostra tudo o que os agentes fazem:
canais e métricas, roteiros, conferência, render ao vivo, fila de aprovação, agenda e log.
Iniciar: atalho "Estúdio" na Área de Trabalho/Menu Iniciar, ou  pythonw app/estudio.py
Fechar a janela encerra o app.
"""
import ctypes
import json
import mimetypes
import os
import socket
import subprocess
import sys
import threading
import time
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, quote, unquote, urlparse

AQUI = Path(__file__).resolve().parent
RAIZ = AQUI.parent
sys.path.insert(0, str(RAIZ))
from lib import nicho  # noqa: E402
from lib.comum import DADOS, FILA, config, itens, mudar  # noqa: E402

PORTA = 8790
UI = AQUI / "ui"
PY = Path(sys.executable).with_name("python.exe")
ENV = {**os.environ, "PYTHONIOENCODING": "utf-8", "PYTHONUTF8": "1"}
ETAPAS_RENDER = ["voz", "trilha", "imagens", "cenas", "render"]
SEM_JANELA = 0x08000000  # CREATE_NO_WINDOW


# ---------------- utilidades ----------------
def ler_json(p, padrao=None):
    try:
        return json.loads(Path(p).read_text(encoding="utf-8"))
    except Exception:
        return padrao


def vivo(pid):
    """Processo ainda existe? (OpenProcess + GetExitCodeProcess, sem psutil)."""
    if not pid:
        return False
    k = ctypes.windll.kernel32
    h = k.OpenProcess(0x1000, False, int(pid))  # PROCESS_QUERY_LIMITED_INFORMATION
    if not h:
        return False
    cod = ctypes.c_ulong()
    k.GetExitCodeProcess(h, ctypes.byref(cod))
    # o Windows reaproveita números de processo: confere se é mesmo um Python (o motor)
    buf = ctypes.create_unicode_buffer(1024)
    n = ctypes.c_ulong(1024)
    k.QueryFullProcessImageNameW(h, 0, buf, ctypes.byref(n))
    k.CloseHandle(h)
    return cod.value == 259 and "python" in buf.value.lower()  # 259 = STILL_ACTIVE


def url_arquivo(p):
    if not p:
        return None
    p = Path(p)
    if not p.exists():
        return None
    try:
        rel = p.resolve().relative_to(RAIZ)
    except ValueError:
        return None
    return "/f/" + quote(rel.as_posix()) + f"?v={int(p.stat().st_mtime)}"


def dur_iso(s):
    """PT8M6S -> segundos"""
    import re
    m = re.fullmatch(r"PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?", s or "")
    return (int(m[1] or 0) * 3600 + int(m[2] or 0) * 60 + int(m[3] or 0)) if m else None


# ---------------- tarefas do Windows (cache de 60 s) ----------------
_tarefas = {"quando": 0, "dados": []}


def tarefas():
    if time.time() - _tarefas["quando"] < 60:
        return _tarefas["dados"]
    out = []
    for nome in ("AgentesYouTube\\Render", "AgentesYouTube\\Fila", "AgentesYouTube\\Vigia", "AgentesYouTube\\Metricas"):
        try:
            r = subprocess.run(["schtasks", "/query", "/tn", nome, "/fo", "csv", "/v", "/nh"], capture_output=True,
                               text=True, encoding="cp850", errors="replace", creationflags=SEM_JANELA, timeout=15)
            cols = next(iter(__import__("csv").reader([r.stdout.strip().splitlines()[0]]))) if r.stdout.strip() else []
            out.append({"nome": nome.split("\\")[1], "proxima": cols[2] if len(cols) > 2 else "?",
                        "status": cols[3] if len(cols) > 3 else "?", "ultima": cols[5] if len(cols) > 5 else "?",
                        "resultado": cols[6] if len(cols) > 6 else "?"})
        except Exception as e:
            out.append({"nome": nome.split("\\")[1], "erro": str(e)})
    for nome, quando in (("Produção diária (Claude)", "todo dia 06:30"), ("Plantão de notícia (Claude)", "todo dia 12:00"),
                         ("Conferência da tarde (Claude)", "todo dia 16:30"),
                         ("Revisão semanal (Claude)", "segunda 08:00")):
        out.append({"nome": nome, "proxima": quando, "status": "agendada no app Claude (precisa do app aberto)"})
    _tarefas.update(quando=time.time(), dados=out)
    return out


# ---------------- produção: junta roteiros, status de render e fila ----------------
def producao():
    cfg = config()
    por_chave = {}
    for canal in cfg["canais"]:
        for arq in sorted((RAIZ / "episodios" / canal).glob("*.json")):
            ep = ler_json(arq, {})
            pasta = FILA / canal / arq.stem
            por_chave[(canal, arq.stem)] = {
                "canal": canal, "id": arq.stem, "titulo": ep.get("titulo", arq.stem), "formato": ep.get("formato"),
                "nicho": ep.get("nicho"), "cenas": len(ep.get("cenas") or ep.get("slides") or []),
                "motor": "pro" if "cenas" in ep else "antigo", "etapa": "roteiro",
                "roteiro_mod": arq.stat().st_mtime, "pasta": str(pasta)}
    for it in itens():
        k = (it["canal"], it["id"])
        base = por_chave.setdefault(k, {"canal": it["canal"], "id": it["id"], "motor": "antigo",
                                        "pasta": it["_pasta"]})
        base.update({"titulo": it["titulo"], "formato": it.get("formato"), "nicho": it.get("nicho"),
                     "slot": it.get("slot"),
                     "etapa": it["estado"], "estado_fila": it["estado"], "youtube_id": it.get("youtube_id"),
                     "publica_em": it.get("publica_em"), "atualizado": it.get("atualizado"),
                     "criado": it.get("criado")})
    out = []
    for (canal, id_), p in por_chave.items():
        pasta = Path(p["pasta"])
        st = ler_json(pasta / "_trabalho" / "status.json")
        if st:
            p["status"] = st
            ativo = st.get("etapa") in ETAPAS_RENDER and vivo(st.get("pid"))
            if ativo:
                p["etapa"] = "renderizando" if st.get("modo") == "final" else "conferindo"
                p["sub"] = st["etapa"]
                if st["etapa"] == "render":  # progresso pelo tamanho do arquivo (vale até para render antigo)
                    v = pasta / "video.mp4"
                    dur = st.get("duracao") or 480
                    pct = min(0.99, (v.stat().st_size if v.exists() else 0) / ((1.25e6 if p.get("formato") == "short" else 1.512e6) * dur))
                    gasto = time.time() - st.get("desde", time.time())
                    p["pct"] = pct
                    p["eta"] = (gasto / pct - gasto) if pct > 0.02 else None
            elif p["etapa"] == "roteiro":
                if st.get("etapa") == "erro" or (st.get("etapa") in ETAPAS_RENDER and not ativo):
                    p["etapa"] = "erro"
                    p["erro"] = st.get("msg") or f"parou na etapa '{st.get('etapa')}'"
                elif (pasta / "_trabalho" / "confere_0.png").exists():
                    p["etapa"] = "conferencia"
        if p["etapa"] == "roteiro" and not st and (pasta / "_trabalho" / "confere_0.png").exists():
            p["etapa"] = "conferencia"
        p["thumb"] = url_arquivo(pasta / "thumb.jpg") or url_arquivo(pasta / "thumb.png")
        p["video"] = url_arquivo(pasta / "video.mp4") if p["etapa"] not in ("renderizando",) else None
        rot = ler_json(pasta / "roteiro.json") or {}
        p["duracao"] = rot.get("duracao") or (st or {}).get("duracao")
        out.append(p)
    # pedidos de render (o operador do Windows renderiza um por vez, o horário mais cedo primeiro)
    prod = RAIZ / "producao"
    pedidos = sorted([(ler_json(q, {}), q) for q in (prod / "pedidos").glob("*.json")],
                     key=lambda x: (x[0].get("slot") or "9", x[1].name))
    por_id = {(x["canal"], x["id"]): x for x in out}
    for pos, (ped, q) in enumerate(pedidos, 1):
        k = (ped.get("canal"), Path(ped.get("roteiro", "")).stem)
        x = por_id.get(k)
        if x and x["etapa"] in ("roteiro", "conferencia", "erro"):
            x["etapa"], x["fila_pos"] = "na_fila", pos
        if x:
            x["slot"] = ped.get("slot")
    for q in (prod / "erros").glob("*.json"):
        ped = ler_json(q, {})
        x = por_id.get((ped.get("canal"), Path(ped.get("roteiro", "")).stem))
        if x and x["etapa"] in ("roteiro", "conferencia"):
            x["etapa"], x["erro"] = "erro", "render falhou: " + (ped.get("erro") or "")[:300]
    ordem = {"renderizando": 0, "conferindo": 1, "na_fila": 2, "enviado": 3, "erro": 4, "conferencia": 5,
             "roteiro": 6, "pronto": 7, "aprovado": 8, "agendado": 9, "manual": 10, "recusado": 11, "publicado": 12}
    out.sort(key=lambda x: (ordem.get(x["etapa"], 20), x["canal"], x["id"]))
    return out


def canais():
    cfg = config()
    out = {}
    for c, cc in cfg["canais"].items():
        met = ler_json(DADOS / c / "metricas.json", {}) or {}
        info = ler_json(RAIZ / "canais" / c / "canal.json", {}) or {}
        tema = ler_json(RAIZ / "canais" / c / "tema.json", {}) or {}
        lista = met.get("videos", [])
        for v in lista:
            v["segundos"] = dur_iso(v.get("duracao"))
        out[c] = {"nome": cc["nome"], "id": info.get("id"), "url": info.get("url"),
                  "inscritos": met.get("inscritos"), "views": met.get("views_canal") or met.get("total_views") or 0,
                  "videos": met.get("total_videos", 0), "mediana": met.get("mediana_views"),
                  "coletado": met.get("coletado"), "diario": met.get("diario", []), "lista": lista,
                  "nicho": nicho.ler(c), "persona": cc.get("persona"), "semana": cc.get("semana"),
                  "horarios": cc.get("horarios"), "cor": tema.get("destaque"), "marca": tema.get("marca"),
                  "token": (RAIZ / "credenciais" / f"token_{c}.json").exists()}
    return out


AGENTES_DIR = Path.home() / ".claude" / "agents"
ORDEM_AGENTES = ["yt-analista", "yt-radar", "yt-acervo", "yt-roteirista", "yt-checador", "yt-seo", "yt-thumb",
                 "yt-editor", "yt-publicador", "yt-horarios"]


def agentes():
    out = []
    for arq in AGENTES_DIR.glob("yt-*.md"):
        txt = arq.read_text(encoding="utf-8", errors="replace")
        meta = {}
        if txt.startswith("---"):
            for linha in txt.split("---", 2)[1].splitlines():
                if ":" in linha:
                    k, v = linha.split(":", 1)
                    meta[k.strip()] = v.strip()
        out.append({"nome": meta.get("name", arq.stem), "modelo": meta.get("model", "?"),
                    "descricao": meta.get("description", "")})
    out.sort(key=lambda a: ORDEM_AGENTES.index(a["nome"]) if a["nome"] in ORDEM_AGENTES else 99)
    return out


def rodada():
    """Checklist da rodada de hoje, pelos arquivos que cada agente deixa."""
    hoje = time.strftime("%Y-%m-%d")
    d = RAIZ / "producao" / "rodadas" / hoje
    def tem(*nomes):
        return any((d / n).exists() or list(d.glob(n)) for n in nomes)
    prod = RAIZ / "producao"
    pedidos_hoje = [q for sub in ("pedidos", "feitos") for q in (prod / sub).glob(f"{hoje}_*.json")]
    passos = [
        ("yt-analista", "Métricas e nicho", tem("analise.md")),
        ("yt-radar", "Pauta do dia", tem("pauta.json")),
        ("yt-acervo", "Cenas oficiais escolhidas", tem("cenas_*.json")),
        ("yt-roteirista", "Roteiros (longo + Short)", None),
        ("yt-checador", "Checagem de fatos", tem("checagem_*.md")),
        ("yt-seo", "Título, descrição e tags", None),
        ("yt-thumb", "Miniaturas", None),
        ("yt-editor", "Conferência e pedidos de render", bool(pedidos_hoje)),
        ("render", "Render (Windows)", None),
        ("publicar", "Envio e agendamento", None),
        ("yt-publicador", "Conferência da tarde", tem("publicacao.md")),
    ]
    return {"data": hoje, "pasta": str(d), "passos": [{"agente": a, "nome": n, "feito": f} for a, n, f in passos],
            "resumo": (d / "resumo.md").read_text(encoding="utf-8") if (d / "resumo.md").exists() else None,
            "pedidos": len(pedidos_hoje)}


def tudo():
    log = DADOS / "agente.log"
    linhas = log.read_text(encoding="utf-8", errors="replace").splitlines()[-300:] if log.exists() else []
    return {"agora": time.time(), "canais": canais(), "producao": producao(), "log": linhas[::-1],
            "tarefas": tarefas(), "agentes": agentes(), "rodada": rodada()}


def detalhe(canal, id_):
    pasta = FILA / canal / id_
    trab = pasta / "_trabalho"
    ep = ler_json(RAIZ / "episodios" / canal / f"{id_}.json") or ler_json(pasta / "roteiro.json") or {}
    final = ler_json(pasta / "roteiro.json") or {}
    item = ler_json(pasta / "item.json")
    conf = [url_arquivo(q) for q in sorted(trab.glob("confere_*.png"))]
    logs = []
    for nome in (f"_render_{id_}.log", f"_f_{canal[:3]}.log", f"_r_{canal[:3]}.log", f"_app_{canal}_{id_}.log"):
        q = DADOS / nome
        if q.exists() and id_ in q.read_text(encoding="utf-8", errors="replace")[:4000] or nome.startswith(("_app", "_render")):
            if q.exists():
                logs.append({"nome": nome, "texto": q.read_text(encoding="utf-8", errors="replace")[-6000:]})
    return {"roteiro": ep, "final": final, "item": item, "status": ler_json(trab / "status.json"),
            "confere": [c for c in conf if c], "imagens": url_arquivo(trab / "imagens.jpg"),
            "thumb": url_arquivo(pasta / "thumb.jpg") or url_arquivo(pasta / "thumb.png"),
            "video": url_arquivo(pasta / "video.mp4"), "legendas": url_arquivo(pasta / "legendas.srt"),
            "logs": logs}


# ---------------- ações ----------------
def rodar_bg(args, log_nome):
    log = open(DADOS / log_nome, "w", encoding="utf-8")
    return subprocess.Popen([str(PY), "-u", *args], cwd=RAIZ, env=ENV, stdout=log, stderr=subprocess.STDOUT,
                            creationflags=SEM_JANELA)


def acao(c):
    a, canal, id_ = c.get("acao"), c.get("canal"), c.get("id")
    if a in ("aprovar", "recusar"):
        for it in itens(canal):
            if it["id"] == id_ and it["estado"] == "enviado":
                mudar(it, "aprovado" if a == "aprovar" else "recusado", "via Estúdio")
                rodar_bg(["publicar.py"], "_app_publicar.log")
                return {"ok": True, "msg": "Aprovado: vou agendar no próximo horário bom." if a == "aprovar"
                        else "Marcado para refazer na próxima rodada do agente."}
        return {"erro": "Esse vídeo não está aguardando decisão."}
    if a == "vetar":  # modo independente: o dono barra um vídeo já aprovado/agendado
        for it in itens(canal):
            if it["id"] == id_ and it["estado"] in ("aprovado", "agendado", "pronto"):
                if it.get("youtube_id"):
                    from lib.yt import api
                    yt = api(canal)
                    st = yt.videos().list(part="status", id=it["youtube_id"]).execute()["items"][0]["status"]
                    st.update(privacyStatus="private", publishAt=None)
                    yt.videos().update(part="status", body={"id": it["youtube_id"], "status": st}).execute()
                mudar(it, "recusado", "vetado pelo dono no Estúdio (fica privado, nada apagado)")
                return {"ok": True, "msg": "Vetado: o vídeo fica privado e sai da agenda. Nada foi apagado."}
        return {"erro": "Só dá para vetar vídeo pronto, aprovado ou agendado."}
    if a in ("conferir", "renderizar"):
        if any(p["etapa"] in ("renderizando", "conferindo") for p in producao()):
            return {"erro": "Já tem um render rodando. Espere terminar (o computador renderiza um por vez)."}
        arq = RAIZ / "episodios" / canal / f"{id_}.json"
        if not arq.exists() or "cenas" not in (ler_json(arq) or {}):
            return {"erro": "Roteiro não encontrado no formato do motor_pro."}
        if a == "renderizar" and (FILA / canal / id_ / "item.json").exists():
            return {"erro": "Esse vídeo já está na fila. Para refazer, recuse-o primeiro."}
        rodar_bg(["motor_pro/render.py", str(arq), "--rapido" if a == "conferir" else "--fila"],
                 f"_app_{canal}_{id_}.log")
        return {"ok": True, "msg": "Conferência iniciada (voz, imagens, miniatura e 3 quadros)." if a == "conferir"
                else "Render final iniciado. Acompanhe a barra de progresso."}
    if a in ("coletar", "publicar"):
        rodar_bg([f"{a}.py"], f"_app_{a}.log")
        return {"ok": True, "msg": "Coletando métricas do YouTube…" if a == "coletar" else "Rodando a fila agora…"}
    if a == "abrir":
        alvo = FILA / canal / id_ if id_ else RAIZ
        os.startfile(str(alvo if alvo.exists() else RAIZ))
        return {"ok": True}
    if a == "abrir_arquivo":
        alvo = (RAIZ / c.get("caminho", "")).resolve()
        if RAIZ in alvo.parents and alvo.exists():
            os.startfile(str(alvo))
            return {"ok": True}
        return {"erro": "arquivo fora do projeto"}
    if a == "studio":
        webbrowser.open(f"https://studio.youtube.com/video/{c.get('youtube_id')}/edit")
        return {"ok": True}
    return {"erro": f"ação desconhecida: {a}"}


# ---------------- servidor ----------------
ULTIMO = [time.time()]  # última consulta da janela


class H(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def _json(self, obj, code=200):
        b = json.dumps(obj, ensure_ascii=False).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(b)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(b)

    def do_GET(self):
        u = urlparse(self.path)
        ULTIMO[0] = time.time()
        q = {k: v[0] for k, v in parse_qs(u.query).items()}
        try:
            if u.path == "/api/tudo":
                return self._json(tudo())
            if u.path == "/api/item":
                return self._json(detalhe(q["canal"], q["id"]))
            if u.path == "/api/ping":
                return self._json({"ok": True})
            if u.path.startswith("/f/"):
                alvo = (RAIZ / unquote(u.path[3:])).resolve()
                if RAIZ not in alvo.parents or not alvo.is_file():
                    return self._json({"erro": "não encontrado"}, 404)
                return self._servir(alvo)
            alvo = (UI / (u.path.lstrip("/") or "index.html")).resolve()
            if UI in alvo.parents and alvo.is_file():
                return self._servir(alvo)
            self._json({"erro": "não encontrado"}, 404)
        except (BrokenPipeError, ConnectionResetError):
            pass

    def do_POST(self):
        try:
            corpo = json.loads(self.rfile.read(int(self.headers.get("Content-Length", 0)) or 0) or "{}")
            if urlparse(self.path).path == "/api/acao":
                r = acao(corpo)
                return self._json(r, 200 if r.get("ok") else 400)
            self._json({"erro": "não encontrado"}, 404)
        except Exception as e:
            self._json({"erro": str(e)}, 500)

    def _servir(self, p):
        tam = p.stat().st_size
        tipo = mimetypes.guess_type(p.name)[0] or "application/octet-stream"
        if p.suffix in (".srt", ".md", ".log"):
            tipo = "text/plain; charset=utf-8"
        rng = self.headers.get("Range")
        ini, fim = 0, tam - 1
        if rng and rng.startswith("bytes="):
            a, b = rng[6:].split("-")
            ini = int(a or 0)
            fim = min(int(b), tam - 1) if b else tam - 1
            self.send_response(206)
            self.send_header("Content-Range", f"bytes {ini}-{fim}/{tam}")
        else:
            self.send_response(200)
        self.send_header("Content-Type", tipo)
        self.send_header("Accept-Ranges", "bytes")
        self.send_header("Content-Length", str(fim - ini + 1))
        if p.parent == UI:
            self.send_header("Cache-Control", "no-store")
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


def porta_ocupada():
    with socket.socket() as s:
        return s.connect_ex(("127.0.0.1", PORTA)) == 0


def edge():
    for base in (os.environ.get("ProgramFiles(x86)", r"C:\Program Files (x86)"),
                 os.environ.get("ProgramFiles", r"C:\Program Files"), os.environ.get("LOCALAPPDATA", "")):
        p = Path(base) / "Microsoft/Edge/Application/msedge.exe"
        if p.exists():
            return str(p)
    return None


def janela():
    """Abre a janela do app (Edge modo app, perfil próprio) e devolve o processo."""
    exe = edge()
    url = f"http://127.0.0.1:{PORTA}/"
    if not exe:
        webbrowser.open(url)
        return None
    perfil = Path(os.environ.get("LOCALAPPDATA", str(AQUI))) / "EstudioCanais" / "perfil"
    perfil.mkdir(parents=True, exist_ok=True)
    return subprocess.Popen([exe, f"--app={url}", f"--user-data-dir={perfil}", "--window-size=1440,900",
                             "--no-first-run", "--no-default-browser-check", "--disable-features=Translate",
                             "--disable-background-timer-throttling", "--disable-renderer-backgrounding",
                             "--disable-backgrounding-occluded-windows"])


def main():
    if porta_ocupada():  # já está aberto: só traz outra janela
        janela()
        return
    srv = ThreadingHTTPServer(("127.0.0.1", PORTA), H)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    if "--sem-janela" in sys.argv:
        print(f"Estúdio em http://127.0.0.1:{PORTA}/")
        threading.Event().wait()
    proc = janela()
    if proc is None:
        threading.Event().wait()
    proc.wait()
    # o Edge pode entregar a janela a outro processo: o app fecha quando a janela para de consultar (45 s)
    while time.time() - ULTIMO[0] < 45:
        time.sleep(2)
    srv.shutdown()


if __name__ == "__main__":
    main()
