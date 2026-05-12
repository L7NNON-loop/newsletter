#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."
PID_FILE=".bot.pid"

if [ -f "$PID_FILE" ]; then
  PID="$(cat "$PID_FILE" || true)"
  if [ -n "${PID:-}" ] && kill -0 "$PID" >/dev/null 2>&1; then
    echo "🛑 Parando instância anterior do Aviator Bot (PID $PID)..."
    kill "$PID" >/dev/null 2>&1 || true
    sleep 2
    kill -9 "$PID" >/dev/null 2>&1 || true
  fi
  rm -f "$PID_FILE"
fi

if command -v pkill >/dev/null 2>&1; then
  pkill -f '[p]ython.*bot.py' >/dev/null 2>&1 || true
fi

echo "✅ Bot parado."
