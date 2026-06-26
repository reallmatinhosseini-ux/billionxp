from __future__ import annotations

from aiogram import F, Router
from aiogram.enums import ChatType
from aiogram.types import CallbackQuery

from app.database import Database, SignalRecord
from app.events import EventConfig, all_take_profits, get_event
from app.middlewares import AppContext
from utils.logger import get_logger

log = get_logger(__name__)

router = Router(name="followups")

_DM_CALLBACK = F.message.chat.type == ChatType.PRIVATE


def _apply_event_flags(event: EventConfig) -> dict[str, object]:
    """Translate an EventConfig into DB update kwargs."""
    kw: dict[str, object] = {}
    if event.is_take_profit and event.tp_index is not None:
        kw[f"tp{event.tp_index}_hit"] = True
    if event.moves_sl_to_be:
        kw["sl_moved_to_be"] = True
    if event.code == "sl":
        kw["sl_hit"] = True
    if event.code == "be":
        kw["be_hit"] = True
    if event.closes_signal:
        kw["status"] = "closed"
    return kw


async def _maybe_mark_completed(db: Database, sig: SignalRecord) -> None:
    """If every defined TP is hit, move the signal to completed."""
    refreshed = await db.fetch_signal_by_id(sig.id)
    if refreshed is None or refreshed.status != "active":
        return
    defined_tp_indexes = [
        tp.tp_index
        for tp in all_take_profits()
        if tp.tp_index is not None
        and getattr(refreshed, f"tp{tp.tp_index}") is not None
    ]
    if not defined_tp_indexes:
        return
    if all(getattr(refreshed, f"tp{i}_hit") for i in defined_tp_indexes):
        await db.update_hits_and_status(refreshed.id, status="completed")


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
        return "Cancelled."

    sig = await db.fetch_signal_by_id(alert.signal_id)
    if not sig:
        await db.set_alert_status(alert_id, "cancelled")
        return "Signal not found. Cancelled."

    event = get_event(alert.kind)
    if event is None:
        await db.set_alert_status(alert_id, "cancelled")
        return f"Unknown event kind '{alert.kind}'. Cancelled."

    text = event.render(sig.symbol)
    await bot.send_message(
        chat_id=sig.telegram_chat_id,
        text=text,
        reply_parameters={"message_id": sig.telegram_message_id},
    )

    flags = _apply_event_flags(event)
    if flags:
        await db.update_hits_and_status(sig.id, **flags)  # type: ignore[arg-type]
    await db.set_alert_status(alert_id, "sent")

    if event.is_take_profit:
        await _maybe_mark_completed(db, sig)

    return f"Sent to channel ({event.label})."


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
