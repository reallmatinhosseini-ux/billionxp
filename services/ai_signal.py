from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import Any

from openai import AsyncOpenAI

from app.parser import ParsedSignal


@dataclass(frozen=True)
class AiParsedSignal:
    signal: ParsedSignal
    market_insight: str
    risk_management: str


_JSON_CLEANUP = re.compile(r"^```(?:json)?\s*|\s*```$", re.IGNORECASE)


def _clean_json(s: str) -> str:
    return _JSON_CLEANUP.sub("", (s or "").strip()).strip()


def _to_float(val: Any) -> float | None:
    if val is None:
        return None
    if isinstance(val, (int, float)):
        return float(val)
    if isinstance(val, str):
        t = val.strip().replace(",", "")
        if not t:
            return None
        try:
            return float(t)
        except ValueError:
            return None
    return None


def _norm_direction(raw: Any) -> str | None:
    if not isinstance(raw, str):
        return None
    u = raw.strip().upper()
    if "BUY" in u:
        return "BUY"
    if "SELL" in u:
        return "SELL"
    return None


def _norm_symbol(raw: Any) -> str:
    if not isinstance(raw, str):
        return "XAUUSD"
    u = raw.strip().upper().replace("/", "").replace(" ", "")
    if u in {"GOLD", "XAU", "XAUUSD"}:
        return "XAUUSD"
    # Keep forex/crypto pairs like EURUSD, BTCUSDT, etc.
    return u or "XAUUSD"


async def parse_signal_via_openai(
    *,
    api_key: str,
    model: str,
    text: str,
) -> tuple[AiParsedSignal | None, list[str]]:
    """
    Use OpenAI to extract structured signal fields from messy text.
    Returns (AiParsedSignal|None, errors). Does not hallucinate numbers:
    if required numeric fields are missing/unreliable, returns errors.
    """
    cleaned = (text or "").strip()
    if not cleaned:
        return None, ["Message is empty."]
    if not api_key.strip():
        return None, ["OPENAI_API_KEY is not configured."]

    client = AsyncOpenAI(api_key=api_key)

    schema_hint = {
        "symbol": "XAUUSD",
        "direction": "BUY | SELL",
        "order_type": "LIMIT | MARKET | STOP | ''",
        "entry_min": 0.0,
        "entry_max": 0.0,
        "stop_loss": 0.0,
        "take_profits": [0.0],
        "market_insight": "",
        "risk_management": "",
    }

    system = (
        "You are an expert trading-signal parser.\n"
        "Task: extract fields from a raw signal message.\n"
        "Rules:\n"
        "- Output MUST be valid JSON only.\n"
        "- Do NOT invent prices. If a number is not present, use null for that field.\n"
        "- If only one entry price exists, set entry_min=entry_max.\n"
        "- take_profits: array of numbers in order (max 5). If none, use [].\n"
        "- symbol: normalize GOLD/XAU -> XAUUSD; else keep detected pair.\n"
        "- direction must be BUY or SELL if present.\n"
        "- market_insight: short professional note if present; otherwise empty string.\n"
        "- risk_management: if not present, return an empty string.\n"
        f"Return JSON matching this shape: {json.dumps(schema_hint)}"
    )

    user = f"RAW MESSAGE:\n{cleaned}"

    try:
        resp = await client.chat.completions.create(
            model=model,
            temperature=0.1,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
        )
    except Exception as exc:
        return None, [f"OpenAI request failed: {exc!s}"]

    content = ""
    try:
        content = resp.choices[0].message.content or ""
    except Exception:
        content = ""

    payload_raw = _clean_json(content)
    try:
        data = json.loads(payload_raw)
    except Exception:
        return None, ["AI returned non-JSON output. Try again or paste with clearer numbers."]

    direction = _norm_direction(data.get("direction"))
    symbol = _norm_symbol(data.get("symbol"))
    entry_min = _to_float(data.get("entry_min"))
    entry_max = _to_float(data.get("entry_max"))
    sl = _to_float(data.get("stop_loss"))

    tps_raw = data.get("take_profits", [])
    tp_list: list[float] = []
    if isinstance(tps_raw, list):
        for x in tps_raw[:5]:
            f = _to_float(x)
            if f is not None:
                tp_list.append(f)

    issues: list[str] = []
    if not direction:
        issues.append("Could not detect direction (BUY/SELL).")
    if entry_min is None or entry_max is None:
        issues.append("Could not detect entry zone (two prices or one entry).")
    if sl is None:
        issues.append("Could not detect stop loss.")
    if not tp_list:
        issues.append("Could not detect take profit levels.")

    if issues:
        return None, issues

    e1, e2 = float(entry_min), float(entry_max)
    e_min, e_max = (e1, e2) if e1 <= e2 else (e2, e1)

    tp_levels = {i + 1: v for i, v in enumerate(tp_list)}
    tp_order = list(tp_levels.keys())

    market_insight = str(data.get("market_insight") or "").strip()
    risk_management = str(data.get("risk_management") or "").strip()

    return (
        AiParsedSignal(
            signal=ParsedSignal(
                direction=direction,
                symbol=symbol,
                entry_min=e_min,
                entry_max=e_max,
                sl=float(sl),
                tp_levels=tp_levels,
                tp_order=tp_order,
            ),
            market_insight=market_insight,
            risk_management=risk_management,
        ),
        [],
    )

