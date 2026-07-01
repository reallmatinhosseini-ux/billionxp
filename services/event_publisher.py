"""
Single source of truth for posting event followups to a channel.

Both the followup approval handler (manual admin approval flow) and the
tracker (auto-approve mode) route through `publish_event_to_channel` so that
side-effects — DB flag updates, channel post, FULL TP auto-fire — happen in
exactly one place.
"""

from __future__ import annotations

from aiogram import Bot

from app.database import Database, SignalRecord
from app.events import EventConfig, all_take_profits, get_event
from utils.logger import get_logger

log = get_logger(__name__)


def apply_event_flags(event: EventConfig) -> dict[str, object]:
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


async def _post_to_thread(bot: Bot, sig: SignalRecord, text: str) -> None:
    await bot.send_message(
        chat_id=sig.telegram_chat_id,
        text=text,
        reply_parameters={"message_id": sig.telegram_message_id},
    )


async def _maybe_full_tp(bot: Bot, db: Database, sig: SignalRecord) -> None:
    """If every defined TP is now hit, mark completed and post FULL TP HIT."""
    refreshed = await db.fetch_signal_by_id(sig.id)
    if refreshed is None or refreshed.status != "active":
        return
    defined = [
        tp.tp_index
        for tp in all_take_profits()
        if tp.tp_index is not None
        and getattr(refreshed, f"tp{tp.tp_index}") is not None
    ]
    if not defined:
        return
    if not all(getattr(refreshed, f"tp{i}_hit") for i in defined):
        return

    await db.update_hits_and_status(refreshed.id, status="completed")
    full_tp = get_event("full_tp")
    if full_tp is None:
        return
    try:
        await _post_to_thread(bot, refreshed, full_tp.render(refreshed.symbol))
    except Exception:
        log.exception("FULL TP post failed for signal %s", refreshed.id)


async def publish_event_to_channel(
    bot: Bot,
    db: Database,
    sig: SignalRecord,
    event: EventConfig,
) -> None:
    """Post the event text into the signal's channel thread and update flags."""
    await _post_to_thread(bot, sig, event.render(sig.symbol))

    flags = apply_event_flags(event)
    if flags:
        await db.update_hits_and_status(sig.id, **flags)  # type: ignore[arg-type]

    if event.is_take_profit:
        await _maybe_full_tp(bot, db, sig)
