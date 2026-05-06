from __future__ import annotations

from aiogram import F, Router
from aiogram.enums import ChatType
from aiogram.filters import Command
from aiogram.types import Message

from app.middlewares import AppContext
from app.replies import message_answer_logged

router = Router(name="admin")

_DM = F.chat.type == ChatType.PRIVATE


@router.message(Command("settings"), _DM)
async def cmd_settings(message: Message, app_ctx: AppContext) -> None:
    s = app_ctx.settings
    lines = (
        "Bot configuration",
        f"CHECK_INTERVAL_SECONDS: {s.check_interval_seconds:g}",
        f"VIP_CHANNEL_ID: {s.vip_channel_id or '(unset)'}",
        f"FREE_CHANNEL_ID: {s.free_channel_id or '(unset)'}",
        f"FREE_CTA_USERNAME: {s.free_cta_username or '(unset)'}",
        f"PRICE_PROVIDER: {s.price_provider}",
        f"Admins: {len(s.admin_ids)}",
    )
    await message_answer_logged(message, "\n".join(lines))


@router.message(Command("active"), _DM)
async def cmd_active(message: Message, app_ctx: AppContext) -> None:
    rows = await app_ctx.db.fetch_active_signals()
    if not rows:
        await message_answer_logged(message, "No active signals.")
        return

    lines: list[str] = ["Active signals:\n"]
    for r in rows:
        tps = [
            f"TP{i}"
            for i in range(1, 6)
            if getattr(r, f"tp{i}") is not None
        ]
        lines.append(
            f"#{r.id} {r.symbol} {r.direction} | channel={r.channel_type} | "
            f"msg={r.telegram_message_id} | {', '.join(tps)}"
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
        await message_answer_logged(message, "Unknown id.")
        return
    if rec.status != "active":
        await message_answer_logged(message, f"Signal #{sid} is already {rec.status}.")
        return

    await app_ctx.db.update_hits_and_status(sid, status="closed")
    await message_answer_logged(message, f"Signal #{sid} marked closed. Tracking stopped.")
