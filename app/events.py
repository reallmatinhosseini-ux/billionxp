"""
Event registry for trade lifecycle notifications.

Each event (TP1, TP2, TP3, TP4, TP5, SL, BE) lives in its own independent
configuration block below. To tweak a message, edit only that block.
To add a new event, append a new block and register it in `_REGISTRY`.

The tracker and follow-up handler both read this registry — they never
hard-code TP/SL/BE behavior themselves.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Mapping


# ─────────────────────────────────────────────────────────────────────────────
# Event metadata
# ─────────────────────────────────────────────────────────────────────────────


@dataclass(frozen=True)
class EventConfig:
    code: str                          # internal id stored in the alerts table
    label: str                         # short human label, e.g. "TP1 HIT"
    render: Callable[[str], str]       # (display_symbol) -> follow-up message
    moves_sl_to_be: bool = False       # flip sl_moved_to_be flag on signal
    closes_signal: bool = False        # set status='closed' after sending
    is_take_profit: bool = False       # contributes to "all TPs hit -> completed"
    tp_index: int | None = None        # 1..5 when is_take_profit


def _display_symbol(symbol: str) -> str:
    sym = (symbol or "").upper()
    return "GOLD" if sym == "XAUUSD" else sym


# ─────────────────────────────────────────────────────────────────────────────
# TP1
# ─────────────────────────────────────────────────────────────────────────────

def _render_tp1(symbol: str) -> str:
    s = _display_symbol(symbol)
    return (
        f"🎯 TP1 HIT — {s}\n"
        "\n"
        "✅ First target secured\n"
        "💰 Take partial profits\n"
        "🛡 SL moved to Break Even\n"
        "🚀 Let the runner work"
    )


TP1 = EventConfig(
    code="tp1",
    label="TP1 HIT",
    render=_render_tp1,
    moves_sl_to_be=True,
    is_take_profit=True,
    tp_index=1,
)


# ─────────────────────────────────────────────────────────────────────────────
# TP2
# ─────────────────────────────────────────────────────────────────────────────

def _render_tp2(symbol: str) -> str:
    s = _display_symbol(symbol)
    return (
        f"🚀 TP2 HIT — {s}\n"
        "\n"
        "💰 Profits stacking up\n"
        "📈 Momentum confirmed\n"
        "🔥 Hold the remaining position"
    )


TP2 = EventConfig(
    code="tp2",
    label="TP2 HIT",
    render=_render_tp2,
    is_take_profit=True,
    tp_index=2,
)


# ─────────────────────────────────────────────────────────────────────────────
# TP3
# ─────────────────────────────────────────────────────────────────────────────

def _render_tp3(symbol: str) -> str:
    s = _display_symbol(symbol)
    return (
        f"🏆 TP3 HIT — {s}\n"
        "\n"
        "💎 Major target reached\n"
        "📊 Trade now risk-free\n"
        "⚡ Trend still in our favour"
    )


TP3 = EventConfig(
    code="tp3",
    label="TP3 HIT",
    render=_render_tp3,
    is_take_profit=True,
    tp_index=3,
)


# ─────────────────────────────────────────────────────────────────────────────
# TP4
# ─────────────────────────────────────────────────────────────────────────────

def _render_tp4(symbol: str) -> str:
    s = _display_symbol(symbol)
    return (
        f"💎 TP4 HIT — {s}\n"
        "\n"
        "🔥 Exceptional move\n"
        "📈 Trend extending\n"
        "🚀 One target remaining"
    )


TP4 = EventConfig(
    code="tp4",
    label="TP4 HIT",
    render=_render_tp4,
    is_take_profit=True,
    tp_index=4,
)


# ─────────────────────────────────────────────────────────────────────────────
# TP5
# ─────────────────────────────────────────────────────────────────────────────

def _render_tp5(symbol: str) -> str:
    s = _display_symbol(symbol)
    return (
        f"👑 TP5 HIT — FULL TARGET — {s}\n"
        "\n"
        "🏆 Every level reached\n"
        "💰 Maximum profit secured\n"
        "🎉 Congratulations to all members"
    )


TP5 = EventConfig(
    code="tp5",
    label="TP5 HIT",
    render=_render_tp5,
    is_take_profit=True,
    tp_index=5,
)


# ─────────────────────────────────────────────────────────────────────────────
# SL — Stop Loss
# ─────────────────────────────────────────────────────────────────────────────

def _render_sl(symbol: str) -> str:
    s = _display_symbol(symbol)
    return (
        f"⛔ STOP LOSS HIT — {s}\n"
        "\n"
        "📉 Trade closed at SL\n"
        "🛡 Capital protected — discipline first\n"
        "🔥 Resetting for the next high-quality setup"
    )


SL = EventConfig(
    code="sl",
    label="SL HIT",
    render=_render_sl,
    closes_signal=True,
)


# ─────────────────────────────────────────────────────────────────────────────
# BE — Break Even (price returned to entry after TP1 already secured)
# ─────────────────────────────────────────────────────────────────────────────

def _render_be(symbol: str) -> str:
    s = _display_symbol(symbol)
    return (
        f"⚖️ BREAK EVEN — {s}\n"
        "\n"
        "🛡 Trade closed at entry — zero loss\n"
        "✅ Profit from TP1 already locked\n"
        "🔥 On to the next opportunity"
    )


BE = EventConfig(
    code="be",
    label="BREAK EVEN",
    render=_render_be,
    closes_signal=True,
)


# ─────────────────────────────────────────────────────────────────────────────
# Registry
# ─────────────────────────────────────────────────────────────────────────────

_REGISTRY: Mapping[str, EventConfig] = {
    e.code: e for e in (TP1, TP2, TP3, TP4, TP5, SL, BE)
}


def get_event(code: str) -> EventConfig | None:
    return _REGISTRY.get((code or "").lower().strip())


def all_take_profits() -> tuple[EventConfig, ...]:
    return tuple(e for e in _REGISTRY.values() if e.is_take_profit)


def render_event(code: str, symbol: str) -> str | None:
    cfg = get_event(code)
    if cfg is None:
        return None
    return cfg.render(symbol)
