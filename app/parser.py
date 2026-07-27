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
_SYMBOL_PATTERN = re.compile(
    r"\b([A-Z]{3,10})\s*[/\-]?\s*([A-Z]{3,10})\b"
)
_SINGLE_SYMBOL_PATTERN = re.compile(r"\b[A-Z]{3,12}\b")
_DIRECTION_PATTERN = re.compile(r"\b(BUY|SELL|LONG|SHORT)\b", re.IGNORECASE)
_ORDER_TYPE_PATTERN = re.compile(r"\b(LIMIT|MARKET|STOP)\b", re.IGNORECASE)
_ENTRY_KEYWORDS = re.compile(r"\b(entry|buy\s*at|sell\s*at|zone|open)\b", re.IGNORECASE)
_TP_KEYWORDS = re.compile(r"\b(tp\d?|take\s*profit|targets?|target)\b", re.IGNORECASE)
_SL_KEYWORDS = re.compile(r"\b(sl|stop\s*loss|stops?)\b", re.IGNORECASE)
_NUM_PATTERN = re.compile(_NUMBER)


def _looks_like_numbering(smaller: float, larger: float) -> bool:
    """
    True when `smaller` next to `larger` is almost certainly a list index
    rather than a real price — e.g. "Entry: 1 – 4089" or "1. 4089" where the
    leading "1" is enumeration, not a bound of the entry zone.
    """
    if smaller <= 0 or smaller >= larger:
        return False
    # A 100×+ magnitude gap means one side is either garbage or an index.
    if larger / smaller >= 100:
        return True
    # Small single-digit integer next to a plausible price line.
    if smaller == int(smaller) and 1 <= smaller <= 9 and larger >= 50:
        return True
    return False


def _normalize_entry_pair(a: float, b: float) -> tuple[float, float]:
    """Order the pair and collapse an obvious numbering prefix to a single value."""
    lo, hi = (a, b) if a <= b else (b, a)
    if _looks_like_numbering(lo, hi):
        return (hi, hi)
    return (lo, hi)


def _strip_numbering_prefix(nums: list[float]) -> list[float]:
    """Drop a leading list-index number from a line like `1. 4089` / `2) 4095`."""
    if len(nums) >= 2 and _looks_like_numbering(nums[0], max(nums[1:])):
        return nums[1:]
    return nums


@dataclass
class ParsedSignal:
    direction: str
    symbol: str = "XAUUSD"
    entry_min: float = 0.0
    entry_max: float = 0.0
    sl: float = 0.0
    tp_levels: dict[int, float] = field(default_factory=dict)
    tp_order: list[int] = field(default_factory=list)


@dataclass(frozen=True)
class ParseExtras:
    order_type: str = ""
    notes: str = ""


def parse_signal(text: str) -> tuple[ParsedSignal | None, list[str]]:
    """Legacy strict parser (kept for compatibility)."""
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
        entry_min, entry_max = _normalize_entry_pair(float(a), float(b))

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


def parse_signal_any(text: str) -> tuple[ParsedSignal | None, ParseExtras, list[str]]:
    """
    Flexible best-effort parser.
    Tries to extract: symbol, direction, order type, entry (single or range), SL, and TP levels
    from messy/unstructured messages.
    """
    cleaned = (text or "").strip()
    if not cleaned:
        return None, ParseExtras(), ["Message is empty."]

    upper = cleaned.upper()

    direction = _infer_direction(upper)
    symbol = _infer_symbol_flexible(cleaned, upper)
    order_type = _infer_order_type(upper)

    sl = _infer_sl(cleaned)
    tp_levels = _infer_tps(cleaned)
    entry_min, entry_max = _infer_entry(cleaned, sl=sl, tp_levels=tp_levels)

    issues: list[str] = []
    if not direction:
        issues.append("Could not detect direction (BUY/SELL).")
    if entry_min is None or entry_max is None:
        issues.append("Could not detect entry price/zone.")
    if sl is None:
        issues.append("Could not detect stop loss.")
    if not tp_levels:
        issues.append("Could not detect take profit levels.")

    if issues:
        return None, ParseExtras(order_type=order_type, notes=_infer_notes(cleaned)), issues

    e1, e2 = float(entry_min), float(entry_max)
    e_min, e_max = (e1, e2) if e1 <= e2 else (e2, e1)

    tp_order = sorted(tp_levels.keys())
    sig = ParsedSignal(
        direction=direction,
        symbol=symbol,
        entry_min=e_min,
        entry_max=e_max,
        sl=float(sl),
        tp_levels=dict(sorted(tp_levels.items())),
        tp_order=tp_order,
    )
    extras = ParseExtras(order_type=order_type, notes=_infer_notes(cleaned))
    return sig, extras, []


def _infer_symbol(text: str, upper: str) -> str:
    if "XAUUSD" in upper or "XAU" in upper:
        return "XAUUSD"
    lower = text.lower()
    if re.search(r"\bgold\b", lower):
        return "XAUUSD"
    if re.search(r"\bxauusd\b", lower):
        return "XAUUSD"
    return "XAUUSD"


def _infer_direction(upper: str) -> str:
    m = _DIRECTION_PATTERN.search(upper)
    if not m:
        return ""
    raw = m.group(1).upper()
    if raw in {"LONG"}:
        return "BUY"
    if raw in {"SHORT"}:
        return "SELL"
    return raw if raw in {"BUY", "SELL"} else ""


def _infer_order_type(upper: str) -> str:
    # Look for explicit "BUY LIMIT" / "SELL LIMIT" etc.
    m = re.search(r"\b(BUY|SELL)\s+(LIMIT|MARKET|STOP)\b", upper)
    if m:
        return m.group(2).upper()
    m2 = _ORDER_TYPE_PATTERN.search(upper)
    return m2.group(1).upper() if m2 else ""


def _infer_symbol_flexible(text: str, upper: str) -> str:
    if "XAUUSD" in upper or re.search(r"\bXAU\b", upper):
        return "XAUUSD"
    if re.search(r"\bGOLD\b", upper):
        return "XAUUSD"

    # Pair forms: EURUSD, BTCUSDT, EUR/USD, BTC-USDT, etc.
    m = _SYMBOL_PATTERN.search(upper)
    if m:
        a, b = m.group(1), m.group(2)
        pair = f"{a}{b}"
        # Avoid common English words accidentally captured
        if pair not in {"TAKEPROFIT", "STOPLOSS"}:
            return pair

    # Single tokens like BTCUSDT, ETHUSD, US30, NAS100.
    tokens = _SINGLE_SYMBOL_PATTERN.findall(upper)
    blacklist = {
        "BUY", "SELL", "LONG", "SHORT", "ENTRY", "ZONE", "SL", "TP", "TPS", "STOP", "LOSS",
        "LIMIT", "MARKET", "TARGET", "TARGETS", "TAKE", "PROFIT",
    }
    for t in tokens:
        if t in blacklist:
            continue
        if 3 <= len(t) <= 12 and any(ch.isdigit() for ch in t) or len(t) in {6, 7, 8}:
            return t
        if len(t) in {6, 7, 8, 9, 10} and t.isalpha():
            return t

    return _infer_symbol(text, upper)


def _infer_sl(text: str) -> float | None:
    m = _SL_PATTERN.search(text)
    if m:
        return float(m.group(1))

    # Line-based heuristic: "sl 2345" or "stop 2345"
    for line in text.splitlines():
        if not _SL_KEYWORDS.search(line):
            continue
        nums = [float(x) for x in _NUM_PATTERN.findall(line)]
        if nums:
            return nums[0]
    return None


def _infer_tps(text: str) -> dict[int, float]:
    levels: dict[int, float] = {}
    for m in _TP_LABEL_PATTERN.finditer(text):
        idx = int(m.group(1))
        if 1 <= idx <= 5:
            levels[idx] = float(m.group(2))

    if levels:
        return levels

    # If no labeled TPs, collect numbers from lines that look like TP/target lines.
    found: list[float] = []
    for line in text.splitlines():
        if not _TP_KEYWORDS.search(line):
            continue
        nums = [float(x) for x in _NUM_PATTERN.findall(line)]
        for n in nums:
            found.append(n)

    # If still none, try generic "target: 1234" matches across whole text.
    if not found:
        gens = list(_TP_GENERIC_PATTERN.finditer(text))
        for gm in gens:
            found.append(float(gm.group(1)))

    for i, v in enumerate(found[:5], start=1):
        levels[i] = float(v)
    return levels


def _infer_entry(
    text: str,
    *,
    sl: float | None,
    tp_levels: dict[int, float],
) -> tuple[float | None, float | None]:
    # Prefer explicit entry range patterns (with separators).
    m = _ENTRY_PATTERN.search(text)
    if m:
        return _normalize_entry_pair(float(m.group(1)), float(m.group(2)))

    # Look for entry-ish lines and pull 1-2 numbers.
    for line in text.splitlines():
        if not _ENTRY_KEYWORDS.search(line):
            continue
        nums = [float(x) for x in _NUM_PATTERN.findall(line)]
        nums = _strip_numbering_prefix(nums)
        if len(nums) >= 2:
            return _normalize_entry_pair(nums[0], nums[1])
        if len(nums) == 1:
            return nums[0], nums[0]

    # Fallback: infer from overall number set by excluding SL and TPs.
    all_nums = [float(x) for x in _NUM_PATTERN.findall(text)]
    exclude: set[float] = set()
    if sl is not None:
        exclude.add(float(sl))
    for v in tp_levels.values():
        exclude.add(float(v))
    candidates = [n for n in all_nums if n not in exclude]
    candidates = _strip_numbering_prefix(candidates)

    if len(candidates) >= 2:
        return _normalize_entry_pair(candidates[0], candidates[1])
    if len(candidates) == 1:
        return candidates[0], candidates[0]
    return None, None


def _infer_notes(text: str) -> str:
    # Keep a short note from lines that aren't obviously entry/sl/tp/symbol/direction.
    notes: list[str] = []
    for raw in text.splitlines():
        line = raw.strip()
        if not line:
            continue
        u = line.upper()
        if _DIRECTION_PATTERN.search(u) or _ORDER_TYPE_PATTERN.search(u):
            continue
        if _ENTRY_KEYWORDS.search(u) or _TP_KEYWORDS.search(u) or _SL_KEYWORDS.search(u):
            continue
        if _NUM_PATTERN.search(u):
            continue
        if len(line) < 6:
            continue
        notes.append(line)
    out = " ".join(notes).strip()
    return out[:240]
