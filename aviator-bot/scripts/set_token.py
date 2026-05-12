"""Atualiza o token do BotFather no arquivo .env com segurança.

Uso:
  python scripts/set_token.py 123456:ABC...
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ENV_PATH = ROOT / ".env"
KEY = "TELEGRAM_BOT_TOKEN"


def main() -> int:
    if len(sys.argv) != 2 or ":" not in sys.argv[1]:
        print("Uso: python scripts/set_token.py SEU_TOKEN_DO_BOTFATHER")
        return 2

    token = sys.argv[1].strip()
    lines = ENV_PATH.read_text(encoding="utf-8").splitlines() if ENV_PATH.exists() else []
    updated = False
    output: list[str] = []
    for line in lines:
        if line.startswith(f"{KEY}="):
            output.append(f"{KEY}={token}")
            updated = True
        else:
            output.append(line)
    if not updated:
        output.append(f"{KEY}={token}")

    ENV_PATH.write_text("\n".join(output) + "\n", encoding="utf-8")
    print("Token atualizado em .env. Não envie este arquivo com token real para repositórios públicos.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
