from __future__ import annotations

from typing import List

from app.events import render_event
from app.parser import ParsedSignal


_ALLOWED_EMOJIS = ("🏆", "🎯", "🛡", "⚡", "🔥")

_DEFAULT_DISCIPLINE = "Risk 1%. Trust the plan."


def _display(symbol: str) -> str:
    s = (symbol or "").upper()
    return "GOLD" if s == "XAUUSD" else s


def _resolve_order_type(order_type: str, entry_min: float, entry_max: float) -> str:
    ot = (order_type or "").strip().upper()
    if ot in {"LIMIT", "MARKET", "STOP"}:
        return ot
    return "LIMIT" if entry_min != entry_max else "MARKET"


def _direction_label(direction: str, order_type: str) -> str:
    """`BUY LIMIT`, `SELL STOP`, or bare `BUY` for MARKET orders."""
    d = direction.upper()
    if order_type == "MARKET":
        return d
    return f"{d} {order_type}"


def _entry_value(sig: ParsedSignal) -> str:
    if sig.entry_min != sig.entry_max:
        return f"{sig.entry_min:g} – {sig.entry_max:g}"
    return f"{sig.entry_min:g}"


def fmt_pair_title(direction: str, symbol_display: str) -> str:
    return f"🏆 {symbol_display} • {direction.upper()}"


def _core_signal_block(
    sig: ParsedSignal,
    *,
    order_type: str,
    market_insight: str,
    risk_management: str,
) -> str:
    """Institutional-style block. Minimal, scannable, allowed emojis only."""
    display = _display(sig.symbol)
    ot = _resolve_order_type(order_type, sig.entry_min, sig.entry_max)
    direction_label = _direction_label(sig.direction, ot)

    lines: List[str] = [
        f"🏆 {display} • {direction_label}",
        "",
        f"ENTRY : {_entry_value(sig)}",
        "",
    ]
    for idx in sig.tp_order:
        lines.append(f"🎯 TP{idx} : {sig.tp_levels[idx]:g}")
    if not sig.tp_order:
        lines.append("🎯 TP : —")

    lines += ["", f"🛡 SL : {sig.sl:g}"]

    insight = (market_insight or "").strip()
    discipline = (risk_management or "").strip() or _DEFAULT_DISCIPLINE

    lines.append("")
    if insight:
        lines.append(f"⚡ {insight}")
    lines.append(f"🔥 {discipline}")

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
    """VIP body needs no extra header — the 🏆 title already signals VIP-grade."""
    return body


def add_free_cta(body: str, username: str) -> str:
    """Single-line institutional CTA. No marketing fluff."""
    username = username.strip().lstrip("@")
    return f"{body}\n\n🏆 VIP access — @{username}"


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
