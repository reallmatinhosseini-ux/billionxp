"""
Event registry for trade lifecycle notifications.

Each event (TP1..TP5, SL, BE, FULL TP) lives in its own independent
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


# ─────────────────────────────────────────────────────────────────────────────
# TP1
# ─────────────────────────────────────────────────────────────────────────────

def _render_tp1(symbol: str) -> str:
    return (
        "TP1 HIT 😎\n"
        "Target 1 secured ✔\n"
        "First reaction confirmed. Structure intact.\n"
        "No exit. Just validation."
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
    return (
        "TP2 HIT 🚀\n"
        "Momentum continues ✔\n"
        "Risk off (BE locked ⛔️)\n"
        "Let it breathe."
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
    return (
        "TP3 HIT 🔥\n"
        "Trend confirmed ✔\n"
        "No weakness in structure.\n"
        "Hold steady."
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
    return (
        "TP4 HIT 💥\n"
        "Expansion phase ✔\n"
        "Price accelerating.\n"
        "No emotional moves."
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
    return (
        "TP5 HIT ⚡\n"
        "High profit zone ✔\n"
        "Most are out already.\n"
        "You stay disciplined."
    )


TP5 = EventConfig(
    code="tp5",
    label="TP5 HIT",
    render=_render_tp5,
    is_take_profit=True,
    tp_index=5,
)


# ─────────────────────────────────────────────────────────────────────────────
# FULL TP — every defined target cleared (auto-fires after final TP)
# ─────────────────────────────────────────────────────────────────────────────

def _render_full_tp(symbol: str) -> str:
    return (
        "FULL TP HIT 🏁\n"
        "All targets cleared ✔✔✔\n"
        "Perfect execution from start to finish.\n"
        "No hesitation, no interference — just pure follow-through.\n"
        "That’s the edge."
    )


FULL_TP = EventConfig(
    code="full_tp",
    label="FULL TP HIT",
    render=_render_full_tp,
)


# ─────────────────────────────────────────────────────────────────────────────
# SL — Stop Loss
# ─────────────────────────────────────────────────────────────────────────────

def _render_sl(symbol: str) -> str:
    return (
        "SL HIT ⛔️\n"
        "Trade closed at stop.\n"
        "Capital protected. Discipline intact.\n"
        "No revenge. Next setup loading."
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
    return (
        "BE CLOSED 🛡\n"
        "Trade closed at entry. Zero loss.\n"
        "TP1 profits already locked.\n"
        "Onto the next."
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
    e.code: e for e in (TP1, TP2, TP3, TP4, TP5, FULL_TP, SL, BE)
}


def get_event(code: str) -> EventConfig | None:
    return _REGISTRY.get((code or "").lower().strip())


def all_take_profits() -> tuple[EventConfig, ...]:
    """TPs the live tracker watches. Every TP here has a matching DB column."""
    return tuple(e for e in _REGISTRY.values() if e.is_take_profit)


def render_event(code: str, symbol: str) -> str | None:
    cfg = get_event(code)
    if cfg is None:
        return None
    return cfg.render(symbol)
