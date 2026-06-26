from __future__ import annotations

from typing import List, Tuple
from app.parser import ParsedSignal


_TP_ICONS_BUY = (
    "🥉",
    "🥈",
    "🥇",
    "🏆",
    "💎",
)

_TP_ICONS_SELL = (
    "🥉",
    "🥈",
    "🥇",
    "🏆",
    "💎",
)

_VIP_FOOTER = (
    "🔥 Trade the plan.\n"
    "🛡 Protect your capital.\n"
    "🚀 Let winners run."
)


def fmt_pair_title(direction: str, symbol_display: str) -> str:
    if direction.upper() == "BUY":
        return f"🚨🟢 {symbol_display} BUY SIGNAL 🟢🚨"
    return f"🚨🔴 {symbol_display} SELL SIGNAL 🔴🚨"


def format_signal_standard(sig: ParsedSignal) -> str:
    sym = sig.symbol.upper()
    display = "GOLD" if sym == "XAUUSD" else sym

    icon_row = fmt_pair_title(sig.direction, display)

    line_entry = (
        f"💎 Entry Zone: {sig.entry_min:g} → {sig.entry_max:g}"
        if sig.entry_min != sig.entry_max
        else f"💎 Entry: {sig.entry_min:g}"
    )

    icons = _TP_ICONS_BUY if sig.direction.upper() == "BUY" else _TP_ICONS_SELL

    tp_lines = ["🎯 PROFIT TARGETS"]

    ordered = [(i, sig.tp_levels[i]) for i in sig.tp_order]

    if not ordered:
        tp_lines.append("▪ No targets provided")

    for lbl, price in ordered:
        icon = icons[min(lbl - 1, len(icons) - 1)]
        tp_lines.append(f"{icon} TP{lbl} → {price:g}")

    sl_line = f"🛡 Stop Loss: {sig.sl:g}"

    footer = (
        "⚡ High Probability Setup\n"
        "🛡 Risk Managed\n"
        "🚀 Follow The Plan"
    )

    return "\n".join([
        icon_row,
        "",
        line_entry,
        "",
        *tp_lines,
        "",
        sl_line,
        "",
        footer,
    ])


def format_signal_elite(
    sig: ParsedSignal,
    *,
    order_type: str = "",
    market_insight: str = "",
    risk_management: str = "",
) -> str:
    sym = sig.symbol.upper()
    direction = sig.direction.upper()

    ot = order_type.strip().upper()
    if ot not in {"LIMIT", "MARKET", "STOP"}:
        ot = "LIMIT" if sig.entry_min != sig.entry_max else "MARKET"

    title = f"🏆🚨 VIP {sym} {direction} {ot} 🚨🏆"

    entry_line = (
        f"{sig.entry_min:g} - {sig.entry_max:g}"
        if sig.entry_min != sig.entry_max
        else f"{sig.entry_min:g}"
    )

    icons = _TP_ICONS_BUY if direction == "BUY" else _TP_ICONS_SELL

    ordered = [(i, sig.tp_levels[i]) for i in sig.tp_order]

    tp_lines: List[str] = []
    for idx, price in ordered:
        icon = icons[min(idx - 1, len(icons) - 1)]
        tp_lines.append(f"{icon} TP{idx} → {price:g}")

    if not tp_lines:
        tp_lines.append("🥉 TP1 → (not provided)")

    risk = risk_management.strip() or "Risk 1% Per Trade"

    blocks = [
        title,
        "",
        "💎 ENTRY ZONE",
        entry_line,
        "",
        "🎯 PROFIT TARGETS",
        *tp_lines,
    ]

    if len(ordered) > 1:
        blocks += ["", "🚀 RUNNER OPEN"]

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
        *_VIP_FOOTER,
    ]

    # clean double empty lines
    out: List[str] = []
    for line in blocks:
        if line == "" and (not out or out[-1] == ""):
            continue
        out.append(line)

    return "\n".join(out)


def add_vip_header(body: str) -> str:
    return "🔥 VIP EXCLUSIVE SIGNAL 🔥\n\n" + body


def add_free_cta(body: str, username_without_at: str) -> str:
    uname = username_without_at.strip().lstrip("@")
    return body + f"\n\n🚀 Want Full VIP Access?\n📩 Message: @{uname}"


def tp_hit_title(tp_index: int) -> Tuple[str, str]:
    if tp_index == 1:
        return "🎯🔥 TP1 HIT 🔥🎯", ""
    if tp_index == 2:
        return "🚀🚀 TP2 HIT 🚀🚀", ""
    return f"🏆 TARGET {tp_index} HIT 🏆", ""


def format_tp_followup(direction: str, tp_index: int, symbol_display: str) -> str:
    sym = symbol_display.upper()
    display = "GOLD" if sym == "XAUUSD" else sym

    if tp_index == 1:
        return "\n".join([
            f"🎯🔥 TP1 HIT ON {display} 🔥🎯",
            "",
            "✅ Partial profits secured",
            "🛡 Move SL to Break Even",
            "🚀 Next target loading..."
        ])

    if tp_index == 2:
        return "\n".join([
            f"🚀🚀 TP2 HIT ON {display} 🚀🚀",
            "",
            "💰 More profits locked in",
            "📈 Momentum remains strong",
            "🔥 Hold runners",
            "🎯 TP3 in sight"
        ])

    return "\n".join([
        f"🏆 TARGET {tp_index} HIT ON {display} 🏆",
        "",
        "💎 Massive profits secured",
        "⚡ Trend remains strong",
        "🚀 Let the runner work"
    ])


def format_sl_followup(symbol_display: str) -> str:
    display = symbol_display.upper().replace("XAUUSD", "GOLD")

    return "\n".join([
        "⛔ STOP LOSS HIT",
        "",
        f"{display} trade closed.",
        "",
        "🛡 Loss controlled.",
        "📊 Capital protected.",
        "",
        "🔥 Stay disciplined.",
        "🚀 Next opportunity is coming."
    ])