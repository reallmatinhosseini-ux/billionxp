from __future__ import annotations

from aiogram import F, Router
from aiogram.enums import ChatType
from aiogram.types import CallbackQuery

from app.database import Database
from app.formatter import format_sl_followup, format_tp_followup
from app.middlewares import AppContext
from utils.logger import get_logger

log = get_logger(__name__)

router = Router(name="followups")

_DM_CALLBACK = F.message.chat.type == ChatType.PRIVATE


async def _post_to_channel(db: Database, bot, alert_id: int, action: str, app_ctx: AppContext) -> str:
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

    kind = alert.kind.lower().strip()
    if kind == "sl":
        text = format_sl_followup(sig.symbol)
        await bot.send_message(
            chat_id=sig.telegram_chat_id,
            text=text,
            reply_parameters={"message_id": sig.telegram_message_id},
        )
        await db.update_hits_and_status(sig.id, sl_hit=True, status="closed")
        await db.set_alert_status(alert_id, "sent")
        return "Sent to channel (SL)."

    if kind.startswith("tp") and kind[2:].isdigit():
        idx = int(kind[2:])
        if idx < 1 or idx > 5:
            await db.set_alert_status(alert_id, "cancelled")
            return "Invalid TP index. Cancelled."

        text = format_tp_followup(sig.direction, idx, sig.symbol)
        await bot.send_message(
            chat_id=sig.telegram_chat_id,
            text=text,
            reply_parameters={"message_id": sig.telegram_message_id},
        )

        kw: dict[str, object] = {}
        if idx == 1:
            kw["tp1_hit"] = True
            kw["sl_moved_to_be"] = True
        elif idx == 2:
            kw["tp2_hit"] = True
        elif idx == 3:
            kw["tp3_hit"] = True
        elif idx == 4:
            kw["tp4_hit"] = True
        else:
            kw["tp5_hit"] = True

        await db.update_hits_and_status(sig.id, **kw)  # type: ignore[arg-type]
        await db.set_alert_status(alert_id, "sent")

        # If all defined TPs are hit, mark completed.
        refreshed = await db.fetch_signal_by_id(sig.id)
        if refreshed:
            defined = [(1, refreshed.tp1), (2, refreshed.tp2), (3, refreshed.tp3), (4, refreshed.tp4), (5, refreshed.tp5)]
            tp_defined = [i for i, v in defined if v is not None]
            if tp_defined and all(getattr(refreshed, f"tp{i}_hit") for i in tp_defined):
                await db.update_hits_and_status(refreshed.id, status="completed")

        return f"Sent to channel (TP{idx})."

    await db.set_alert_status(alert_id, "cancelled")
    return "Unknown alert kind. Cancelled."


@router.callback_query(F.data.startswith("alert:"), _DM_CALLBACK)
async def on_followup_approval(
    callback: CallbackQuery,
    app_ctx: AppContext,
) -> None:
    # callback data: alert:send:<id> | alert:cancel:<id>
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
        msg = await _post_to_channel(app_ctx.db, callback.bot, alert_id, action, app_ctx)
        log.info("followup %s alert=%s by admin=%s", action, alert_id, callback.from_user.id if callback.from_user else None)
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
