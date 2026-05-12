#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."
PID_FILE=".bot.pid"
trap 'bash scripts/stop_termux.sh >/dev/null 2>&1 || true' INT TERM
STAMP_FILE=".venv/.requirements.stamp"

if git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
  echo "🔄 Atualizando configurações/código pelo GitHub..."
  git pull --ff-only || echo "⚠️ Não foi possível atualizar via git pull. Continuando com arquivos locais."
fi

bash scripts/stop_termux.sh >/dev/null 2>&1 || true

if [ ! -d ".venv" ]; then
  echo "📦 Ambiente virtual não encontrado. Criando..."
  python -m venv .venv
fi

# shellcheck disable=SC1091
source .venv/bin/activate

if [ ! -f "$STAMP_FILE" ] || [ requirements.txt -nt "$STAMP_FILE" ]; then
  echo "📦 Instalando/atualizando dependências..."
  pip install --prefer-binary -r requirements.txt
  mkdir -p .venv
  touch "$STAMP_FILE"
else
  echo "✅ Dependências já instaladas. Pulando reinstalação."
fi

python scripts/create_assets.py
bash scripts/install_command.sh >/dev/null 2>&1 || true

echo "🚀 Iniciando Aviator AI System..."
python bot.py &
echo $! > "$PID_FILE"
wait "$(cat "$PID_FILE")"
