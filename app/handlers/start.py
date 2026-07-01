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


_HELP = (
    "🆘 BillionXP — Operator Guide\n"
    "━━━━━━━━━━━━━━━━━━━━\n"
    "\n"
    "📥 Paste any raw signal → the bot formats it and asks where to publish.\n"
    "\n"
    "Core commands\n"
    "• /menu — command center with buttons\n"
    "• /tp — TP Sender: fire TP1–TP7, FULL TP, or SL HIT manually\n"
    "• /active — live tracked trades with hit-status badges\n"
    "• /history — last 15 signals\n"
    "• /close <id> — stop tracking a signal (no channel post)\n"
    "• /settings — show current configuration\n"
    "• /ping — liveness check\n"
    "\n"
    "How tracking works\n"
    "• Every tick, prices are checked against every active signal.\n"
    "• TP / SL / BE hits are queued for admin approval (or auto-fired if\n"
    "  AUTO_APPROVE_FOLLOWUPS=true).\n"
    "• After the final TP posts, the FULL TP HIT summary fires automatically\n"
    "  and the signal is marked completed."
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


@router.message(Command("help"), _DM)
async def cmd_help(message: Message) -> None:
    await message_answer_logged(message, _HELP)
