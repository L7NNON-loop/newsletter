#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."

pkg update -y
pkg install -y python git clang libjpeg-turbo zlib freetype

python -m venv .venv
# shellcheck disable=SC1091
source .venv/bin/activate
pip install --upgrade pip setuptools wheel
pip install --prefer-binary -r requirements.txt
touch .venv/.requirements.stamp
python scripts/create_assets.py
bash scripts/install_command.sh

echo "✅ Instalação concluída. Configure no GitHub, depois rode: bash scripts/start_termux.sh"
