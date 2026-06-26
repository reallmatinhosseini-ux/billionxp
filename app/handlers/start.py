from __future__ import annotations

from aiogram import F, Router
from aiogram.enums import ChatType
from aiogram.filters import Command, CommandStart
from aiogram.types import CallbackQuery, Message

from app.keyboards import main_menu_keyboard
from app.replies import message_answer_logged
from utils.logger import get_logger

log = get_logger(__name__)

router = Router(name="start")

_DM = F.chat.type == ChatType.PRIVATE
_DM_CALLBACK = F.message.chat.type == ChatType.PRIVATE


_WELCOME = (
    "✅ BillionXP bot is live.\n"
    "\n"
    "What you can do:\n"
    "• Paste a raw signal to format & publish\n"
    "• /tp — TP Sender (manual TP1–TP7 / SL post)\n"
    "• /active — list active tracked signals\n"
    "• /history — recent signals\n"
    "• /menu — open the inline menu\n"
    "• /settings — show non-secret config\n"
)


@router.message(CommandStart(), _DM)
async def cmd_start(message: Message) -> None:
    log.info("START handler called chat=%s user=%s", message.chat.id, message.from_user.id)
    await message_answer_logged(message, _WELCOME, reply_markup=main_menu_keyboard())


@router.message(Command("ping"), _DM)
async def cmd_ping(message: Message) -> None:
    await message_answer_logged(message, "pong")


@router.message(Command("menu"), _DM)
async def cmd_menu(message: Message) -> None:
    await message_answer_logged(message, "Main menu:", reply_markup=main_menu_keyboard())
