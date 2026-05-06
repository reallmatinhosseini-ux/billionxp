from __future__ import annotations

from dataclasses import dataclass

from dotenv import load_dotenv
import os

load_dotenv()


def _csv_ids(raw: str) -> frozenset[int]:
    out: set[int] = set()
    for part in (raw or "").split(","):
        part = part.strip()
        if not part:
            continue
        try:
            out.add(int(part))
        except ValueError:
            continue
    return frozenset(out)


@dataclass(frozen=True)
class Settings:
    bot_token: str
    admin_ids: frozenset[int]
    vip_channel_id: str
    free_channel_id: str
    free_cta_username: str
    check_interval_seconds: float
    price_provider: str
    price_api_key: str
    sqlite_path: str = "signals.db"


def load_settings() -> Settings:
    token = os.getenv("BOT_TOKEN", "").strip()
    interval_raw = os.getenv("CHECK_INTERVAL_SECONDS", "5")
    try:
        interval = float(interval_raw)
    except ValueError:
        interval = 5.0
    if interval < 1:
        interval = 1.0

    return Settings(
        bot_token=token,
        admin_ids=_csv_ids(os.getenv("ADMIN_IDS", "")),
        vip_channel_id=(os.getenv("VIP_CHANNEL_ID", "") or "").strip(),
        free_channel_id=(os.getenv("FREE_CHANNEL_ID", "") or "").strip(),
        free_cta_username=(os.getenv("FREE_CTA_USERNAME", "") or "").strip(),
        check_interval_seconds=interval,
        price_provider=(os.getenv("PRICE_PROVIDER", "mock") or "mock").strip().lower(),
        price_api_key=(os.getenv("PRICE_API_KEY", "") or "").strip(),
        sqlite_path=(os.getenv("SQLITE_PATH", "signals.db") or "signals.db").strip(),
    )
