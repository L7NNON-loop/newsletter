"""Painel de status amigável para Termux."""
from __future__ import annotations

import logging

logger = logging.getLogger("aviator-status")

RESET = "\033[0m"
BOLD = "\033[1m"
GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
CYAN = "\033[96m"
MAGENTA = "\033[95m"


def color(text: str, ansi: str) -> str:
    return f"{ansi}{text}{RESET}"


def icon(ok: bool) -> str:
    return color("✅", GREEN) if ok else color("🛑", RED)


def send_icon(ok: bool | None) -> str:
    if ok is None:
        return color("AGUARDANDO", YELLOW)
    return icon(ok)


def panel(
    *,
    server_online: bool,
    total_groups_online: int,
    bot_connected: bool,
    sending_ok: bool | None,
    last_candle: float | None = None,
    note: str | None = None,
) -> None:
    candle = "--" if last_candle is None else f"{last_candle:.2f}x"
    lines = [
        "",
        color("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━", CYAN),
        color("🤖 AVIATOR AI SYSTEM | TERMUX STATUS", BOLD + MAGENTA),
        color("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━", CYAN),
        f"Servidor de sinais: {icon(server_online)}",
        f"Total de grupos online: {color(str(total_groups_online), GREEN if total_groups_online else RED)}",
        f"BotConectado: {color('[1]', GREEN) if bot_connected else color('[0]', RED)}",
        f"Enviando mensagem: {send_icon(sending_ok)}",
        f"Última vela: {color(candle, YELLOW)}",
    ]
    if note:
        lines.append(f"Nota: {color(note, YELLOW)}")
    lines.append(color("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━", CYAN))
    logger.info("\n".join(lines))


def signal_detected(after: float, protection: float, exit_value: float) -> None:
    logger.info(
        "\n%s\n%s\n%s\n%s",
        color("⚡ SINAL DETECTADO", BOLD + GREEN),
        color(f"📊 APÓS: {after:.2f}x", CYAN),
        color(f"🛡 PROTEÇÃO: {protection:.2f}x", YELLOW),
        color(f"🔥 SAÍDA: {exit_value:.2f}x", GREEN),
    )


def quiz_started(manual: bool) -> None:
    origin = "MANUAL PELO ADM" if manual else "AUTOMÁTICO"
    logger.info("%s", color(f"🧠 QUIZ {origin} INICIADO", BOLD + MAGENTA))
