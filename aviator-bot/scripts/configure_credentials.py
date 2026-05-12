"""Configura credenciais do Telegram/Gemini em um único comando.

Por padrão grava no `.env` local (mais seguro). Com `--github-config`, grava em
`config/bots.json` para quem quer gerir tudo pelo GitHub privado.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ENV_PATH = ROOT / ".env"
BOTS_PATH = ROOT / "config" / "bots.json"


def update_env(telegram_token: str | None, gemini_key: str | None) -> None:
    lines = ENV_PATH.read_text(encoding="utf-8").splitlines() if ENV_PATH.exists() else []
    values = {}
    if telegram_token:
        values["TELEGRAM_BOT_TOKEN"] = telegram_token
    if gemini_key is not None:
        values["GEMINI_API_KEY"] = gemini_key

    written = set()
    output: list[str] = []
    for line in lines:
        key = line.split("=", 1)[0] if "=" in line else ""
        if key in values:
            output.append(f"{key}={values[key]}")
            written.add(key)
        else:
            output.append(line)
    for key, value in values.items():
        if key not in written:
            output.append(f"{key}={value}")

    ENV_PATH.write_text("\n".join(output) + "\n", encoding="utf-8")


def update_bots_json(telegram_token: str | None, gemini_key: str | None, bot_name: str) -> None:
    data = json.loads(BOTS_PATH.read_text(encoding="utf-8")) if BOTS_PATH.exists() else {"bots": []}
    data["active_bot"] = bot_name
    bots = data.setdefault("bots", [])
    active_bot = next((bot for bot in bots if bot.get("name") == bot_name), None)
    if not active_bot:
        active_bot = {"name": bot_name, "telegram_token": "CHANGE_ME", "gemini_api_key": "", "active": True}
        bots.append(active_bot)

    for bot in bots:
        bot["active"] = bot.get("name") == bot_name
    if telegram_token:
        active_bot["telegram_token"] = telegram_token
    if gemini_key is not None:
        active_bot["gemini_api_key"] = gemini_key

    BOTS_PATH.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Configura credenciais do Aviator Bot em um comando.")
    parser.add_argument("--telegram-token", help="Token do BotFather.")
    parser.add_argument("--gemini-key", default=None, help="API key do Gemini opcional.")
    parser.add_argument("--bot-name", default="principal", help="Nome do bot ativo em config/bots.json.")
    parser.add_argument(
        "--github-config",
        action="store_true",
        help="Grava em config/bots.json em vez do .env local.",
    )
    args = parser.parse_args()

    if not args.telegram_token and args.gemini_key is None:
        parser.error("Informe --telegram-token e/ou --gemini-key.")

    if args.github_config:
        update_bots_json(args.telegram_token, args.gemini_key, args.bot_name)
        print("✅ Credenciais atualizadas em config/bots.json.")
    else:
        update_env(args.telegram_token, args.gemini_key)
        print("✅ Credenciais atualizadas no .env local.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
