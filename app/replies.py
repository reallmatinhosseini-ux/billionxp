from __future__ import annotations

from typing import Any

from aiogram.types import Message

from utils.logger import get_logger

log = get_logger(__name__)


async def message_answer_logged(
    message: Message, text: str, **kwargs: Any
) -> Message | None:
    """Thin wrapper — always tries message.answer(); logs Telegram failures."""
    try:
        sent = await message.answer(text, **kwargs)
        log.debug(
            "message.answer OK chat=%s mid=%s",
            message.chat.id,
            getattr(sent, "message_id", None),
        )
        return sent
    except Exception:
        log.exception(
            "message.answer FAILED chat=%s user=%s preview=%r",
            getattr(message.chat, "id", None),
            getattr(message.from_user, "id", None),
            text[:200],
        )
        return None
