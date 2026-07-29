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


_HELP = (
    "✅ BillionXP Bot — ready.\n"
    "\n"
    "📥 Paste any raw signal. The bot formats it and asks where to publish\n"
    "(VIP / Public / Both). Once posted, the tracker watches price and\n"
    "posts TP / SL / BE follow-ups automatically.\n"
    "\n"
    "Commands:\n"
    "• /active — active tracked signals\n"
    "• /close <id> — stop tracking a signal\n"
    "• /settings — show configuration\n"
    "• /help — show this message\n"
    "• /ping — liveness check"
)


@router.message(CommandStart(), _DM)
async def cmd_start(message: Message) -> None:
    log.info("START chat=%s user=%s", message.chat.id, message.from_user.id)
    await message_answer_logged(message, _HELP)


@router.message(Command("help"), _DM)
async def cmd_help(message: Message) -> None:
    await message_answer_logged(message, _HELP)


@router.message(Command("ping"), _DM)
async def cmd_ping(message: Message) -> None:
    await message_answer_logged(message, "🟢 pong")
