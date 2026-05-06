from __future__ import annotations

from aiogram import F, Router
from aiogram.enums import ChatType
from aiogram.filters import Command, CommandStart
from aiogram.types import Message

from app.replies import message_answer_logged
from utils.logger import get_logger

log = get_logger(__name__)

router = Router(name="start")

_DM = F.chat.type == ChatType.PRIVATE


@router.message(CommandStart(), _DM)
async def cmd_start(message: Message) -> None:
    log.info("START handler called chat=%s user=%s", message.chat.id, message.from_user.id)
    text = "✅ Bot is alive. Send me a raw signal."
    await message_answer_logged(message, text)


@router.message(Command("ping"), _DM)
async def cmd_ping(message: Message) -> None:
    log.info("PING handler called chat=%s user=%s", message.chat.id, message.from_user.id)
    await message_answer_logged(message, "pong")
