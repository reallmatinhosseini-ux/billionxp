from __future__ import annotations

from aiogram import F, Router
from aiogram.enums import ChatType
from aiogram.types import CallbackQuery

from app.database import Database
from app.events import get_event
from app.middlewares import AppContext
from services.event_publisher import publish_event_to_channel
from utils.logger import get_logger

log = get_logger(__name__)

router = Router(name="followups")

_DM_CALLBACK = F.message.chat.type == ChatType.PRIVATE


async def _post_to_channel(
    db: Database, bot, alert_id: int, action: str
) -> str:
    alert = await db.fetch_alert_by_id(alert_id)
    if not alert:
        return "This alert no longer exists."
    if alert.status != "pending":
        return f"This alert is already {alert.status}."

    if action == "cancel":
        await db.set_alert_status(alert_id, "cancelled")
        return "🛑 Alert suppressed. Nothing sent to the channel."

    sig = await db.fetch_signal_by_id(alert.signal_id)
    if not sig:
        await db.set_alert_status(alert_id, "cancelled")
        return "❓ Signal not found. Alert cancelled."

    event = get_event(alert.kind)
    if event is None:
        await db.set_alert_status(alert_id, "cancelled")
        return f"❓ Unknown event '{alert.kind}'. Alert cancelled."

    await publish_event_to_channel(bot, db, sig, event)
    await db.set_alert_status(alert_id, "sent")
    return f"🚀 BROADCAST LIVE — {event.label} pushed to channel. 💎"


@router.callback_query(F.data.startswith("alert:"), _DM_CALLBACK)
async def on_followup_approval(
    callback: CallbackQuery,
    app_ctx: AppContext,
) -> None:
    # callback data format: alert:<send|cancel>:<id>
    data = callback.data or ""
    parts = data.split(":")
    if len(parts) != 3:
        await callback.answer("Bad payload.", show_alert=True)
        return

    action = parts[1]
    try:
        alert_id = int(parts[2])
    except ValueError:
        await callback.answer("Bad alert id.", show_alert=True)
        return

    if action not in {"send", "cancel"}:
        await callback.answer("Bad action.", show_alert=True)
        return

    try:
        msg = await _post_to_channel(app_ctx.db, callback.bot, alert_id, action)
        log.info(
            "followup %s alert=%s by admin=%s",
            action,
            alert_id,
            callback.from_user.id if callback.from_user else None,
        )
        await callback.answer("OK")
        if callback.message:
            try:
                await callback.message.edit_reply_markup(reply_markup=None)
            except Exception:
                pass
            await callback.message.answer(msg)
    except Exception:
        log.exception("followup approval failed alert=%s", alert_id)
        await callback.answer("Failed.", show_alert=True)
