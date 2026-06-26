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
    "🏆 BillionXP — Operator Console LIVE 🟢\n"
    "━━━━━━━━━━━━━━━━━━━━\n"
    "\n"
    "You’re in the engine room. Speed wins. Discipline pays. 💎\n"
    "\n"
    "⚡ What you can do:\n"
    "• Paste a raw signal → premium formatting + 1-tap publish 🚀\n"
    "• /tp — TP Sender: fire TP1–TP7 / SL HIT to any channel 🎯\n"
    "• /active — live tracked trades 📡\n"
    "• /history — recent operations 📜\n"
    "• /menu — open the command center 🎛\n"
    "• /settings — bot configuration ⚙️\n"
    "\n"
    "Let’s go to work. 🦾"
)


_MENU_HEADER = (
    "🎛 BillionXP — Command Center\n"
    "━━━━━━━━━━━━━━━━━━━━\n"
    "Pick your move. ⚡"
)


@router.message(CommandStart(), _DM)
async def cmd_start(message: Message) -> None:
    log.info("START handler called chat=%s user=%s", message.chat.id, message.from_user.id)
    await message_answer_logged(message, _WELCOME, reply_markup=main_menu_keyboard())


@router.message(Command("ping"), _DM)
async def cmd_ping(message: Message) -> None:
    await message_answer_logged(message, "🟢 pong — engine online.")


@router.message(Command("menu"), _DM)
async def cmd_menu(message: Message) -> None:
    await message_answer_logged(message, _MENU_HEADER, reply_markup=main_menu_keyboard())
