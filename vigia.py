"""Vigia de novidades oficiais: confere de hora em hora os canais oficiais e avisa quando sai vídeo novo do tema.

Roda pelo Agendador do Windows (AgentesYouTube\\Vigia, a cada 60 min). Vídeo novo relevante:
  - baixa no acervo (acervo.py baixar) para as cenas ficarem prontas;
  - grava producao/alertas/<id>.json (o maestro e o radar tratam alerta como PRIORIDADE MÁXIMA);
  - escreve "NOVIDADE OFICIAL" no dados/agente.log e avisa no Telegram (se configurado).
"""
import json
import subprocess
import sys

from lib import telegram
from lib.comum import DADOS, RAIZ, SEM_JANELA, agora, log

sys.path.insert(0, str(RAIZ / "motor_pro"))
import acervo  # noqa: E402

# o que conta como "do nosso tema" em cada canal (título do vídeo oficial)
TEMAS = {"gta6": ["grand theft auto vi", "gta vi", "gta 6"],
         "engenhoso": ["artemis", "starship"]}
ESTADO = DADOS / "vigia.json"


def main():
    visto = json.loads(ESTADO.read_text(encoding="utf-8")) if ESTADO.exists() else {}
    primeira_vez = not visto
    alertas = RAIZ / "producao" / "alertas"
    alertas.mkdir(parents=True, exist_ok=True)
    for canal, chaves in TEMAS.items():
        for f in acervo.fontes().get(canal, []):
            if f["nome"].startswith("Netflix"):
                continue  # Netflix publica demais; entra só quando o radar pedir
            r = subprocess.run([sys.executable, "-m", "yt_dlp", "--no-warnings", "--flat-playlist", "-J",
                                "--playlist-items", "1-5", f"{f['url']}/videos"], capture_output=True, text=True,
                               encoding="utf-8", timeout=120, creationflags=SEM_JANELA)
            try:
                entradas = json.loads(r.stdout).get("entries") or []
            except Exception:
                continue
            for e in entradas:
                vid, titulo = e["id"], e.get("title") or ""
                if vid in visto:
                    continue
                visto[vid] = {"canal": canal, "fonte": f["nome"], "titulo": titulo, "visto": agora()}
                if primeira_vez or not any(k in titulo.lower() for k in chaves):
                    continue
                try:
                    acervo.baixar(canal, vid)
                    baixado = True
                except SystemExit as erro:
                    baixado = str(erro)
                alerta = {"canal": canal, "video": vid, "titulo": titulo, "fonte": f["nome"], "quando": agora(),
                          "baixado": baixado, "url": f"https://www.youtube.com/watch?v={vid}"}
                (alertas / f"{vid}.json").write_text(json.dumps(alerta, ensure_ascii=False, indent=2), encoding="utf-8")
                log(canal, f"NOVIDADE OFICIAL: {f['nome']} publicou '{titulo}' ({vid}) - alerta para a esteira")
                telegram.avisar(f"🚨 [{canal}] {f['nome']} publicou: {titulo} — https://youtu.be/{vid}")
    ESTADO.write_text(json.dumps(visto, ensure_ascii=False, indent=1), encoding="utf-8")


if __name__ == "__main__":
    main()
