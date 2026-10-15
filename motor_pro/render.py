"""Motor profissional (grátis): roteiro -> voz própria do canal -> cenas animadas no EffectCraft -> miniatura
(EffectCraft + PhotoCraft) -> descrição com capítulos, fontes e créditos -> fila de aprovação.

Uso: python motor_pro/render.py episodios/<canal>/<id>.json [--fila] [--rapido]
  --rapido  renderiza só a miniatura e 3 quadros de conferência (sem o vídeo inteiro)

Formato do roteiro: ver motor_pro/ROTEIRO.md
"""
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

import numpy as np

AQUI = Path(__file__).resolve().parent
RAIZ = AQUI.parent
sys.path.insert(0, str(RAIZ))
sys.path.insert(0, str(AQUI))
from lib.comum import FILA, config, novo_item  # noqa: E402
import acervo  # noqa: E402
import imagens  # noqa: E402
import trilha  # noqa: E402
import voz  # noqa: E402

CRAFT = Path.home() / "AppData/Local/Programs/ArtCraft"


def craft(app, obrigatorio=True):
    """Windows: versão portátil em %LOCALAPPDATA%/Programs/ArtCraft. Linux (nuvem): <app>-cli no PATH ou CRAFT_DIR."""
    exe = sorted(CRAFT.glob(f"{app}/*/{app}-cli.exe"))
    if exe:
        return str(exe[-1])
    achado = shutil.which(f"{app}-cli")
    if not achado and os.environ.get("CRAFT_DIR"):
        cand = sorted(Path(os.environ["CRAFT_DIR"]).glob(f"**/{app}-cli"))
        achado = str(cand[-1]) if cand else None
    if achado or not obrigatorio:
        return achado
    raise SystemExit(f"{app}-cli não encontrado (Windows: {CRAFT}; Linux: PATH ou CRAFT_DIR)")


def ts(seg):
    seg = int(seg)
    return f"{seg // 3600}:{seg % 3600 // 60:02d}:{seg % 60:02d}" if seg >= 3600 else f"{seg // 60:02d}:{seg % 60:02d}"


def legendas(palavras, cenas, max_pal=3, max_chars=18):
    """Agrupa palavras em blocos curtos (estilo Shorts). Destaca números e palavras marcadas na cena."""
    destaques = set()
    for c in cenas:
        for w in c.get("destaques", []):
            destaques.add(w.lower())
    blocos, atual = [], []
    for p in palavras:
        atual.append(p)
        txt = " ".join(w for _, _, w in atual)
        if len(atual) >= max_pal or len(txt) >= max_chars or re.search(r"[.!?,:;]$", p[2]):
            blocos.append(atual)
            atual = []
    if atual:
        blocos.append(atual)
    out = []
    for i, b in enumerate(blocos):
        ini = b[0][0]
        prox = blocos[i + 1][0][0] if i + 1 < len(blocos) else b[-1][1] + 0.4
        fim = min(prox, b[-1][1] + 0.35)
        txt = re.sub(r"[,;:]$", "", " ".join(w for _, _, w in b))
        d = any(re.search(r"\d", w) or w.lower().strip(".,!?") in destaques for _, _, w in b)
        out.append({"t": txt, "i": round(ini, 3), "f": round(fim, 3), "d": d})
    return out


def tratar(arq, tema, trab):
    """Cor do canal aplicada uma vez (no EffectCraft custaria ~45 ms por quadro) + tamanho certo pro 1080p."""
    from PIL import Image, ImageEnhance
    import hashlib
    pasta = trab / "img"
    pasta.mkdir(exist_ok=True)
    k = hashlib.sha1(f"{arq}|{tema.get('contraste')}|{tema.get('saturacao')}".encode()).hexdigest()[:12]
    out = pasta / f"{k}.jpg"
    if not out.exists():
        im = Image.open(arq).convert("RGB")
        if im.width > 2300:
            im = im.resize((2300, round(im.height * 2300 / im.width)), Image.LANCZOS)
        im = ImageEnhance.Contrast(im).enhance(1 + tema.get("contraste", 15) / 100)
        im = ImageEnhance.Color(im).enhance(1 + tema.get("saturacao", 10) / 100)
        im.save(out, quality=93)
    return str(out)


def entregar(canal, ep, pasta, desc):
    """Cópia de entrega em Entregas/<canal>/<id>/ (link físico: não ocupa espaço em dobro)."""
    import os
    dest = RAIZ / "Entregas" / canal / ep["id"]
    dest.mkdir(parents=True, exist_ok=True)
    for nome in ("video.mp4", "thumb.jpg", "legendas.srt"):
        a, b = pasta / nome, dest / nome
        if a.exists():
            b.unlink(missing_ok=True)
            try:
                os.link(a, b)
            except OSError:
                shutil.copy2(a, b)
    alt = "\n".join(f"  {i}. {t}" for i, t in enumerate(ep.get("titulos_alternativos", []), 1))
    texto = (f"TÍTULO\n{ep['titulo']}\n\nOUTROS TÍTULOS\n{alt}\n\nDESCRIÇÃO\n{desc}\n\n"
             f"TAGS\n{', '.join(ep.get('tags', []))}\n")
    (dest / "publicar.txt").write_text(texto, encoding="utf-8")
    return dest


def folha_imagens(dados_cenas, mini_foto, saida):
    """Folha de contato com cada foto usada e o número da cena: o agente olha antes do render final."""
    from PIL import Image, ImageDraw
    itens = [(f"thumb", mini_foto)] if mini_foto else []
    for i, c in enumerate(dados_cenas, 1):
        itens += [(f"cena {i}", f) for f in c["visual"].get("_fotos", [])]
    if not itens:
        return
    tw, th, cols = 320, 180, 6
    linhas = (len(itens) + cols - 1) // cols
    folha = Image.new("RGB", (tw * cols, (th + 22) * linhas), "white")
    d = ImageDraw.Draw(folha)
    for k, (rot, arq) in enumerate(itens):
        x, y = k % cols * tw, k // cols * (th + 22)
        try:
            im = Image.open(arq).convert("RGB")
            im.thumbnail((tw - 4, th - 4))
            folha.paste(im, (x + 2, y + 2))
        except Exception:
            pass
        d.text((x + 4, y + th + 4), rot, fill="black")
    folha.save(saida, quality=80)


def capitulos(cenas, tempos):
    caps = [(0.0, cenas[0].get("capitulo") or "Introdução")]
    for c, (ini, _) in zip(cenas[1:], tempos[1:]):
        if c.get("capitulo") and ini - caps[-1][0] >= 10:
            caps.append((ini, c["capitulo"]))
    return caps if len(caps) >= 3 else []


STATUS = None  # _trabalho/status.json: o app "Estúdio" acompanha a produção por ele
BYTES_POR_SEG = 12.1e6 / 8  # medido: o EffectCraft grava ~12,1 Mbps (--bitrate 12000): tamanho = progresso


def status(etapa, **kw):
    if not STATUS:
        return
    import time
    atual = {}
    if STATUS.exists():
        try:
            atual = json.loads(STATUS.read_text(encoding="utf-8"))
        except Exception:
            atual = {}
    if etapa != atual.get("etapa"):
        atual["desde"] = time.time()
    atual.update(kw, etapa=etapa, atualizado=time.time())
    STATUS.write_text(json.dumps(atual, ensure_ascii=False), encoding="utf-8")


def main():
    try:
        _main()
    except BaseException as e:
        status("erro", msg=str(e)[:300])
        raise


def _main():
    global STATUS
    arq = Path(sys.argv[1])
    ep = json.loads(arq.read_text(encoding="utf-8"))
    rapido = "--rapido" in sys.argv
    if os.name == "nt":
        # conferência em prioridade baixa (os filhos herdam): o render final nunca disputa a máquina com ela;
        # disputando, um longo passou de ~50 min para ~5 h em 15/10/2026
        import ctypes
        ctypes.windll.kernel32.SetPriorityClass(ctypes.windll.kernel32.GetCurrentProcess(),
                                                0x4000 if rapido else 0x8000)  # BELOW_NORMAL / ABOVE_NORMAL
    cfg = config()
    canal = ep["canal"]
    cc = cfg["canais"][canal]
    tema = json.loads((RAIZ / "canais" / canal / "tema.json").read_text(encoding="utf-8"))
    short = ep.get("formato") == "short"
    W, H = (1080, 1920) if short else (1920, 1080)
    pasta = FILA / canal / ep["id"]
    pasta.mkdir(parents=True, exist_ok=True)
    trab = pasta / "_trabalho"
    trab.mkdir(exist_ok=True)
    STATUS = trab / "status.json"
    import time as _t
    STATUS.write_text(json.dumps({"etapa": "voz", "modo": "rapido" if rapido else "final", "inicio": _t.time(),
                                  "desde": _t.time(), "pid": __import__("os").getpid(),
                                  "roteiro": str(arq)}), encoding="utf-8")

    # 1) voz
    cenas = ep["cenas"]
    print(f"[1/5] voz ({cc['persona']['voz']}, timbre {cc['persona'].get('timbre')}) - {len(cenas)} cenas")
    a_voz, tempos, palavras = voz.narrar([c["fala"] for c in cenas], cc["persona"])
    fim_fala = len(a_voz) / voz.SR
    TELA_FINAL = 0.0 if short else 12.0  # espaço para os elementos de tela final do YouTube
    if TELA_FINAL:
        a_voz = np.concatenate([a_voz, np.zeros(int(TELA_FINAL * voz.SR), np.float32)])
    total = len(a_voz) / voz.SR

    # 2) trilha + mix
    status("trilha", duracao=round(total, 1), cenas=len(cenas))
    print(f"[2/5] trilha {tema['trilha']} + mix ({total:.1f}s)")
    musica = trilha.gerar(tema["trilha"], total)
    cortes = [t[0] for t in tempos[1:]]
    mix = trilha.mixar(a_voz, musica, cortes, tema.get("vol_musica", 0.16))
    bruto = trab / "mix_bruto.wav"
    voz.salvar_wav(bruto, mix)
    audio = trab / "audio.wav"
    subprocess.run([cfg["ffmpeg"], "-y", "-loglevel", "error", "-i", str(bruto), "-af",
                    "loudnorm=I=-14:TP=-1.5:LRA=11", "-ar", "48000", "-ac", "2", str(audio)], check=True)

    # 3) imagens (grátis, com crédito)
    print("[3/5] imagens")
    status("imagens")
    usados, creditos = set(), []

    def pega(consulta):
        r = imagens.buscar(consulta, usados)
        if not r:
            print(f"  sem imagem para '{consulta}' (cena fica com fundo animado)")
            return None
        if r.get("id"):
            usados.add(r["id"])
        if r.get("credito") and r["credito"] not in creditos:
            creditos.append(r["credito"])
        return tratar(r["arquivo"], tema, trab).replace("\\", "/")

    dados_cenas = []
    oficiais, seg_oficiais = {}, 0.0
    for i, (c, (ini, fim)) in enumerate(zip(cenas, tempos)):
        v = dict(c.get("visual", {"tipo": "imagem"}))
        consultas = v.get("imagens") or ([v["imagem"]] if v.get("imagem") else [])
        v["_fotos"] = [f for f in (pega(q) for q in consultas) if f]
        if v.get("clipes"):  # cenas oficiais: [{"video": "<id do acervo>", "ini": 40.5}, ...]
            v["_clipes"] = []
            for c_ in v["clipes"]:
                arq_c, inf = acervo.cortar(c_["video"], c_["ini"], acervo.MAX_TRECHO)
                v["_clipes"].append(str(arq_c).replace("\\", "/"))
                oficiais.setdefault(inf["id"], inf)
                fontes_cena = inf["fonte"]
            v["_credito"] = f"Imagens: {fontes_cena}"
            seg_oficiais += ((tempos[i + 1][0] if i + 1 < len(tempos) else fim_fala) - (0 if i == 0 else ini))
        a = 0.0 if i == 0 else ini - 0.05
        b = tempos[i + 1][0] - 0.05 if i + 1 < len(tempos) else fim_fala
        dados_cenas.append({"ini": round(a, 3), "fim": round(b, 3), "visual": v})
    if TELA_FINAL:
        dados_cenas.append({"ini": round(fim_fala, 3), "fim": round(total, 3),
                            "visual": {"tipo": "telafinal", "texto": tema.get("tela_final", "Assista também"),
                                       "sub": ep.get("tela_final_sub", "")}})
    # limite de uso de cena oficial (comentário/crítica, não reupload)
    if seg_oficiais > 0.45 * fim_fala:
        raise SystemExit(f"cena oficial demais: {seg_oficiais:.0f}s de {fim_fala:.0f}s (máx. 45%). "
                         "Troque algumas cenas 'clipes' por imagens/gráficos.")
    mini = ep["miniatura"]
    if mini.get("quadro"):  # miniatura a partir de um quadro oficial: {"video": id, "t": 41.2}
        q_arq, inf = acervo.cortar(mini["quadro"]["video"], mini["quadro"]["t"], 1)
        png_q = trab / "quadro_thumb.png"
        subprocess.run([cfg["ffmpeg"], "-v", "error", "-y", "-i", str(q_arq), "-frames:v", "1", str(png_q)], check=True)
        mini_foto = str(png_q).replace("\\", "/")
        oficiais.setdefault(inf["id"], inf)
    else:
        mini_foto = pega(mini["imagem"]) if mini.get("imagem") else None
    folha_imagens(dados_cenas, mini_foto, trab / "imagens.jpg")

    # 4) projeto do EffectCraft
    print("[4/5] cenas no EffectCraft")
    status("cenas")
    projeto = trab / "projeto.ecproj"
    D = {"W": W, "H": H, "fps": 30, "total": round(total, 3), "tema": tema, "cenas": dados_cenas,
         "audio": str(audio).replace("\\", "/"), "projeto": str(projeto).replace("\\", "/"),
         "legendas": legendas(palavras, cenas) if short else None, "progresso": not short,
         "marca": tema.get("marca"),
         "miniatura": {"texto": mini["texto"], "selo": mini.get("selo"), "tam": mini.get("tam", 150),
                       "foto": mini_foto}}
    jsx = trab / "montar.jsx"
    jsx.write_text((AQUI / "cenas.jsx").read_text(encoding="utf-8") + "\nvar D = " +
                   json.dumps(D, ensure_ascii=False) + ";\nmontar(D);\n", encoding="utf-8")
    ec = craft("effectcraft")
    r = subprocess.run([ec, "script", str(jsx)], capture_output=True, text=True, encoding="utf-8")
    print("  " + (r.stdout.strip().splitlines() or ["?"])[-1])
    if r.returncode != 0 or not projeto.exists():
        print(r.stdout, r.stderr)
        raise SystemExit("falha no script do EffectCraft")

    # miniatura: EffectCraft desenha, PhotoCraft finaliza em JPG (< 2 MB, exigência do YouTube)
    png = trab / "thumb.png"
    subprocess.run([ec, "render-frame", str(projeto), "--comp", "Thumb", "--time", "1", "--out", str(png)],
                   check=True, capture_output=True)
    thumb = pasta / "thumb.jpg"
    pc = craft("photocraft", obrigatorio=False)
    if pc:
        subprocess.run([pc, "convert", str(png), str(thumb), "--quality", "92"], check=True, capture_output=True)
    else:  # sem PhotoCraft (nuvem): mesma conversão pelo PIL
        from PIL import Image
        Image.open(png).convert("RGB").save(thumb, quality=92)

    # quadros de conferência (o agente olha antes de mandar pra fila)
    conf = []
    for k, frac in enumerate((0.04, 0.4, 0.8)):
        q = trab / f"confere_{k}.png"
        subprocess.run([ec, "render-frame", str(projeto), "--comp", "Main", "--time", f"{total * frac:.2f}",
                        "--out", str(q), "--max-side", "960"], check=True, capture_output=True)
        conf.append(str(q))
    print("  conferir:", *conf, str(thumb), sep="\n   ")
    if rapido:
        status("conferencia")
        return

    # 5) render final
    print("[5/5] render final (EffectCraft, H.264 + AAC)")
    video = pasta / "video.mp4"
    status("render", pct=0)
    import time as _t
    t0 = _t.time()
    proc = subprocess.Popen([ec, "render", str(projeto), "--comp", "Main", "--out", str(video), "--format", "h264",
                             "--audio", "on", "--bitrate", "12000" if not short else "10000"],
                            stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, encoding="utf-8")
    while proc.poll() is None:
        _t.sleep(5)
        tam = video.stat().st_size if video.exists() else 0
        pct = min(0.99, tam / (BYTES_POR_SEG * total))
        gasto = _t.time() - t0
        status("render", pct=round(pct, 4), eta=round(gasto / pct - gasto) if pct > 0.02 else None)
    out, err = proc.communicate()
    print("  " + ((out or "").strip().splitlines() or ["?"])[-1])
    if proc.returncode != 0:
        print(err)
        raise SystemExit("falha no render")

    # descrição final: texto + capítulos + fontes + créditos
    desc = ep["descricao"].rstrip()
    caps = capitulos(cenas, tempos) if not short else []
    if caps:
        desc += "\n\n" + "\n".join(f"{ts(t)} {nome}" for t, nome in caps)
    if ep.get("fontes"):
        desc += "\n\nFontes:\n" + "\n".join(f"• {f}" for f in ep["fontes"])
    if oficiais:
        desc += ("\n\nCenas oficiais (trechos curtos, sem o áudio original, usados para comentário e análise; "
                 "direitos dos respectivos donos):\n" +
                 "\n".join(f"• {o['fonte']} — \"{o['title']}\" ({o['webpage_url']})" for o in oficiais.values()))
    if creditos:
        desc += "\n\nImagens (licenças livres):\n" + "\n".join(f"• {c}" for c in creditos)
    desc += "\n\nNarração com voz sintética e trilha original do canal."
    if ep.get("hashtags"):
        desc += "\n\n" + " ".join(ep["hashtags"])
    # legendas .srt (para subir como legenda no Studio, se quiser)
    srt = []
    for n, g in enumerate(legendas(palavras, cenas, max_pal=8, max_chars=42), 1):
        def f(x):
            return f"{int(x // 3600):02d}:{int(x % 3600 // 60):02d}:{int(x % 60):02d},{int(x * 1000 % 1000):03d}"
        srt.append(f"{n}\n{f(g['i'])} --> {f(g['f'])}\n{g['t']}\n")
    (pasta / "legendas.srt").write_text("\n".join(srt), encoding="utf-8")

    ep_final = dict(ep, descricao_final=desc, duracao=round(total, 1))
    (pasta / "roteiro.json").write_text(json.dumps(ep_final, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"OK: {video} ({total / 60:.1f} min)")
    print("Entrega:", entregar(canal, ep, pasta, desc))
    if "--fila" in sys.argv:
        it = novo_item(canal, ep["id"], ep.get("formato", "longo"), ep["titulo"], desc, ep.get("tags", []),
                       video, thumb, ep.get("nicho"), roteiro=str(pasta / "roteiro.json"))
        if "--slot" in sys.argv:  # horário pedido pela produção diária
            from lib.comum import salvar
            it["slot"] = sys.argv[sys.argv.index("--slot") + 1]
            salvar(it)
        print("Registrado na fila (estado: pronto).")
    status("concluido", pct=1)


if __name__ == "__main__":
    main()
