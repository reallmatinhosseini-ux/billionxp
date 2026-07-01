from __future__ import annotations

import asyncio
from dataclasses import dataclass

from aiogram import Bot
from aiogram.types import ReplyParameters

from app.config import Settings
from app.database import Database, SignalRecord
from app.events import EventConfig, all_take_profits, get_event
from app.keyboards import followup_approval_keyboard
from services.event_publisher import publish_event_to_channel
from services.price_provider import PriceProvider
from utils.logger import get_logger

log = get_logger(__name__)


def _reply_params(sig: SignalRecord) -> ReplyParameters:
    return ReplyParameters(message_id=sig.telegram_message_id)


async def _send_admin_alerts(
    bot: Bot, settings: Settings, text: str, alert_id: int
) -> None:
    kb = followup_approval_keyboard(alert_id)
    for admin_id in settings.admin_ids:
        try:
            await bot.send_message(chat_id=admin_id, text=text, reply_markup=kb)
        except Exception:
            log.exception("Failed to DM admin %s for alert %s", admin_id, alert_id)


def _admin_alert_header(sig: SignalRecord, event: EventConfig) -> str:
    return (
        "🚨 LIVE EVENT DETECTED — APPROVAL NEEDED\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        f"🎯 Event:  {event.label}\n"
        f"📊 Trade:  #{sig.id}  {sig.symbol} {sig.direction}\n"
        f"📨 Thread: {sig.telegram_chat_id}:{sig.telegram_message_id}\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        "Tap ✅ SEND to broadcast to the channel.\n"
        "Tap ❌ CANCEL to suppress."
    )


async def _queue_alert(
    bot: Bot,
    settings: Settings,
    db: Database,
    sig: SignalRecord,
    event: EventConfig,
) -> bool:
    """
    Emit an event. In manual mode, queue a pending alert and DM admins for
    approval. In auto-approve mode, post directly to the channel.
    Returns True if a new alert / broadcast was emitted.
    """
    # De-dupe: whether manual or auto, don't re-fire the same event repeatedly.
    pending = await db.fetch_pending_alert_for_signal(sig.id, event.code)
    if pending is not None:
        return False

    if settings.auto_approve_followups:
        # Direct fire — no approval, no alert row.
        try:
            await publish_event_to_channel(bot, db, sig, event)
            log.info("auto-fired %s for signal %s", event.label, sig.id)
        except Exception:
            log.exception(
                "auto-fire failed for signal %s event %s", sig.id, event.code
            )
        return True

    alert_id = await db.create_pending_alert(sig.id, event.code)
    if not alert_id:
        return False
    body = event.render(sig.symbol)
    text = _admin_alert_header(sig, event) + "\n\n" + body
    await _send_admin_alerts(bot, settings, text, alert_id)
    return True


def _sl_triggered(sig: SignalRecord, price: float) -> bool:
    if sig.direction.upper() == "BUY":
        return price <= sig.sl
    return price >= sig.sl


def _tp_reached(sig: SignalRecord, level: float, price: float) -> bool:
    if sig.direction.upper() == "BUY":
        return price >= level
    return price <= level


def _entry_midpoint(sig: SignalRecord) -> float:
    return (sig.entry_min + sig.entry_max) / 2.0


def _be_triggered(sig: SignalRecord, price: float) -> bool:
    """
    BE triggers once TP1 is hit (SL has been moved to entry).
    BUY: price drops back into/under the entry zone.
    SELL: price rallies back into/over the entry zone.
    """
    if sig.direction.upper() == "BUY":
        return price <= _entry_midpoint(sig)
    return price >= _entry_midpoint(sig)


async def evaluate_price_tick(
    bot: Bot,
    settings: Settings,
    db: Database,
    sig: SignalRecord,
    price: float,
) -> None:
    # 1) Stop loss dominates if SL is still the active stop (TP1 not yet hit).
    if not sig.sl_hit and not sig.be_hit and not sig.sl_moved_to_be:
        if _sl_triggered(sig, price):
            event = get_event("sl")
            if event is not None:
                await _queue_alert(bot, settings, db, sig, event)
            return

    # 2) After TP1 has moved SL to entry, a retrace closes the trade at BE.
    if sig.sl_moved_to_be and not sig.be_hit and not sig.sl_hit:
        if _be_triggered(sig, price):
            event = get_event("be")
            if event is not None:
                await _queue_alert(bot, settings, db, sig, event)
            return

    # 3) Take profits, sequentially. Only one TP event per tick.
    for tp in all_take_profits():
        if tp.tp_index is None:
            continue
        level = getattr(sig, f"tp{tp.tp_index}")
        if level is None:
            continue
        if getattr(sig, f"tp{tp.tp_index}_hit"):
            continue
        if not _tp_reached(sig, float(level), price):
            break

        await _queue_alert(bot, settings, db, sig, tp)
        break


@dataclass
class TrackerService:
    settings: Settings
    db: Database
    bot: Bot
    price_provider: PriceProvider

    async def loop_forever(self) -> None:
        delay = float(self.settings.check_interval_seconds)
        await asyncio.sleep(1)

        while True:
            try:
                await self._tick()
            except asyncio.CancelledError:
                raise
            except Exception:
                log.exception("Tracker tick crashed; continuing")
            await asyncio.sleep(delay)

    async def _tick(self) -> None:
        active = await self.db.fetch_active_signals()
        if not active:
            return

        by_symbol: dict[str, list[SignalRecord]] = {}
        for sig in active:
            by_symbol.setdefault(sig.symbol.upper(), []).append(sig)

        for sym, records in by_symbol.items():
            try:
                price = await self.price_provider.get_current_price(sym)
            except Exception:
                log.exception("price fetch failed for %s", sym)
                continue

            for sig in records:
                await evaluate_price_tick(self.bot, self.settings, self.db, sig, price)


async def tracker_loop(bot: Bot, svc: TrackerService) -> None:
    await svc.loop_forever()
