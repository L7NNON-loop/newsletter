"""Entry point do Aviator AI System.

Execute com: python bot.py
"""
from __future__ import annotations

import asyncio
import json
import logging
import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

from core.api import AviatorAPIClient, AviatorAPIError
from core.signals import Signal, SignalEngine
from core.status import panel, signal_detected
from core.strategy_ai import AdaptiveStrategyAI
from core.telegram import TelegramService
from core.ui import generate_green_image

ROOT = Path(__file__).resolve().parent


@dataclass(slots=True)
class RuntimeState:
    enabled: bool = True
    last_candle: float | None = None
    candles_since_signal: int = 999
    pending_signal: Signal | None = None
    pending_age: int = 0
    last_signal: Signal | None = None


def load_settings() -> dict:
    settings_path = ROOT / "config" / "settings.json"
    return json.loads(settings_path.read_text(encoding="utf-8"))


def load_bot_credentials() -> tuple[str, str | None]:
    """Carrega credenciais por .env ou por config/bots.json.

    Prioridade:
    1. TELEGRAM_BOT_TOKEN/GEMINI_API_KEY no .env ou variáveis de ambiente.
    2. Bot ativo em config/bots.json, útil para configurar tudo pelo GitHub.
    """
    env_token = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
    env_gemini = os.getenv("GEMINI_API_KEY", "").strip() or None
    if env_token and env_token != "CHANGE_ME":
        return env_token, env_gemini

    bots_path = ROOT / "config" / "bots.json"
    if not bots_path.exists():
        return env_token, env_gemini

    data = json.loads(bots_path.read_text(encoding="utf-8"))
    active_name = data.get("active_bot")
    bots = data.get("bots", [])
    active_bot = next(
        (bot for bot in bots if bot.get("active") and (not active_name or bot.get("name") == active_name)),
        None,
    )
    if not active_bot:
        active_bot = next((bot for bot in bots if bot.get("active")), None)
    if not active_bot:
        return env_token, env_gemini

    token = str(active_bot.get("telegram_token", "")).strip()
    gemini_key = str(active_bot.get("gemini_api_key", "")).strip() or env_gemini
    return token, gemini_key


def setup_logging(logs_dir: str, level: str, telegram_http_logs: bool = False) -> None:
    log_dir = ROOT / logs_dir
    log_dir.mkdir(parents=True, exist_ok=True)
    logging.basicConfig(
        level=getattr(logging, level.upper(), logging.INFO),
        format="%(asctime)s | %(message)s",
        handlers=[
            logging.FileHandler(log_dir / "aviator-bot.log", encoding="utf-8"),
            logging.StreamHandler(),
        ],
    )
    if not telegram_http_logs:
        logging.getLogger("httpx").setLevel(logging.WARNING)
        logging.getLogger("telegram").setLevel(logging.WARNING)
        logging.getLogger("telegram.ext").setLevel(logging.WARNING)


async def main() -> None:
    load_dotenv(ROOT / ".env")
    settings = load_settings()
    setup_logging(
        settings.get("logs_dir", "logs"),
        os.getenv("LOG_LEVEL", "INFO"),
        bool(settings.get("telegram_http_logs", False)),
    )
    logger = logging.getLogger("aviator-bot")

    token, _ = load_bot_credentials()
    if not token or token == "CHANGE_ME":
        raise RuntimeError(
            "Configure o token no .env ou em config/bots.json antes de iniciar o bot."
        )

    ai = AdaptiveStrategyAI(ROOT / settings["ai_state_path"])
    engine = SignalEngine(
        ai=ai,
        min_candles=int(settings["min_candles"]),
        players_min=int(settings["players_min"]),
        players_max=int(settings["players_max"]),
    )
    api = AviatorAPIClient(settings["api_url"], timeout=float(settings["api_timeout_seconds"]))
    telegram = TelegramService(
        token=token,
        groups_path=ROOT / "config" / "groups.json",
        links_path=ROOT / "config" / "links.json",
        bot_name=settings["bot_name"],
        monitor_all_chats=bool(settings.get("monitor_all_chats", True)),
        admin_user_id=int(settings.get("admin_user_id")) if settings.get("admin_user_id") else None,
    )
    state = RuntimeState()
    async def set_enabled(enabled: bool) -> None:
        state.enabled = enabled
        logger.info("%s Sistema %s via grupo", "✅" if enabled else "🛑", "ativado" if enabled else "pausado")
        panel(
            server_online=state.enabled,
            total_groups_online=len(telegram.online_group_ids),
            bot_connected=telegram.bot_connected,
            sending_ok=telegram.last_send_ok,
            last_candle=state.last_candle,
        )

    telegram.set_state_callback(set_enabled)
    await telegram.start()
    online_groups = await telegram.refresh_online_groups()
    panel(
        server_online=state.enabled,
        total_groups_online=online_groups,
        bot_connected=telegram.bot_connected,
        sending_ok=None,
        note="Envie /id no grupo se aparecer Chat not found.",
    )
    if bool(settings.get("startup_audio_enabled", True)):
        await telegram.broadcast_startup_audio(
            settings.get(
                "startup_audio_text",
                "Olá caros apostadores, criem a vossa conta e sigam as entradas confirmadas.",
            )
        )

    try:
        while True:
            await asyncio.sleep(float(settings["poll_interval_seconds"]))
            if not state.enabled:
                continue

            try:
                snapshot = await api.fetch_candles()
            except AviatorAPIError:
                continue

            latest = snapshot.latest
            if state.last_candle is not None and latest == state.last_candle:
                continue

            previous = state.last_candle if state.last_candle is not None else latest
            state.last_candle = latest
            state.candles_since_signal += 1
            logger.info("🎯 Nova vela detectada: %.2fx", latest)

            last_signal = getattr(state, "last_signal", None)
            if last_signal and latest >= last_signal.exit:
                await telegram.broadcast_green(latest, previous, last_signal, generate_green_image(latest, settings["bot_name"], ROOT / "assets" / "green_latest.png"))

            signal = engine.build_signal(snapshot.values)
            if signal is None:
                signal = engine.build_fallback_signal(snapshot.values)
            if signal:
                setattr(state, "last_signal", signal)
                signal_detected(signal.after, signal.protection, signal.exit)
                send_ok = await telegram.broadcast_signal(signal)
                panel(
                    server_online=state.enabled,
                    total_groups_online=len(telegram.online_group_ids),
                    bot_connected=telegram.bot_connected,
                    sending_ok=send_ok,
                    last_candle=latest,
                )
    finally:
        await api.close()
        await telegram.stop()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Bot finalizado pelo usuário.")
