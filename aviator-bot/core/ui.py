"""Design premium das mensagens e imagens do bot."""
from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from core.signals import Signal

SEPARATOR = "━━━━━━━━━━━━━━━━━━━━━━"


def signal_message(signal: Signal, bot_name: str) -> str:
    return (
        f"{SEPARATOR}\n"
        f"🤖 {bot_name}\n"
        f"{SEPARATOR}\n\n"
        "🎯 NOVA RODADA DETECTADA\n\n"
        f"📊 APÓS: {signal.after:.2f}x\n"
        f"🛡 PROTEÇÃO: {signal.protection:.2f}x\n"
        f"🔥 SAÍDA: {signal.exit:.2f}x\n"
        f"👥 PLAYERS: {signal.players}\n\n"
        f"🧠 AI SCORE: {signal.ai_score} ({signal.ai_percent}%)\n"
        f"📈 VOL: {signal.volatility:.3f} | TEND: {signal.trend:.3f}\n\n"
        f"{SEPARATOR}\n"
        "⚡ STATUS: MONITORANDO\n"
        f"{SEPARATOR}"
    )


def green_message(current: float, previous: float, signal: Signal, bot_name: str) -> str:
    return (
        "🟢 GREEN CONFIRMADO 🟢\n\n"
        f"🤖 {bot_name}\n"
        f"🚀 Multiplicador: {current:.2f}x\n"
        f"📊 Vela anterior: {previous:.2f}x\n"
        f"🔥 Alvo: {signal.exit:.2f}x\n"
        f"🧠 Estratégia: {signal.ai_score} ({signal.ai_percent}%)"
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
