from __future__ import annotations

from typing import List

from app.events import render_event
from app.parser import ParsedSignal


_DIVIDER = "━━━━━━━━━━━━━━━"


def _display(symbol: str) -> str:
    s = (symbol or "").upper()
    return "GOLD" if s == "XAUUSD" else s


def _direction_dot(direction: str) -> str:
    return "🟢" if direction.upper() == "BUY" else "🔴"


def _resolve_order_type(order_type: str, entry_min: float, entry_max: float) -> str:
    ot = (order_type or "").strip().upper()
    if ot in {"LIMIT", "MARKET", "STOP"}:
        return ot
    return "LIMIT" if entry_min != entry_max else "MARKET"


def _entry_value(sig: ParsedSignal) -> str:
    if sig.entry_min != sig.entry_max:
        return f"{sig.entry_min:g} → {sig.entry_max:g}"
    return f"{sig.entry_min:g}"


def fmt_pair_title(direction: str, symbol_display: str) -> str:
    return f"{_direction_dot(direction)} {symbol_display} {direction.upper()}"


def _core_signal_block(
    sig: ParsedSignal,
    *,
    order_type: str,
    market_insight: str,
    risk_management: str,
) -> str:
    """Compact, scannable signal body. ~10 lines."""
    display = _display(sig.symbol)
    direction = sig.direction.upper()
    ot = _resolve_order_type(order_type, sig.entry_min, sig.entry_max)

    lines: List[str] = [
        f"{_direction_dot(direction)} {display} {direction} {ot}",
        _DIVIDER,
        f"💎 Entry: {_entry_value(sig)}",
        f"🛡 SL: {sig.sl:g}",
        "",
    ]
    for idx in sig.tp_order:
        lines.append(f"🎯 TP{idx}: {sig.tp_levels[idx]:g}")
    if not sig.tp_order:
        lines.append("🎯 TP: —")

    insight = (market_insight or "").strip()
    if insight:
        lines += ["", f"📊 {insight}"]

    risk = (risk_management or "").strip() or "Risk 1% max"
    lines += ["", _DIVIDER, f"⚠️ {risk}"]
    return "\n".join(lines)


def format_signal_standard(sig: ParsedSignal) -> str:
    return _core_signal_block(
        sig, order_type="", market_insight="", risk_management=""
    )


def format_signal_elite(
    sig: ParsedSignal,
    *,
    order_type: str = "",
    market_insight: str = "",
    risk_management: str = "",
) -> str:
    return _core_signal_block(
        sig,
        order_type=order_type,
        market_insight=market_insight,
        risk_management=risk_management,
    )


def add_vip_header(body: str) -> str:
    return f"🔥 VIP EXCLUSIVE 🔥\n{body}"


def add_free_cta(body: str, username: str) -> str:
    """Free-channel CTA — short, sharp, max FOMO."""
    username = username.strip().lstrip("@")
    cta = (
        "\n\n"
        f"{_DIVIDER}\n"
        "⏰ You’re seeing this LATE.\n"
        "🏆 VIP got the call first — they always do.\n"
        "💎 Limited seats. No second chances.\n"
        "🚪 Doors close without warning.\n"
        f"📩 DM @{username} for VIP access."
    )
    return body + cta


def format_tp_followup(tp_index: int, symbol: str) -> str:
    """Backward-compatible TP renderer. Delegates to the events registry."""
    text = render_event(f"tp{tp_index}", symbol)
    if text is None:
        return f"🎯 TP{tp_index} HIT — {_display(symbol)}"
    return text


def format_sl_followup(symbol: str) -> str:
    return render_event("sl", symbol) or symbol


def format_be_followup(symbol: str) -> str:
    return render_event("be", symbol) or symbol
