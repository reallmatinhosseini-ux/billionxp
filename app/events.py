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
        f"🎯 TP1 SECURED — {s}\n"
        "\n"
        "Partials banked. SL → Break Even.\n"
        "Risk eliminated in one move.\n"
        "\n"
        "⚡ While others hesitated, VIP got paid.\n"
        "🔥 This is the edge."
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
        f"🎯 TP2 SECURED — {s}\n"
        "\n"
        "Profit stacked. Trade fully risk-free.\n"
        "The runner works for us now.\n"
        "\n"
        "⚡ Non-members are still analyzing.\n"
        "🔥 We’re already paid."
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
        f"🎯 TP3 SECURED — {s}\n"
        "\n"
        "Three clean prints. The plan is printing.\n"
        "Runner trailing. We let it work.\n"
        "\n"
        "⚡ You can’t fake this kind of consistency.\n"
        "🔥 Conviction. Patience. Execution."
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
        f"🎯 TP4 SECURED — {s}\n"
        "\n"
        "Deep in the move. Late entries chasing.\n"
        "We’re already sitting on premium profit.\n"
        "\n"
        "⚡ Inside the room, this is the standard.\n"
        "🔥 The system never tilts."
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
        f"🎯 TP5 SECURED — {s}\n"
        "\n"
        "Five clean targets. Surgical precision.\n"
        "Every cent the market offered — claimed.\n"
        "\n"
        "⚡ This is what VIP pays for.\n"
        "🔥 No noise. Just results."
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
        f"🎯 TP6 SECURED — {s}\n"
        "\n"
        "Rare air. Six clean prints.\n"
        "Most traders never see this kind of run.\n"
        "\n"
        "⚡ The system. The discipline. The edge.\n"
        "🔥 We don’t celebrate — we execute."
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
        f"🏆 TP7 — FULL CLEAR — {s}\n"
        "\n"
        "Seven targets. Maximum extraction.\n"
        "The kind of run other channels brag about for weeks.\n"
        "\n"
        "⚡ For VIP — this is the standard.\n"
        "🔥 Nothing less."
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
        f"🛡 SL HIT — {s}\n"
        "\n"
        "This one didn’t pay. We accept it clean.\n"
        "Capital protected. Discipline intact.\n"
        "\n"
        "⚡ Losses are the cost of staying in the game.\n"
        "🔥 No revenge. No tilt. Next setup loading."
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
        f"🛡 BREAK EVEN — {s}\n"
        "\n"
        "Trade closed at entry. Zero loss.\n"
        "TP1 profits already locked.\n"
        "\n"
        "⚡ Early SL management = bulletproof trading.\n"
        "🔥 Risk dies. Upside stays."
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
