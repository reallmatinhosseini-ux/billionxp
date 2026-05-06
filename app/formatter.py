from __future__ import annotations

from app.parser import ParsedSignal


_TP_ICONS_SELL = ("✅", "✅✅", "✅✅✅", "✅✅✅✅", "▪✅✅✅✅✅")
_TP_ICONS_BUY = ("✅", "✅✅", "✅✅✅", "✅✅✅✅", "▪✅✅✅✅✅")


def fmt_pair_title(direction: str, symbol_display: str) -> str:
    d = direction.upper()
    emoji = "🟢" if d == "BUY" else "🔴"
    return f"{emoji} {symbol_display} {d} SIGNAL"


def format_signal_standard(sig: ParsedSignal) -> str:
    """Premium channel-ready body matching the STANDARD template."""
    sym = sig.symbol.upper()
    display = sym.replace("XAUUSD", "GOLD") if sym == "XAUUSD" else sym

    icon_row = fmt_pair_title(sig.direction, display)

    line_entry = (
        f"💰 Entry Zone: {sig.entry_min:g} → {sig.entry_max:g}"
        if sig.entry_min != sig.entry_max
        else f"💰 Entry: {sig.entry_min:g}"
    )

    icons = _TP_ICONS_BUY if sig.direction.upper() == "BUY" else _TP_ICONS_SELL
    tp_lines = ["🎯 Take Profit Targets:"]

    ordered = [(i, sig.tp_levels[i]) for i in sig.tp_order]
    if not ordered:
        tp_lines.append("▸ _(no targets)_")
    for lbl, price in ordered:
        icon = icons[(lbl - 1) % len(icons)]
        tp_lines.append(f"▸ TP{lbl} → {price:g} {icon}")

    sl_line = f"⛔ Stop Loss: {sig.sl:g}"

    footer = (
        "⚠️ Use proper risk management. Discipline is your real edge."
    )

    blocks = [
        icon_row,
        "",
        line_entry,
        "",
        *tp_lines,
        "",
        sl_line,
        "",
        footer,
    ]
    return "\n".join(blocks)


def add_vip_header(body: str) -> str:
    return "🔥 VIP EXCLUSIVE SIGNAL\n\n" + body


def add_free_cta(body: str, username_without_at: str) -> str:
    uname = username_without_at.strip().lstrip("@")
    cta = f"🚀 Want full VIP access?\nMessage: @{uname}"
    return body + "\n\n" + cta


def tp_hit_title(tp_index: int) -> tuple[str, str]:
    """Return title and optional subtitle hints for alerts."""
    if tp_index <= 2:
        return "✅ TP1 HIT" if tp_index == 1 else "✅ TP2 HIT", ""
    return "✅ TARGET HIT", ""


def format_tp_followup(direction: str, tp_index: int, symbol_display: str) -> str:
    sym = symbol_display.upper()
    display = sym.replace("XAUUSD", "GOLD")

    title, _ = tp_hit_title(tp_index)
    lines = [title, ""]

    if tp_index == 1:
        lines.extend(
            [
                f"{display} reached the first target 🔥",
                "Secure your position and move SL to BE.",
            ]
        )
    elif tp_index == 2:
        lines.extend(
            [
                f"Strong move {'📉' if direction.upper()=='SELL' else '📈'}🔥",
                "Partial profit secured",
                "Set SL to BE.",
            ]
        )
    else:
        lines.extend(
            [
                "Momentum is clean 🔥",
                "Let the trade run.",
            ]
        )

    return "\n".join(lines)


def format_sl_followup(symbol_display: str) -> str:
    display = symbol_display.upper().replace("XAUUSD", "GOLD")
    lines = [
        "⛔ SL HIT",
        "",
        f"This position closed at stop loss on {display}.",
        "",
        "Losses are part of the game.",
        "Stay disciplined.",
    ]
    return "\n".join(lines)
