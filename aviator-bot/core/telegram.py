"""Camada Telegram: grupos dinâmicos, botões, comandos ON/Pare e quiz."""
from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Callable, Awaitable

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, InputFile, Update
from telegram.constants import ParseMode
from telegram.ext import Application, CallbackQueryHandler, ContextTypes, MessageHandler, filters

from core.signals import Signal
from core import ui

logger = logging.getLogger(__name__)


class TelegramService:
    def __init__(
        self,
        token: str,
        groups_path: str | Path,
        links_path: str | Path,
        bot_name: str,
    ) -> None:
        self.bot_name = bot_name
        self.groups_path = Path(groups_path)
        self.links_path = Path(links_path)
        self.application = Application.builder().token(token).build()
        self.is_running = True
        self.quiz_active = False
        self.quiz_votes: dict[int, str] = {}
        self._on_state_change: Callable[[bool], Awaitable[None]] | None = None
        self.application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self._handle_text))
        self.application.add_handler(CallbackQueryHandler(self._handle_callback))

    def set_state_callback(self, callback: Callable[[bool], Awaitable[None]]) -> None:
        self._on_state_change = callback

    async def start(self) -> None:
        await self.application.initialize()
        await self.application.start()
        await self.application.updater.start_polling(drop_pending_updates=True)
        logger.info("Telegram polling iniciado")

    async def stop(self) -> None:
        await self.application.updater.stop()
        await self.application.stop()
        await self.application.shutdown()

    def active_groups(self) -> list[int]:
        data = json.loads(self.groups_path.read_text(encoding="utf-8"))
        groups = data.get("groups", [])
        return [int(group["id"]) for group in groups if group.get("active")]

    def register_keyboard(self) -> InlineKeyboardMarkup:
        data = json.loads(self.links_path.read_text(encoding="utf-8"))
        return InlineKeyboardMarkup(
            [[InlineKeyboardButton(data["register_button_text"], url=data["register_url"])]]
        )

    async def broadcast_signal(self, signal: Signal) -> None:
        text = ui.signal_message(signal, self.bot_name)
        await self._broadcast_text(text, reply_markup=self.register_keyboard())

    async def broadcast_green(self, current: float, previous: float, signal: Signal, image_path: Path) -> None:
        caption = ui.green_message(current, previous, signal, self.bot_name)
        for chat_id in self.active_groups():
            try:
                with image_path.open("rb") as image_file:
                    await self.application.bot.send_photo(
                        chat_id=chat_id,
                        photo=InputFile(image_file, filename=image_path.name),
                        caption=caption,
                        reply_markup=self.register_keyboard(),
                    )
            except Exception as exc:  # noqa: BLE001 - broadcast must not crash loop
                logger.warning("Falha ao enviar GREEN para %s: %s", chat_id, exc)

    async def broadcast_quiz(self, duration_seconds: int, question: str | None = None) -> None:
        self.quiz_active = True
        self.quiz_votes.clear()
        keyboard = InlineKeyboardMarkup(
            [[InlineKeyboardButton("👍 SIM", callback_data="quiz_yes"), InlineKeyboardButton("👎 NÃO", callback_data="quiz_no")]]
        )
        await self._broadcast_text(ui.quiz_message(question or "Estão gostando dos sinais? 🎯"), reply_markup=keyboard)

    async def finish_quiz(self) -> None:
        yes = sum(1 for vote in self.quiz_votes.values() if vote == "yes")
        no = sum(1 for vote in self.quiz_votes.values() if vote == "no")
        self.quiz_active = False
        await self._broadcast_text(ui.quiz_result_message(yes, no), reply_markup=self.register_keyboard())

    async def _broadcast_text(self, text: str, reply_markup: InlineKeyboardMarkup | None = None) -> None:
        for chat_id in self.active_groups():
            try:
                await self.application.bot.send_message(
                    chat_id=chat_id,
                    text=text,
                    reply_markup=reply_markup,
                    parse_mode=ParseMode.HTML,
                )
            except Exception as exc:  # noqa: BLE001
                logger.warning("Falha ao enviar mensagem para %s: %s", chat_id, exc)

    async def _handle_text(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        del context
        if not update.effective_message or not update.effective_chat:
            return
        text = (update.effective_message.text or "").strip().lower()
        chat_id = update.effective_chat.id
        if chat_id not in self.active_groups():
            return
        if text == "on":
            self.is_running = True
            if self._on_state_change:
                await self._on_state_change(True)
            await update.effective_message.reply_text(ui.started_message())
        elif text == "pare":
            self.is_running = False
            if self._on_state_change:
                await self._on_state_change(False)
            await update.effective_message.reply_text(ui.stopped_message())

    async def _handle_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        del context
        query = update.callback_query
        if not query:
            return
        await query.answer("Voto registrado ✅")
        if not self.quiz_active or not query.from_user:
            return
        if query.data == "quiz_yes":
            self.quiz_votes[query.from_user.id] = "yes"
        elif query.data == "quiz_no":
            self.quiz_votes[query.from_user.id] = "no"
