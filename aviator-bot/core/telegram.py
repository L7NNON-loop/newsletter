"""Camada Telegram: grupos dinâmicos, botões e comandos ON/Pare."""
from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Awaitable, Callable

from gtts import gTTS
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, InputFile, Update
from telegram.constants import ParseMode
from telegram.error import Conflict
from telegram.ext import Application, ContextTypes, MessageHandler, filters

from core import ui
from core.signals import Signal

logger = logging.getLogger(__name__)


class TelegramService:
    def __init__(
        self,
        token: str,
        groups_path: str | Path,
        links_path: str | Path,
        bot_name: str,
        monitor_all_chats: bool = True,
    ) -> None:
        self.bot_name = bot_name
        self.groups_path = Path(groups_path)
        self.links_path = Path(links_path)
        self.monitor_all_chats = monitor_all_chats
        self.application = Application.builder().token(token).build()
        self.is_running = True
        self.online_group_ids: set[int] = set()
        self.last_send_ok: bool | None = None
        self.bot_connected = False
        self._on_state_change: Callable[[bool], Awaitable[None]] | None = None
        self.application.add_handler(MessageHandler(filters.TEXT, self._handle_text))

    def set_state_callback(self, callback: Callable[[bool], Awaitable[None]]) -> None:
        self._on_state_change = callback

    async def start(self) -> None:
        await self.application.initialize()
        bot_user = await self.application.bot.get_me()
        self.bot_connected = True
        logger.info("🤖 Bot conectado: @%s | id=%s", bot_user.username, bot_user.id)
        await self.application.start()
        try:
            await self.application.updater.start_polling(drop_pending_updates=True)
        except Conflict as exc:
            raise RuntimeError(
                "Já existe outra instância deste bot rodando. Use `codex stop` ou `bash scripts/stop_termux.sh` antes de iniciar."
            ) from exc
        logger.info("📡 Monitoramento de mensagens iniciado")

    async def stop(self) -> None:
        await self.application.updater.stop()
        await self.application.stop()
        await self.application.shutdown()

    def configured_groups(self) -> list[dict]:
        data = json.loads(self.groups_path.read_text(encoding="utf-8"))
        return data.get("groups", [])

    def active_groups(self) -> list[int]:
        groups: list[int] = []
        for group in self.configured_groups():
            if not group.get("active"):
                continue
            try:
                groups.append(int(group["id"]))
            except (KeyError, TypeError, ValueError):
                logger.warning("🛑 ID de grupo inválido em config/groups.json: %s", group)
        return groups

    def target_groups(self) -> list[int]:
        if self.online_group_ids:
            return sorted(self.online_group_ids)
        return self.active_groups()

    def is_allowed_chat(self, chat_id: int) -> bool:
        return chat_id in self.active_groups()

    async def refresh_online_groups(self) -> int:
        self.online_group_ids.clear()
        for group in self.configured_groups():
            if not group.get("active"):
                continue
            try:
                chat_id = int(group["id"])
            except (KeyError, TypeError, ValueError):
                logger.warning("🛑 ID de grupo inválido em config/groups.json: %s", group)
                continue
            try:
                chat = await self.application.bot.get_chat(chat_id)
                self.online_group_ids.add(chat_id)
                logger.info("✅ Grupo online: %s | id=%s", chat.title or group.get("name"), chat_id)
            except Exception as exc:  # noqa: BLE001
                logger.warning(
                    "🛑 Grupo offline/não encontrado: %s | id=%s | erro=%s | envie /id no grupo correto e atualize config/groups.json",
                    group.get("name"),
                    chat_id,
                    exc,
                )
        return len(self.online_group_ids)

    def register_keyboard(self) -> InlineKeyboardMarkup:
        data = json.loads(self.links_path.read_text(encoding="utf-8"))
        return InlineKeyboardMarkup(
            [[InlineKeyboardButton(data["register_button_text"], url=data["register_url"])]]
        )

    async def broadcast_signal(self, signal: Signal) -> bool:
        text = ui.signal_message(signal, self.bot_name)
        return await self._broadcast_text(text, reply_markup=self.register_keyboard())

    async def broadcast_green(self, current: float, previous: float, signal: Signal, image_path: Path) -> bool:
        caption = ui.green_message(current, previous, signal, self.bot_name)
        success = 0
        targets = self.target_groups()
        for chat_id in targets:
            try:
                with image_path.open("rb") as image_file:
                    await self.application.bot.send_photo(
                        chat_id=chat_id,
                        photo=InputFile(image_file, filename=image_path.name),
                        caption=caption,
                        reply_markup=self.register_keyboard(),
                    )
                success += 1
            except Exception as exc:  # noqa: BLE001 - broadcast must not crash loop
                logger.warning("🛑 Falha ao enviar GREEN para %s: %s", chat_id, exc)
        self.last_send_ok = bool(targets) and success == len(targets)
        return self.last_send_ok

    async def _broadcast_text(self, text: str, reply_markup: InlineKeyboardMarkup | None = None) -> bool:
        success = 0
        targets = self.target_groups()
        for chat_id in targets:
            try:
                await self.application.bot.send_message(
                    chat_id=chat_id,
                    text=text,
                    reply_markup=reply_markup,
                    parse_mode=ParseMode.HTML,
                )
                success += 1
            except Exception as exc:  # noqa: BLE001
                logger.warning("🛑 Falha ao enviar mensagem para %s: %s", chat_id, exc)
        self.last_send_ok = bool(targets) and success == len(targets)
        return self.last_send_ok

    async def broadcast_startup_audio(self, text: str) -> bool:
        voice_path = self.groups_path.parent / "assets" / "startup_message.mp3"
        voice_path.parent.mkdir(parents=True, exist_ok=True)
        try:
            gTTS(text=text, lang="pt", tld="com.br").save(str(voice_path))
        except Exception as exc:  # noqa: BLE001
            logger.warning("🛑 Falha ao gerar áudio de boas-vindas: %s", exc)
            return False

        success = 0
        targets = self.target_groups()
        for chat_id in targets:
            try:
                with voice_path.open("rb") as voice_file:
                    await self.application.bot.send_voice(
                        chat_id=chat_id,
                        voice=InputFile(voice_file, filename=voice_path.name),
                        caption="🎧 Mensagem oficial da sala",
                        reply_markup=self.register_keyboard(),
                    )
                success += 1
            except Exception as exc:  # noqa: BLE001
                logger.warning("🛑 Falha ao enviar áudio para %s: %s", chat_id, exc)
        self.last_send_ok = bool(targets) and success == len(targets)
        return self.last_send_ok

    async def _handle_text(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        del context
        if not update.effective_message or not update.effective_chat:
            return
        raw_text = (update.effective_message.text or "").strip()
        text = raw_text.lower()
        chat = update.effective_chat
        chat_id = chat.id
        allowed = self.is_allowed_chat(chat_id)

        if self.monitor_all_chats:
            logger.info(
                "📥 Mensagem recebida | chat=%s | id=%s | permitido=%s | texto=%s",
                chat.title or chat.full_name or chat.type,
                chat_id,
                "SIM" if allowed else "NÃO",
                raw_text,
            )

        if text in {"/id", "id", "chatid", "/chatid"}:
            await update.effective_message.reply_text(
                f"🆔 ID deste chat/grupo:\n`{chat_id}`\n\nCopie este valor para config/groups.json.",
                parse_mode=ParseMode.MARKDOWN,
            )
            return

        if not allowed:
            if text in {"on", "ligar", "continuar", "pare", "parar", "off"}:
                await update.effective_message.reply_text(
                    f"⚠️ Este chat ainda não está permitido.\nID detectado: `{chat_id}`\nAdicione em config/groups.json e rode git pull/start.",
                    parse_mode=ParseMode.MARKDOWN,
                )
            return

        if text in {"on", "ligar", "continuar"}:
            if self.is_running:
                return
            self.is_running = True
            if self._on_state_change:
                await self._on_state_change(True)
            await update.effective_message.reply_text(ui.started_message())
        elif text in {"pare", "parar", "off"}:
            if not self.is_running:
                return
            self.is_running = False
            if self._on_state_change:
                await self._on_state_change(False)
            await update.effective_message.reply_text(ui.stopped_message())
