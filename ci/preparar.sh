#!/usr/bin/env bash
# Prepara o servidor do GitHub Actions: ffmpeg, Python, EffectCraft (Linux), fontes e as credenciais (Secrets).
set -euo pipefail
sudo apt-get update -qq
sudo apt-get install -y -qq ffmpeg fontconfig libfuse2 >/dev/null
python -m pip install -q -r requirements.txt
# EffectCraft (clone open-source do After Effects) - versão Linux
mkdir -p "$HOME/craft"
if [ ! -x "$HOME/craft/bin/effectcraft-cli" ]; then
  gh release download -R storytold/effectcraft -p "*linux-x86_64.tar.gz" -D /tmp/ec --clobber
  mkdir -p /tmp/ec/x && tar -xzf /tmp/ec/*.tar.gz -C /tmp/ec/x
  mkdir -p "$HOME/craft/bin"
  cp -r /tmp/ec/x/* "$HOME/craft/"
  ln -sf "$(find "$HOME/craft" -name effectcraft-cli -type f | head -1)" "$HOME/craft/bin/effectcraft-cli"
fi
chmod +x "$HOME"/craft/bin/* || true
echo "$HOME/craft/bin" >> "$GITHUB_PATH"
echo "CRAFT_DIR=$HOME/craft" >> "$GITHUB_ENV"
# fontes do canal (OFL)
mkdir -p "$HOME/.local/share/fonts" && cp fonts/*.ttf "$HOME/.local/share/fonts/" && fc-cache -f >/dev/null
# credenciais do YouTube (Secrets em base64) - nunca ficam no repositório
mkdir -p credenciais
echo "$YT_CLIENT_SECRET" | base64 -d > credenciais/client_secret.json
echo "$YT_TOKEN_GTA6" | base64 -d > credenciais/token_gta6.json
echo "$YT_TOKEN_ENGENHOSO" | base64 -d > credenciais/token_engenhoso.json
[ -n "${TELEGRAM_TOKEN:-}" ] && echo "TELEGRAM_TOKEN=$TELEGRAM_TOKEN" > .env || true
"$HOME/craft/bin/effectcraft-cli" info --empty >/dev/null 2>&1 && echo "EffectCraft OK" || echo "AVISO: effectcraft-cli não respondeu"
