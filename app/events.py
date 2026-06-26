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
    return (
        "TP1 HIT 😎\n"
        "\n"
        "Initial target hit ✔\n"
        "Price reacted clean to the setup, structure still valid and momentum aligned.\n"
        "\n"
        "Nothing to do here except stay patient. Don’t rush exits — first move is just confirmation, not the main profit phase."
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
        "\n"
        "Second target hit ✔✔\n"
        "Continuation is strong, no structural damage.\n"
        "\n"
        "Risk is now removed (breakeven secured ⛔️), so the position is effectively risk-free.\n"
        "\n"
        "Let it run. Interfering here is where most traders destroy good trades."
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
        "\n"
        "Trend is fully confirmed ✔✔✔\n"
        "Market is still respecting direction with no real rejection.\n"
        "\n"
        "Just hold. No overthinking, no early exit. Let the move develop properly."
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
        "\n"
        "Expansion is in progress ✔✔✔✔\n"
        "Price is accelerating and liquidity is being delivered.\n"
        "\n"
        "Stay disciplined — don’t chase, don’t adjust emotionally. You’re already positioned."
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
        "\n"
        "High profit zone ✔\n"
        "Most traders are already out by now.\n"
        "\n"
        "This is where discipline matters more than profit itself. Stick to plan."
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
    return (
        "TP6 HIT 🚀\n"
        "\n"
        "Parabolic phase active\n"
        "Volatility increases and emotions start to interfere.\n"
        "\n"
        "Only structure matters here. Not feelings, not noise."
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
    return (
        "TP7 HIT 💰\n"
        "\n"
        "Final target hit ✔\n"
        "Full move completed from start to finish.\n"
        "\n"
        "Close according to plan, log it, and move on. Execution is the real edge."
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
        "━━━━━━━━━━━━━━━\n"
        "This one didn’t pay. We accept it clean.\n"
        "Capital intact. Discipline untouched. ⛔\n"
        "\n"
        "Losses aren’t failure — they’re tuition.\n"
        "The game rewards survival, not bravado.\n"
        "\n"
        "⚡ No revenge. No tilt. No chase.\n"
        "🔥 The next high-conviction setup is loading."
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
        "━━━━━━━━━━━━━━━\n"
        "Trade closed at entry. Zero damage.\n"
        "TP1 profits already locked. ✅\n"
        "\n"
        "This is why we move SL early:\n"
        "Risk dies. Upside stays. Capital compounds. 💎\n"
        "\n"
        "⚡ Smart management beats lucky predictions.\n"
        "🔥 Onto the next print."
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
