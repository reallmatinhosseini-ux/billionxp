from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Awaitable, Callable

from aiogram import BaseMiddleware
from aiogram.types import CallbackQuery, Message, TelegramObject

from app.config import Settings
from app.database import Database
from utils.logger import get_logger
from utils.security import is_admin

log = get_logger(__name__)

_DENIED = (
    "🔒 Access denied.\n"
    "This bot is restricted to authorized operators only."
)


@dataclass
class AppContext:
    settings: Settings
    db: Database


def _telegram_command_stub(text: str) -> str | None:
    if not text.strip():
        return None
    return text.split(maxsplit=1)[0].split("@", 1)[0].strip().lower()


def _is_public_liveness_command(message: Message) -> bool:
    """These must always reach handlers (DM only): /start, /ping."""
    if not message.chat or message.chat.type != "private":
        return False
    stub = _telegram_command_stub(message.text or "")
    return stub in {"/start", "/ping"}


class InjectContextMiddleware(BaseMiddleware):
    def __init__(self, ctx: AppContext) -> None:
        self.ctx = ctx

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        data["app_ctx"] = self.ctx
        return await handler(event, data)


class AdminOnlyMiddleware(BaseMiddleware):
    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        # /start & /ping are never silently blocked by admin gate
        if isinstance(event, Message) and _is_public_liveness_command(event):
            return await handler(event, data)

        uid: int | None = None
        if isinstance(event, Message) and event.from_user:
            uid = event.from_user.id
        elif isinstance(event, CallbackQuery) and event.from_user:
            uid = event.from_user.id

        if not self._settings.admin_ids:
            hint = (
                "⚠️ No operators configured.\n"
                "Set ADMIN_IDS in `.env` (comma-separated Telegram user IDs), "
                "restart the bot, then try again."
            )
            if isinstance(event, Message):
                try:
                    await event.answer(hint)
                except Exception:
                    log.exception(
                        "Failed to notify empty ADMIN_IDS (message) chat=%s",
                        event.chat.id,
                    )
            else:
                cq = event
                try:
                    await cq.answer(hint, show_alert=True)
                except Exception:
                    log.exception("Failed to notify empty ADMIN_IDS (callback)")
            log.warning("ADMIN_IDS empty — blocked uid=%s", uid)
            return None

        if not is_admin(uid, self._settings):
            if isinstance(event, Message):
                try:
                    await event.answer(_DENIED)
                    log.warning("DENIED uid=%s (message)", uid)
                except Exception:
                    log.exception("DENIED notify failed uid=%s", uid)
            else:
                try:
                    await event.answer(_DENIED, show_alert=True)
                    log.warning("DENIED uid=%s (callback)", uid)
                except Exception:
                    log.exception("DENIED callback notify failed uid=%s", uid)
            return None

        return await handler(event, data)
