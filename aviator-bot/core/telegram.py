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
from core.firebase import FirebasePanel
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
        admin_user_id: int | None = None,
    ) -> None:
        self.bot_name = bot_name
        self.groups_path = Path(groups_path)
        self.links_path = Path(links_path)
        self.monitor_all_chats = monitor_all_chats
        self.admin_user_id = admin_user_id
        self.application = Application.builder().token(token).build()
        self.firebase = FirebasePanel()
        self.is_running = True
        self.paused_groups: set[int] = set()
        self.group_signal_count: dict[int, int] = {}
        self.admin_authenticated = False
        self._admin_step: str | None = None
        self.online_group_ids: set[int] = set()
        self.last_send_ok: bool | None = None
        self.bot_connected = False
        self._on_state_change: Callable[[bool], Awaitable[None]] | None = None
        self.application.add_handler(MessageHandler(filters.TEXT, self._handle_text))

    def _load_links(self) -> dict:
        return json.loads(self.links_path.read_text(encoding="utf-8"))

    def _save_links(self, data: dict) -> None:
        self.links_path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    def _save_groups(self, groups: list[dict]) -> None:
        self.groups_path.write_text(json.dumps({"groups": groups}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

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
        await self.firebase.close()

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
        now = __import__("time").time()
        for g in self.configured_groups():
            try:
                gid = int(g.get("id", 0))
            except Exception:
                continue
            if gid != chat_id or not g.get("active"):
                continue
            expires_at = g.get("expires_at")
            if expires_at and now > float(expires_at):
                return False
            return True
        return False

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

    def register_keyboard(self, chat_id: int | None = None) -> InlineKeyboardMarkup:
        data = json.loads(self.links_path.read_text(encoding="utf-8"))
        if chat_id is not None and isinstance(data.get("group_links"), list):
            for item in data["group_links"]:
                if str(item.get("chat_id", "")).strip() == str(chat_id):
                    return InlineKeyboardMarkup(
                        [[InlineKeyboardButton(item.get("button_text", "📌 REGISTRAR AGORA"), url=item.get("url", data["register_url"]))]]
                    )
        return InlineKeyboardMarkup(
            [[InlineKeyboardButton(data["register_button_text"], url=data["register_url"])]]
        )

    def _register_url_for_chat(self, chat_id: int) -> str:
        data = json.loads(self.links_path.read_text(encoding="utf-8"))
        if isinstance(data.get("group_links"), list):
            for item in data["group_links"]:
                if str(item.get("chat_id", "")).strip() == str(chat_id) and item.get("url"):
                    return str(item["url"])
        return str(data.get("register_url", "https://example.com"))

    async def broadcast_signal(self, signal: Signal) -> bool:
        text = ui.signal_message(signal, self.bot_name)
        return await self._broadcast_text(text)

    async def broadcast_green(self, current: float, previous: float, signal: Signal, image_path: Path) -> bool:
        caption = ui.green_message(current, previous, signal, self.bot_name)
        success = 0
        targets = self.target_groups()
        for chat_id in targets:
            if chat_id in self.paused_groups:
                continue
            try:
                with image_path.open("rb") as image_file:
                    sent = False
                    for _ in range(2):
                        try:
                            await self.application.bot.send_photo(
                                chat_id=chat_id,
                                photo=InputFile(image_file, filename=image_path.name),
                                caption=caption,
                                reply_markup=self.register_keyboard(chat_id),
                            )
                            sent = True
                            break
                        except Exception:
                            continue
                    if not sent:
                        raise RuntimeError("timeout/retry failed")
                success += 1
            except Exception as exc:  # noqa: BLE001 - broadcast must not crash loop
                logger.warning("🛑 Falha ao enviar GREEN para %s: %s", chat_id, exc)
        self.last_send_ok = bool(targets) and success == len(targets)
        return self.last_send_ok

    async def _broadcast_text(self, text: str, reply_markup: InlineKeyboardMarkup | None = None) -> bool:
        success = 0
        targets = self.target_groups()
        for chat_id in targets:
            if chat_id in self.paused_groups:
                continue
            try:
                payload_text = text.replace("{REGISTER_URL}", self._register_url_for_chat(chat_id))
                await self.application.bot.send_message(
                    chat_id=chat_id,
                    text=payload_text,
                    reply_markup=reply_markup or self.register_keyboard(chat_id),
                    parse_mode=ParseMode.HTML,
                )
                success += 1
                self.group_signal_count[chat_id] = self.group_signal_count.get(chat_id, 0) + 1
                try:
                    await self.firebase.set_group_signal_count(chat_id, self.group_signal_count[chat_id])
                except Exception:
                    pass
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
        if text in {"/admin", "admin"} and (not update.effective_user or update.effective_user.id != self.admin_user_id):
            await update.effective_message.reply_text("COMANDO ADMIN NAO PERMITIDO AO USUÁRIO!! 🛑")
            return

        if self.admin_user_id and update.effective_user and update.effective_user.id == self.admin_user_id:
            if text in {"/admin", "admin"}:
                self._admin_step = "username"
                self.admin_authenticated = False
                await update.effective_message.reply_text("Painel Admin\nDigite usuário:")
                return
            if self._admin_step == "username":
                if raw_text.strip() == "klein":
                    self._admin_step = "password"
                    await update.effective_message.reply_text("Usuário OK. Digite senha:")
                else:
                    await update.effective_message.reply_text("Usuário inválido.")
                return
            if self._admin_step == "password":
                if raw_text.strip() == "871009140":
                    self.admin_authenticated = True
                    self._admin_step = None
                    await update.effective_message.reply_text(
                        "✅ Acesso admin liberado.\n"
                        "Comandos:\n"
                        "/stats\n/pausegroup <id>\n/resumegroup <id>\n/alerta <id> <msg>\n"
                        "/addgroup <chat_id> <nome> <active:true|false> [duracao_min]\n"
                        "/setlink <chat_id> <texto_botao> <url>"
                    )
                else:
                    await update.effective_message.reply_text("Senha inválida.")
                return
            if self.admin_authenticated and text.startswith("/stats"):
                lines = [f"{gid}: {cnt} sinais" for gid, cnt in sorted(self.group_signal_count.items())] or ["Sem sinais enviados ainda."]
                await update.effective_message.reply_text("📊 Painel de grupos\n" + "\n".join(lines))
                return
            if self.admin_authenticated and text.startswith("/addgroup"):
                parts = raw_text.split(maxsplit=4)
                if len(parts) >= 4:
                    gid = parts[1]
                    name = parts[2]
                    active = parts[3].lower() in {"1", "true", "sim", "yes", "on"}
                    duration_minutes = int(parts[4]) if len(parts) >= 5 and parts[4].isdigit() else 0
                    groups = self.configured_groups()
                    expires_at = (__import__("time").time() + duration_minutes * 60) if duration_minutes > 0 else None
                    groups.append({"name": name, "id": gid, "active": active, "expires_at": expires_at})
                    self._save_groups(groups)
                    await update.effective_message.reply_text(f"✅ Grupo adicionado: {name} ({gid})")
                else:
                    await update.effective_message.reply_text("Uso: /addgroup <chat_id> <nome> <active:true|false> [duracao_min]")
                return
            if self.admin_authenticated and text.startswith("/setlink"):
                parts = raw_text.split(maxsplit=3)
                if len(parts) >= 4:
                    gid = parts[1]
                    button_text = parts[2]
                    url = parts[3]
                    links = self._load_links()
                    links.setdefault("group_links", [])
                    links["group_links"] = [x for x in links["group_links"] if str(x.get("chat_id", "")).strip() != gid]
                    links["group_links"].append({"chat_id": gid, "button_text": button_text, "url": url})
                    self._save_links(links)
                    await update.effective_message.reply_text(f"✅ Link atualizado para grupo {gid}.")
                else:
                    await update.effective_message.reply_text("Uso: /setlink <chat_id> <texto_botao> <url>")
                return
            if self.admin_authenticated and text.startswith("/pausegroup"):
                parts = raw_text.split()
                if len(parts) >= 2:
                    self.paused_groups.add(int(parts[1]))
                    try:
                        await self.firebase.set_group_paused(int(parts[1]), True)
                    except Exception:
                        pass
                    await update.effective_message.reply_text(f"⏸ Grupo pausado: {parts[1]}")
                return
            if self.admin_authenticated and text.startswith("/resumegroup"):
                parts = raw_text.split()
                if len(parts) >= 2:
                    self.paused_groups.discard(int(parts[1]))
                    try:
                        await self.firebase.set_group_paused(int(parts[1]), False)
                    except Exception:
                        pass
                    await update.effective_message.reply_text(f"▶️ Grupo retomado: {parts[1]}")
                return
            if self.admin_authenticated and text.startswith("/alerta"):
                parts = raw_text.split(maxsplit=2)
                if len(parts) >= 3:
                    gid = int(parts[1])
                    await self.application.bot.send_message(chat_id=gid, text=f"🚨 ALERTA ADMIN:\n{parts[2]}")
                    await update.effective_message.reply_text("Alerta enviado.")
                return
            if text in {"/ultima", "ultima", "/ultimavela"}:
                await update.effective_message.reply_text("Use /logs para detalhes em runtime no momento.")
                return

        if self.admin_user_id and update.effective_user and update.effective_user.id == self.admin_user_id:
            if text in {"/ultima", "ultima", "/ultimavela"}:
                await update.effective_message.reply_text("Use /logs para detalhes em runtime no momento.")
                return

        if not allowed:
            if self.admin_user_id and update.effective_user and update.effective_user.id == self.admin_user_id:
                if text in {"/logs", "logs"}:
                    log_path = self.groups_path.parent.parent / "logs" / "aviator-bot.log"
                    if log_path.exists():
                        await update.effective_message.reply_text(log_path.read_text(encoding="utf-8")[-3500:])
                    else:
                        await update.effective_message.reply_text("Sem logs ainda.")
                    return
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
