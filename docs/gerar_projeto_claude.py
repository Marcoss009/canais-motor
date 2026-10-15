"""Junta todo o conhecimento do projeto num arquivo só, para subir num Projeto do claude.ai (Projects → Add content).

Uso: python docs/gerar_projeto_claude.py   ->  Projeto_Claude/conhecimento_youtube_agentes.md
"""
import datetime as dt
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
AGENTES = Path.home() / ".claude" / "agents"
PARTES = [
    ("Memória do projeto (CLAUDE.md)", RAIZ / "CLAUDE.md"),
    ("Guia de uso (LEIA-ME.md)", RAIZ / "LEIA-ME.md"),
    ("Sistema de roteiro (motor_pro/ROTEIRO.md)", RAIZ / "motor_pro" / "ROTEIRO.md"),
    ("Bíblia — GTAzando", RAIZ / "canais" / "gta6" / "biblia.md"),
    ("Bíblia — Engenhoso", RAIZ / "canais" / "engenhoso" / "biblia.md"),
    ("Fontes oficiais de cenas", RAIZ / "acervo" / "fontes_oficiais.json"),
    ("Configuração (config.json)", RAIZ / "config.json"),
]


def main():
    saida = RAIZ / "Projeto_Claude" / "conhecimento_youtube_agentes.md"
    saida.parent.mkdir(exist_ok=True)
    blocos = [f"# Conhecimento do projeto Agentes de YouTube\n\nGerado em {dt.datetime.now():%d/%m/%Y %H:%M}. "
              "Suba este arquivo no Projeto do claude.ai; para atualizar, rode `python docs/gerar_projeto_claude.py`.\n"]
    for titulo, arq in PARTES:
        if arq.exists():
            txt = arq.read_text(encoding="utf-8")
            if arq.suffix == ".json":
                txt = f"```json\n{txt}\n```"
            blocos.append(f"\n---\n\n# {titulo}\n\n{txt}")
    blocos.append("\n---\n\n# A equipe de agentes (C:\\Users\\vinic\\.claude\\agents)\n")
    for arq in sorted(AGENTES.glob("yt-*.md")):
        blocos.append(f"\n## {arq.stem}\n\n{arq.read_text(encoding='utf-8')}")
    rodadas = sorted((RAIZ / "producao" / "rodadas").glob("*/resumo.md"))[-7:]
    if rodadas:
        blocos.append("\n---\n\n# Últimas rodadas diárias\n")
        for r in rodadas:
            blocos.append(f"\n## {r.parent.name}\n\n{r.read_text(encoding='utf-8')}")
    saida.write_text("\n".join(blocos), encoding="utf-8")
    print(saida, f"{saida.stat().st_size // 1024} KB")


if __name__ == "__main__":
    main()
