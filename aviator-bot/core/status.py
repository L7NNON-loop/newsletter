"""Painel de status amigável para Termux."""
from __future__ import annotations

import logging

logger = logging.getLogger("aviator-status")


def icon(ok: bool) -> str:
    return "✅" if ok else "🛑"


def panel(
    *,
    server_online: bool,
    total_groups_online: int,
    bot_connected: bool,
    sending_ok: bool | None,
    last_candle: float | None = None,
    note: str | None = None,
) -> None:
    sending = "AGUARDANDO" if sending_ok is None else icon(sending_ok)
    candle = "--" if last_candle is None else f"{last_candle:.2f}x"
    lines = [
        "",
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━",
        "🤖 AVIATOR AI SYSTEM | TERMUX STATUS",
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━",
        f"Servidor de sinais: {icon(server_online)}",
        f"Total de grupos online: {total_groups_online}",
        f"BotConectado: [{1 if bot_connected else 0}]",
        f"Enviando mensagem: {sending}",
        f"Última vela: {candle}",
    ]
    if note:
        lines.append(f"Nota: {note}")
    lines.append("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    logger.info("\n".join(lines))
