"""
Event registry for trade lifecycle notifications.

Each event (TP1..TP7, SL, BE) lives in its own independent configuration
block below. To tweak a message, edit only that block. To add a new event,
append a new block and register it in `_REGISTRY`.

The tracker and follow-up handler both read this registry — they never
hard-code TP/SL/BE behavior themselves.

A note on `tracked`:
- TP1..TP5 are persisted on the signals table and watched by the live
  price tracker (`tracked=True`).
- TP6 and TP7 exist only for manual broadcasts via the TP Sender flow
  (`tracked=False`) — they have no DB column and the tracker ignores them.
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
    tp_index: int | None = None        # 1..7 when is_take_profit
    tracked: bool = True               # False = manual-only (no DB column)


def _display_symbol(symbol: str) -> str:
    sym = (symbol or "").upper()
    return "GOLD" if sym == "XAUUSD" else sym


# ─────────────────────────────────────────────────────────────────────────────
# TP1
# ─────────────────────────────────────────────────────────────────────────────

def _render_tp1(symbol: str) -> str:
    s = _display_symbol(symbol)
    return (
        f"TP1 LOCKED IN 🎯💥 — {s}\n"
        "\n"
        "First target down. Execution flawless. ⚡\n"
        "Partials banked. SL ➡️ Break Even. 🛡\n"
        "\n"
        "This trade is now bulletproof. Zero risk. Pure upside. 🚀\n"
        "\n"
        "While others hesitated, we earned. 💰"
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
        f"TP2 HIT 😎🚀 — {s}\n"
        "\n"
        "Second target secured — clean, disciplined, ruthless. 💥\n"
        "Profit banked. Risk eliminated. 🔥⛔️\n"
        "\n"
        "Free ride from here. No pressure. No noise. Just gains. 💎"
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
        f"TP3 SMASHED 🔥📈 — {s}\n"
        "\n"
        "Third target down — the plan is printing. 💎\n"
        "Patience. Conviction. Structure. That’s the edge. 💪\n"
        "\n"
        "Runner trailing. Eyes sharp. We’re not done. 👀"
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
        f"TP4 CRUSHED 🚀💥 — {s}\n"
        "\n"
        "Fourth target cleared. We’re deep in the move now. 😎\n"
        "Most traders cashed out three levels ago. Not us. 🦾\n"
        "\n"
        "Pure precision. Pure patience. Premium results. 💎"
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
        f"TP5 DESTROYED 👑🔥 — {s}\n"
        "\n"
        "Five for five — championship-level execution. 💎🚀\n"
        "The market gave. We took every. single. cent. 💰\n"
        "\n"
        "This isn’t luck. This is the system. 🧠⚡\n"
        "This is what elite looks like."
    )


TP5 = EventConfig(
    code="tp5",
    label="TP5 HIT",
    render=_render_tp5,
    is_take_profit=True,
    tp_index=5,
)


# ─────────────────────────────────────────────────────────────────────────────
# TP6 (manual-only — not tracked by price loop)
# ─────────────────────────────────────────────────────────────────────────────

def _render_tp6(symbol: str) -> str:
    s = _display_symbol(symbol)
    return (
        f"TP6 DEMOLISHED 🏆⚡ — {s}\n"
        "\n"
        "Sixth target down — rare air. 💎🔥\n"
        "No panic. No greed. Just mastery in motion. 🧠\n"
        "\n"
        "One level left. The legend isn’t finished yet. 👑"
    )


TP6 = EventConfig(
    code="tp6",
    label="TP6 HIT",
    render=_render_tp6,
    is_take_profit=True,
    tp_index=6,
    tracked=False,
)


# ─────────────────────────────────────────────────────────────────────────────
# TP7 (manual-only — not tracked by price loop)
# ─────────────────────────────────────────────────────────────────────────────

def _render_tp7(symbol: str) -> str:
    s = _display_symbol(symbol)
    return (
        f"TP7 — TOTAL DOMINATION 👑💎🚀 — {s}\n"
        "\n"
        "Seventh target. Full clear. Maximum extraction. 🏆🔥\n"
        "A legendary run, executed with surgical precision. ⚡\n"
        "\n"
        "This is the ceiling. This is the standard.\n"
        "Bow to the system. Bow to the discipline. 🙇‍♂️"
    )


TP7 = EventConfig(
    code="tp7",
    label="TP7 HIT",
    render=_render_tp7,
    is_take_profit=True,
    tp_index=7,
    tracked=False,
)


# ─────────────────────────────────────────────────────────────────────────────
# SL — Stop Loss
# ─────────────────────────────────────────────────────────────────────────────

def _render_sl(symbol: str) -> str:
    s = _display_symbol(symbol)
    return (
        f"SL HIT ⛔️📉 — {s}\n"
        "\n"
        "This one didn’t go our way.\n"
        "Discipline first. Emotion never. 🧠\n"
        "\n"
        "We take the loss clean. We learn. We reset. 🔄\n"
        "The next high-conviction setup is already loading. 💭📊\n"
        "\n"
        "No revenge. No tilt. No mistakes repeated.\n"
        "This is how professionals operate. 🦾"
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
        f"BREAK EVEN ⚖️ — {s}\n"
        "\n"
        "Trade closed at entry. Zero loss. 🛡\n"
        "TP1 profits already in the bag. ✅💰\n"
        "\n"
        "That’s the power of moving SL early — risk dies, upside stays. 🧠\n"
        "On to the next opportunity. 🚀"
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
    e.code: e for e in (TP1, TP2, TP3, TP4, TP5, TP6, TP7, SL, BE)
}


def get_event(code: str) -> EventConfig | None:
    return _REGISTRY.get((code or "").lower().strip())


def all_take_profits() -> tuple[EventConfig, ...]:
    """TPs the live tracker is allowed to watch (must have a DB column)."""
    return tuple(
        e for e in _REGISTRY.values() if e.is_take_profit and e.tracked
    )


def manual_tp_events() -> tuple[EventConfig, ...]:
    """All TP events exposed in the manual TP Sender flow (1..7)."""
    return tuple(
        sorted(
            (e for e in _REGISTRY.values() if e.is_take_profit),
            key=lambda e: e.tp_index or 0,
        )
    )


def render_event(code: str, symbol: str) -> str | None:
    cfg = get_event(code)
    if cfg is None:
        return None
    return cfg.render(symbol)
