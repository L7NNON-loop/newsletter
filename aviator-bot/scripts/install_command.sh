#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."
COMMAND_PATH="${PREFIX:-/data/data/com.termux/files/usr}/bin/codex"
PROJECT_DIR="$(pwd)"

cat > "$COMMAND_PATH" <<EOF_CMD
#!/usr/bin/env bash
set -euo pipefail
cd "$PROJECT_DIR"
case "\${1:-start}" in
  start)
    bash scripts/start_termux.sh
    ;;
  stop)
    bash scripts/stop_termux.sh
    ;;
  restart)
    bash scripts/stop_termux.sh
    bash scripts/start_termux.sh
    ;;
  update)
    git pull --ff-only
    ;;
  logs)
    tail -f logs/aviator-bot.log
    ;;
  status)
    if [ -f .bot.pid ] && kill -0 "\$(cat .bot.pid)" >/dev/null 2>&1; then
      echo "✅ Aviator Bot rodando | PID \$(cat .bot.pid)"
    else
      echo "🛑 Aviator Bot parado"
    fi
    ;;
  *)
    echo "Uso: codex {start|stop|restart|update|logs|status}"
    exit 2
    ;;
esac
EOF_CMD

chmod +x "$COMMAND_PATH"
echo "✅ Comando instalado: codex start"
