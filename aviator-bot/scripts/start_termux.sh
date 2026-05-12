#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."

if git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
  echo "🔄 Atualizando configurações/código pelo GitHub..."
  git pull --ff-only || echo "⚠️ Não foi possível atualizar via git pull. Continuando com arquivos locais."
fi

if [ ! -d ".venv" ]; then
  echo "📦 Ambiente virtual não encontrado. Criando..."
  python -m venv .venv
fi

# shellcheck disable=SC1091
source .venv/bin/activate
pip install -r requirements.txt
python scripts/create_assets.py

echo "🚀 Iniciando Aviator AI System..."
python bot.py
