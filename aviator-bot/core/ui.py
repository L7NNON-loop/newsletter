"""Design premium das mensagens e imagens do bot."""
from __future__ import annotations

import struct
import zlib
from pathlib import Path

from core.signals import Signal

try:
    from PIL import Image, ImageDraw, ImageFont
except ImportError:  # Pillow é opcional para facilitar instalação no Termux/Python 3.13
    Image = ImageDraw = ImageFont = None

SEPARATOR = "━━━━━━━━━━━━━━━━━━━━━━"


def signal_message(signal: Signal, bot_name: str) -> str:
    confidence = max(70, min(99, signal.ai_percent if signal.ai_percent else 90))
    bars = "🟩" * max(1, min(5, round(confidence / 20))) + "⬜" * (5 - max(1, min(5, round(confidence / 20))))
    return (
        "🎰 <b>NEXUS AI📢</b> 🎰\n"
        "━━━━━━━━━━━━━━\n"
        "✅ <b>ENTRADA CONFIRMADA</b> ✅\n"
        '🚀 Aviator: <a href="https://media1.placard.co.mz/redirect.aspx?pid=4241&bid=1690"><b>Apostar agora</b></a>\n\n'
        f"📊 APÓS: {signal.after:.2f}x\n"
        f"🎯 Sacar em: {signal.exit:.2f}x\n"
        f"🛡 Proteção: {signal.protection:.2f}x\n\n"
        f"📊 Confiança: {confidence}% {bars}\n\n"
        f"🕐 Enviado às: {__import__('datetime').datetime.now().strftime('%H:%M:%S')}\n"
        "━━━━━━━━━━━━━━\n"
        "💫 Não tem conta? Registre-se no botão abaixo!!"
    )


def green_message(current: float, previous: float, signal: Signal, bot_name: str) -> str:
    extra = "\n\nWauuu, Que vela grande...😱😱😱" if current >= 20 else ""
    return (
        "✅ GREEN CONFIRMADO! Excelente entrada.\n\n"
        f"🎯 Multiplicador final: {current:.2f}x\n"
        f"🎯 Alvo previsto: {signal.exit:.2f}x\n"
        f"🛡 Proteção usada: {signal.protection:.2f}x"
        f"{extra}"
    )


def stopped_message() -> str:
    return "🛑 PARADO\n💻 SERVIDOR DESLIGADO"


def started_message() -> str:
    return "🟢 SISTEMA ATIVO\n💻 AVIATOR ONLINE"


def quiz_message(question: str = "Estão gostando dos sinais? 🎯") -> str:
    return f"🎯 {question}\n\nVote abaixo para calibrarmos a experiência."


def quiz_result_message(yes: int, no: int) -> str:
    total = max(yes + no, 1)
    yes_pct = round((yes / total) * 100, 1)
    no_pct = round((no / total) * 100, 1)
    return f"📊 RESULTADO DO QUIZ\n\n👍 SIM: {yes_pct}%\n👎 NÃO: {no_pct}%\n\n⚡ Sinais retomados."


def generate_green_image(current: float, bot_name: str, output_path: str | Path) -> Path:
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    if Image is None:
        _generate_fallback_green_png(output)
        return output

    width, height = 1000, 560
    image = Image.new("RGB", (width, height), "#020403")
    draw = ImageDraw.Draw(image)

    try:
        title_font = ImageFont.truetype("DejaVuSans-Bold.ttf", 54)
        value_font = ImageFont.truetype("DejaVuSans-Bold.ttf", 118)
        text_font = ImageFont.truetype("DejaVuSansMono.ttf", 30)
    except OSError:
        title_font = value_font = text_font = ImageFont.load_default()

    green = "#39ff88"
    dim = "#0f6b3c"
    for x in range(0, width, 40):
        draw.line((x, 0, x, height), fill="#03150c")
    for y in range(0, height, 40):
        draw.line((0, y, width, y), fill="#03150c")

    draw.rounded_rectangle((45, 45, width - 45, height - 45), radius=32, outline=green, width=4)
    draw.text((80, 92), "GREEN CONFIRMADO", fill=green, font=title_font)
    draw.text((80, 205), f"{current:.2f}x", fill=green, font=value_font)
    draw.text((84, 380), f"> {bot_name}", fill=green, font=text_font)
    draw.text((84, 430), "> TERMINAL AI MODE: ONLINE", fill=dim, font=text_font)

    image.save(output, format="PNG")
    return output


def _chunk(kind: bytes, data: bytes) -> bytes:
    return (
        struct.pack(">I", len(data))
        + kind
        + data
        + struct.pack(">I", zlib.crc32(kind + data) & 0xFFFFFFFF)
    )


def _generate_fallback_green_png(output: Path, width: int = 1000, height: int = 560) -> None:
    """Gera PNG neon sem Pillow para Termux enxuto."""
    bg = (2, 4, 3)
    grid = (3, 21, 12)
    green = (57, 255, 136)
    raw_rows = []
    for y in range(height):
        row = bytearray()
        for x in range(width):
            on_border = x in range(45, 50) or x in range(width - 50, width - 45) or y in range(45, 50) or y in range(height - 50, height - 45)
            on_grid = x % 40 == 0 or y % 40 == 0
            is_bar = 110 < y < 170 and 90 < x < 700 or 235 < y < 330 and 90 < x < 520
            color = green if on_border or is_bar else grid if on_grid else bg
            row.extend(color)
        raw_rows.append(b"\x00" + bytes(row))

    payload = (
        b"\x89PNG\r\n\x1a\n"
        + _chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0))
        + _chunk(b"IDAT", zlib.compress(b"".join(raw_rows), 9))
        + _chunk(b"IEND", b"")
    )
    output.write_bytes(payload)
