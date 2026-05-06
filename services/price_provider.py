from __future__ import annotations

import asyncio
import random
from abc import ABC, abstractmethod

from utils.logger import get_logger

log = get_logger(__name__)


class PriceProvider(ABC):
    @abstractmethod
    async def get_current_price(self, symbol: str) -> float:
        """Return last price for the symbol (async for real HTTP later)."""


class MockPriceProvider(PriceProvider):
    """Deterministic-enough random walk around a fixed anchor for MVP."""

    def __init__(self, seed_anchor: float = 2300.0) -> None:
        self._anchor = float(seed_anchor)
        self._last: dict[str, float] = {}

    async def get_current_price(self, symbol: str) -> float:
        sym = symbol.upper()
        prev = self._last.get(sym, self._anchor + random.uniform(-5, 5))
        step = random.uniform(-1.2, 1.2)
        nxt = max(0.01, prev + step)
        self._last[sym] = nxt
        await asyncio.sleep(0)
        return nxt


def build_price_provider(kind: str, *, api_key: str) -> PriceProvider:
    k = (kind or "mock").lower()
    if k == "mock":
        return MockPriceProvider()
    log.warning("Unknown PRICE_PROVIDER=%s; falling back to mock", kind)
    return MockPriceProvider()
