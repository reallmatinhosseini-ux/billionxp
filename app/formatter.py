from __future__ import annotations

from typing import List

from app.events import render_event
from app.parser import ParsedSignal


_TP_ICONS = ("🥉", "🥈", "🥇", "🏆", "💎", "👑", "⚡")

_DIVIDER = "━━━━━━━━━━━━━━━━━━━━"

_VIP_FOOTER = (
    "🔥 Trade the plan. Always.",
    "🛡 Capital is the weapon — protect it.",
    "🚀 Patience pays. Let winners run.",
)


def _display(symbol: str) -> str:
    s = (symbol or "").upper()
    return "GOLD" if s == "XAUUSD" else s


def fmt_pair_title(direction: str, symbol_display: str) -> str:
    direction = direction.upper()
    if direction == "BUY":
        return f"🚨🟢 {symbol_display} BUY SIGNAL 🟢🚨"
    return f"🚨🔴 {symbol_display} SELL SIGNAL 🔴🚨"


def format_signal_standard(sig: ParsedSignal) -> str:
    display = _display(sig.symbol)
    title = fmt_pair_title(sig.direction, display)

    entry = (
        f"💎 Entry Zone:  {sig.entry_min:g}  →  {sig.entry_max:g}"
        if sig.entry_min != sig.entry_max
        else f"💎 Entry:  {sig.entry_min:g}"
    )

    ordered = [(i, sig.tp_levels[i]) for i in sig.tp_order]

    tp_section = ["🎯 PROFIT TARGETS"]
    if ordered:
        for idx, price in ordered:
            icon = _TP_ICONS[min(idx - 1, len(_TP_ICONS) - 1)]
            tp_section.append(f"{icon} TP{idx} → {price:g}")
    else:
        tp_section.append("▪ No targets provided")

    sl = f"🛡 Stop Loss: {sig.sl:g}"

    return "\n".join(
        [
            title,
            _DIVIDER,
            "",
            entry,
            "",
            *tp_section,
            "",
            sl,
            "",
            _DIVIDER,
            *_VIP_FOOTER,
        ]
    )


def format_signal_elite(
    sig: ParsedSignal,
    *,
    order_type: str = "",
    market_insight: str = "",
    risk_management: str = "",
) -> str:
    display = _display(sig.symbol)
    direction = sig.direction.upper()

    ot = order_type.strip().upper()
    if ot not in {"LIMIT", "MARKET", "STOP"}:
        ot = "LIMIT" if sig.entry_min != sig.entry_max else "MARKET"

    title = f"🏆 VIP ELITE — {display} {direction} {ot} 🏆"

    entry = (
        f"{sig.entry_min:g}  →  {sig.entry_max:g}"
        if sig.entry_min != sig.entry_max
        else f"{sig.entry_min:g}"
    )

    ordered = [(i, sig.tp_levels[i]) for i in sig.tp_order]

    tp_lines: List[str] = []
    for idx, price in ordered:
        icon = _TP_ICONS[min(idx - 1, len(_TP_ICONS) - 1)]
        tp_lines.append(f"{icon} TP{idx} → {price:g}")
    if not tp_lines:
        tp_lines.append("🥉 TP1 → Not provided")

    risk = risk_management.strip() or "Risk 1% per trade — never more."

    blocks: List[str] = [
        title,
        _DIVIDER,
        "",
        "💎 ENTRY ZONE",
        entry,
        "",
        "🎯 PROFIT TARGETS",
        *tp_lines,
    ]

    if len(ordered) > 1:
        blocks += ["", "🚀 RUNNER ACTIVE — Multi-target play. Hold for the move."]

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
        "⚠️ RISK MANAGEMENT",
        risk,
        "",
        _DIVIDER,
        *_VIP_FOOTER,
    ]

    # Collapse runs of blank lines for clean spacing.
    out: List[str] = []
    for line in blocks:
        if line == "" and (not out or out[-1] == ""):
            continue
        out.append(line)
    return "\n".join(out)


def add_vip_header(body: str) -> str:
    return (
        "🔥 VIP EXCLUSIVE — INNER CIRCLE ONLY 🔥\n"
        "💎 Real-time. Real edge. Zero noise.\n"
        f"{_DIVIDER}\n"
        "\n"
        f"{body}"
    )


def add_free_cta(body: str, username: str) -> str:
    """Free-channel CTA — built to convert. Strong FOMO without spam."""
    username = username.strip().lstrip("@")
    cta = (
        "\n"
        f"{_DIVIDER}\n"
        "🚨 You’re reading this on the FREE channel.\n"
        "🏆 VIP members had it the moment it printed.\n"
        "💎 Stop trading the leftovers — get the first call, every time.\n"
        "\n"
        f"📩 DM for VIP access → @{username}\n"
        "⏳ Seats are limited. Doors close without warning."
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
