#!/usr/bin/env bash
# Grava o estado (fila, pedidos, log) de volta no repositório, com nova tentativa se outro job gravou antes.
set -uo pipefail
git config user.name "estudio-bot"
git config user.email "estudio-bot@users.noreply.github.com"
git add -A producao fila dados acervo episodios canais 2>/dev/null || true
git diff --cached --quiet && { echo "nada a gravar"; exit 0; }
git commit -q -m "${1:-estado da produção}"
for i in 1 2 3 4 5; do
  git pull -q --rebase -X theirs origin "${GITHUB_REF_NAME:-main}" && git push -q && exit 0
  sleep $((i * 7))
done
echo "não consegui gravar o estado"; exit 1
