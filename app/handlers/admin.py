from __future__ import annotations

from aiogram import F, Router
from aiogram.enums import ChatType
from aiogram.filters import Command
from aiogram.types import CallbackQuery, Message

from app.database import SignalRecord
from app.events import all_take_profits
from app.middlewares import AppContext
from app.replies import message_answer_logged

router = Router(name="admin")

_DM = F.chat.type == ChatType.PRIVATE
_DM_CALLBACK = F.message.chat.type == ChatType.PRIVATE


@router.message(Command("settings"), _DM)
async def cmd_settings(message: Message, app_ctx: AppContext) -> None:
    s = app_ctx.settings
    auto = "ON — direct fire" if s.auto_approve_followups else "OFF — admin approval"
    lines = (
        "⚙️ COMMAND CENTER — CONFIGURATION",
        "━━━━━━━━━━━━━━━━━━━━",
        f"⏱  Tracker interval: {s.check_interval_seconds:g}s",
        f"🏆 VIP channel:      {s.vip_channel_id or '⚠️ unset'}",
        f"🌐 Public channel:   {s.free_channel_id or '⚠️ unset'}",
        f"📩 Free CTA handle:  @{s.free_cta_username}" if s.free_cta_username else "📩 Free CTA handle:  ⚠️ unset",
        f"📈 Price feed:       {s.price_provider}",
        f"⚡ Auto-approve:     {auto}",
        f"🛡 Operators:        {len(s.admin_ids)}",
    )
    await message_answer_logged(message, "\n".join(lines))


def _progress_badges(r: SignalRecord) -> str:
    badges: list[str] = []
    for tp in all_take_profits():
        if tp.tp_index is None:
            continue
        if getattr(r, f"tp{tp.tp_index}") is None:
            continue
        hit = getattr(r, f"tp{tp.tp_index}_hit")
        badges.append(f"TP{tp.tp_index}{'✅' if hit else '·'}")
    if r.sl_moved_to_be and not r.be_hit and not r.sl_hit:
        badges.append("SL→BE")
    if r.be_hit:
        badges.append("BE✅")
    if r.sl_hit:
        badges.append("SL❌")
    return " ".join(badges) if badges else "—"


@router.message(Command("active"), _DM)
async def cmd_active(message: Message, app_ctx: AppContext) -> None:
    rows = await app_ctx.db.fetch_active_signals()
    if not rows:
        await message_answer_logged(
            message,
            "📡 No live trades right now.\nNext setup is loading… stay sharp. 🎯",
        )
        return

    lines: list[str] = [
        "📡 LIVE TRADES — TRACKING",
        "━━━━━━━━━━━━━━━━━━━━",
    ]
    for r in rows:
        lines.append(
            f"#{r.id}  {r.symbol} {r.direction}  •  {r.channel_type.upper()}  •  msg {r.telegram_message_id}\n"
            f"     {_progress_badges(r)}"
        )
    await message_answer_logged(message, "\n".join(lines))


@router.message(Command("history"), _DM)
async def cmd_history(message: Message, app_ctx: AppContext) -> None:
    rows = await app_ctx.db.fetch_recent_signals(limit=15)
    if not rows:
        await message_answer_logged(message, "📜 No operations on record yet.")
        return
    lines: list[str] = [
        "📜 RECENT OPERATIONS — LAST 15",
        "━━━━━━━━━━━━━━━━━━━━",
    ]
    for r in rows:
        lines.append(
            f"#{r.id}  [{r.status.upper()}]  {r.symbol} {r.direction}\n"
            f"     {_progress_badges(r)}"
        )
    await message_answer_logged(message, "\n".join(lines))


@router.message(Command("close"), _DM)
async def cmd_close(message: Message, app_ctx: AppContext) -> None:
    parts = (message.text or "").split(maxsplit=1)
    if len(parts) < 2 or not parts[1].strip().isdigit():
        await message_answer_logged(message, "Usage: /close <signal_id>")
        return
    sid = int(parts[1].strip())
    rec = await app_ctx.db.fetch_signal_by_id(sid)
    if not rec:
        await message_answer_logged(message, "❓ Unknown signal id.")
        return
    if rec.status != "active":
        await message_answer_logged(
            message, f"⚠️ Signal #{sid} is already {rec.status.upper()}."
        )
        return

    await app_ctx.db.update_hits_and_status(sid, status="closed")
    await message_answer_logged(
        message,
        f"🛑 Signal #{sid} closed. Tracking stopped. ✅",
    )


# ─────────────────────────────────────────────────────────────────────────────
# Inline menu shortcuts
# ─────────────────────────────────────────────────────────────────────────────


async def _ack(callback: CallbackQuery) -> None:
    try:
        await callback.answer()
    except Exception:
        pass


@router.callback_query(F.data == "menu:active", _DM_CALLBACK)
async def menu_active(callback: CallbackQuery, app_ctx: AppContext) -> None:
    await _ack(callback)
    if isinstance(callback.message, Message):
        await cmd_active(callback.message, app_ctx)


@router.callback_query(F.data == "menu:history", _DM_CALLBACK)
async def menu_history(callback: CallbackQuery, app_ctx: AppContext) -> None:
    await _ack(callback)
    if isinstance(callback.message, Message):
        await cmd_history(callback.message, app_ctx)


@router.callback_query(F.data == "menu:settings", _DM_CALLBACK)
async def menu_settings(callback: CallbackQuery, app_ctx: AppContext) -> None:
    await _ack(callback)
    if isinstance(callback.message, Message):
        await cmd_settings(callback.message, app_ctx)
