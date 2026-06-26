from __future__ import annotations

from typing import List, Tuple

from app.events import render_event
from app.parser import ParsedSignal


_TP_ICONS = ("🥉", "🥈", "🥇", "🏆", "💎")

_VIP_FOOTER = (
    "🔥 Trade the plan.",
    "🛡 Protect your capital.",
    "🚀 Let winners run."
)


def fmt_pair_title(direction: str, symbol_display: str) -> str:
    direction = direction.upper()

    if direction == "BUY":
        return f"🚨🟢 {symbol_display} BUY SIGNAL 🟢🚨"
    return f"🚨🔴 {symbol_display} SELL SIGNAL 🔴🚨"


def format_signal_standard(sig: ParsedSignal) -> str:
    symbol = sig.symbol.upper()
    display = "GOLD" if symbol == "XAUUSD" else symbol

    title = fmt_pair_title(sig.direction, display)

    entry = (
        f"💎 Entry Zone: {sig.entry_min:g} → {sig.entry_max:g}"
        if sig.entry_min != sig.entry_max
        else f"💎 Entry: {sig.entry_min:g}"
    )

    icons = _TP_ICONS if sig.direction.upper() == "BUY" else _TP_ICONS

    ordered = [(i, sig.tp_levels[i]) for i in sig.tp_order]

    tp_section = ["🎯 PROFIT TARGETS"]
    if ordered:
        for idx, price in ordered:
            icon = icons[min(idx - 1, len(icons) - 1)]
            tp_section.append(f"{icon} TP{idx} → {price:g}")
    else:
        tp_section.append("▪ No targets provided")

    sl = f"🛡 Stop Loss: {sig.sl:g}"

    footer = "\n".join(_VIP_FOOTER)

    return "\n".join([
        title,
        "",
        entry,
        "",
        *tp_section,
        "",
        sl,
        "",
        footer
    ])


def format_signal_elite(
    sig: ParsedSignal,
    *,
    order_type: str = "",
    market_insight: str = "",
    risk_management: str = "",
) -> str:
    symbol = sig.symbol.upper()
    direction = sig.direction.upper()

    display = "GOLD" if symbol == "XAUUSD" else symbol

    ot = order_type.strip().upper()
    if ot not in {"LIMIT", "MARKET", "STOP"}:
        ot = "LIMIT" if sig.entry_min != sig.entry_max else "MARKET"

    title = f"🏆 VIP {display} {direction} {ot}"

    entry = (
        f"{sig.entry_min:g} - {sig.entry_max:g}"
        if sig.entry_min != sig.entry_max
        else f"{sig.entry_min:g}"
    )

    icons = _TP_ICONS
    ordered = [(i, sig.tp_levels[i]) for i in sig.tp_order]

    tp_lines: List[str] = []
    for idx, price in ordered:
        icon = icons[min(idx - 1, len(icons) - 1)]
        tp_lines.append(f"{icon} TP{idx} → {price:g}")

    if not tp_lines:
        tp_lines.append("🥉 TP1 → Not provided")

    risk = risk_management.strip() or "Risk 1% per trade"

    blocks = [
        title,
        "",
        "💎 ENTRY ZONE",
        entry,
        "",
        "🎯 PROFIT TARGETS",
        *tp_lines,
    ]

    if len(ordered) > 1:
        blocks += ["", "🚀 RUNNER ACTIVE"]

    blocks += [
        "",
        "🛡 STOP LOSS",
        f"{sig.sl:g}",
    ]

    if market_insight.strip():
        blocks += [
            "",
            "📊 MARKET INSIGHT",
            market_insight.strip(),
        ]

    blocks += [
        "",
        "⚠️ RISK",
        risk,
        "",
        *_VIP_FOOTER
    ]

    # clean spacing
    out: List[str] = []
    for line in blocks:
        if line == "" and (not out or out[-1] == ""):
            continue
        out.append(line)

    return "\n".join(out)


def add_vip_header(body: str) -> str:
    return f"🔥 VIP EXCLUSIVE SIGNAL 🔥\n\n{body}"


def add_free_cta(body: str, username: str) -> str:
    username = username.strip().lstrip("@")
    return body + f"\n\n🚀 Want VIP Access?\n📩 @{username}"


def format_tp_followup(tp_index: int, symbol: str) -> str:
    """Backward-compatible TP renderer. Delegates to events registry."""
    text = render_event(f"tp{tp_index}", symbol)
    if text is None:
        # Unknown TP index — fall back to a generic line rather than crashing.
        sym = symbol.upper()
        display = "GOLD" if sym == "XAUUSD" else sym
        return f"🎯 TP{tp_index} HIT — {display}"
    return text


def format_sl_followup(symbol: str) -> str:
    """Backward-compatible SL renderer. Delegates to events registry."""
    return render_event("sl", symbol) or symbol


def format_be_followup(symbol: str) -> str:
    """Break-even renderer (price returned to entry after TP1)."""
    return render_event("be", symbol) or symbol