from __future__ import annotations

import asyncio
from dataclasses import dataclass

from aiogram import Bot
from aiogram.types import ReplyParameters

from app.database import AlertRecord, Database, SignalRecord
from app.formatter import format_sl_followup, format_tp_followup
from app.config import Settings
from app.keyboards import followup_approval_keyboard
from services.price_provider import PriceProvider
from utils.logger import get_logger

log = get_logger(__name__)


def _reply_params(sig: SignalRecord) -> ReplyParameters:
    # Reply threading only when numeric message id fits Telegram rules.
    return ReplyParameters(message_id=sig.telegram_message_id)


async def _mark_tp_hit(db: Database, signal_id: int, idx: int) -> None:
    if idx == 1:
        await db.update_hits_and_status(
            signal_id, tp1_hit=True, sl_moved_to_be=True
        )
    elif idx == 2:
        await db.update_hits_and_status(signal_id, tp2_hit=True)
    elif idx == 3:
        await db.update_hits_and_status(signal_id, tp3_hit=True)
    elif idx == 4:
        await db.update_hits_and_status(signal_id, tp4_hit=True)
    else:
        await db.update_hits_and_status(signal_id, tp5_hit=True)


async def _send_admin_alerts(
    bot: Bot, settings: Settings, text: str, alert_id: int
) -> None:
    kb = followup_approval_keyboard(alert_id)
    for admin_id in settings.admin_ids:
        try:
            await bot.send_message(chat_id=admin_id, text=text, reply_markup=kb)
        except Exception:
            log.exception("Failed to DM admin %s for alert %s", admin_id, alert_id)


def _admin_alert_header(sig: SignalRecord, kind: str) -> str:
    return (
        "⚠️ Follow-up pending approval\n"
        f"Signal #{sig.id} {sig.symbol} {sig.direction}\n"
        f"Event: {kind.upper()}\n"
        f"Channel msg: {sig.telegram_chat_id}:{sig.telegram_message_id}\n"
        "\n"
        "Click SEND to post in channel, or CANCEL."
    )


async def evaluate_price_tick(
    bot: Bot,
    settings: Settings,
    db: Database,
    sig: SignalRecord,
    price: float,
) -> None:
    d = sig.direction.upper()
    tp_getters = [(1, sig.tp1), (2, sig.tp2), (3, sig.tp3), (4, sig.tp4), (5, sig.tp5)]
    tp_defined = [(i, t) for i, t in tp_getters if t is not None]

    def tp_flag(i: int) -> bool:
        return bool(getattr(sig, f"tp{i}_hit"))

    def sl_triggered(p: float) -> bool:
        if d == "BUY":
            return p <= sig.sl
        return p >= sig.sl

    def tp_hit_level(p: float, level: float) -> bool:
        if d == "BUY":
            return p >= level
        return p <= level

    # Stop loss dominates while still active tracking.
    if not sig.sl_hit and sl_triggered(price):
        kind = "sl"
        pending = await db.fetch_pending_alert_for_signal(sig.id, kind)
        if pending is None:
            alert_id = await db.create_pending_alert(sig.id, kind)
            if alert_id:
                body = format_sl_followup(sig.symbol)
                text = _admin_alert_header(sig, kind) + "\n\n" + body
                await _send_admin_alerts(bot, settings, text, alert_id)
        return

    if sig.sl_hit:
        return

    # Take profits sequentially; never post automatically — require admin approval.
    for idx, lvl in tp_defined:
        if tp_flag(idx):
            continue
        if not tp_hit_level(price, lvl):
            break

        kind = f"tp{idx}"
        pending = await db.fetch_pending_alert_for_signal(sig.id, kind)
        if pending is None:
            alert_id = await db.create_pending_alert(sig.id, kind)
            if alert_id:
                body = format_tp_followup(sig.direction, idx, sig.symbol)
                text = _admin_alert_header(sig, kind) + "\n\n" + body
                await _send_admin_alerts(bot, settings, text, alert_id)
        # Only one event per tick.
        break

    # Note: completion/closure happens only after admin approval updates hit flags.


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
