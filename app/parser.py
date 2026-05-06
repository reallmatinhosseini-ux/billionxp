from __future__ import annotations

import re
from dataclasses import dataclass, field


_NUMBER = r"\d+(?:\.\d+)?"
_SEP = r"(?:→|\/|−|-|–|—|—|to|→)"
_ENTRY_PATTERN = re.compile(
    rf"(?:entry|zone)?\s*(?:zone|:)?\s*({_NUMBER})\s*{_SEP}\s*({_NUMBER})",
    re.IGNORECASE,
)
_TP_LABEL_PATTERN = re.compile(
    rf"TP\s*([1-5])\s*[:\.]?\s*({_NUMBER})", re.IGNORECASE
)
_TP_GENERIC_PATTERN = re.compile(
    rf"(?:take\s*profit(?:\s*[Tt][Pp]?\s*[1-5]?)?|target)\s*[:\.]?\s*({_NUMBER})",
    re.IGNORECASE,
)
_SL_PATTERN = re.compile(
    rf"(?:SL|stop\s*loss)\s*[:\.]?\s*({_NUMBER})", re.IGNORECASE
)


@dataclass
class ParsedSignal:
    direction: str
    symbol: str = "XAUUSD"
    entry_min: float = 0.0
    entry_max: float = 0.0
    sl: float = 0.0
    tp_levels: dict[int, float] = field(default_factory=dict)
    tp_order: list[int] = field(default_factory=list)


def parse_signal(text: str) -> tuple[ParsedSignal | None, list[str]]:
    """Return parsed signal or None with human-readable correction hints."""
    issues: list[str] = []

    cleaned = text.strip()
    if not cleaned:
        return None, ["Message is empty. Paste a signal with BUY/SELL, entry, SL, and TPs."]

    upper = cleaned.upper()

    direction = ""
    if re.search(r"\bBUY\b", upper):
        direction = "BUY"
    if re.search(r"\bSELL\b", upper):
        if direction == "BUY":
            return None, ["Found both BUY and SELL. Use a single direction."]
        direction = "SELL"

    if not direction:
        issues.append("Could not detect direction. Include BUY or SELL.")

    symbol = _infer_symbol(cleaned, upper)

    entry_matches = list(_ENTRY_PATTERN.finditer(cleaned))
    entry_min = entry_max = 0.0
    if not entry_matches:
        issues.append("Could not detect entry zone (e.g. 4594.4 → 4604.4 or 4594/4604).")
    else:
        a, b = entry_matches[0].group(1), entry_matches[0].group(2)
        e1, e2 = float(a), float(b)
        entry_min, entry_max = (e1, e2) if e1 <= e2 else (e2, e1)

    sl_match = _SL_PATTERN.search(cleaned)
    if not sl_match:
        issues.append("Could not detect stop loss (SL or Stop loss).")
        sl_val = 0.0
    else:
        sl_val = float(sl_match.group(1))

    tp_levels: dict[int, float] = {}

    # Explicit TP1..TP5 wins when present.
    assigned = False
    for m in _TP_LABEL_PATTERN.finditer(cleaned):
        idx = int(m.group(1))
        if 1 <= idx <= 5:
            tp_levels[idx] = float(m.group(2))
            assigned = True

    if not assigned:
        found = [_TP_GENERIC_PATTERN.search(cleaned)]
        # Find all occurrences; re.finditer
        gens = list(_TP_GENERIC_PATTERN.finditer(cleaned))
        if gens:
            for i, gm in enumerate(gens, start=1):
                if i <= 5:
                    tp_levels[i] = float(gm.group(1))

    tp_order = [i for i in range(1, 6) if i in tp_levels]
    if not tp_order:
        issues.append(
            "Could not detect take profit levels (TP1..TP5 or Take profit …)."
        )

    if issues:
        return None, issues

    return (
        ParsedSignal(
            direction=direction,
            symbol=symbol,
            entry_min=float(entry_min),
            entry_max=float(entry_max),
            sl=float(sl_val),
            tp_levels=dict(sorted(tp_levels.items())),
            tp_order=list(tp_order),
        ),
        [],
    )


def _infer_symbol(text: str, upper: str) -> str:
    if "XAUUSD" in upper or "XAU" in upper:
        return "XAUUSD"
    lower = text.lower()
    if re.search(r"\bgold\b", lower):
        return "XAUUSD"
    if re.search(r"\bxauusd\b", lower):
        return "XAUUSD"
    return "XAUUSD"
