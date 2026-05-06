# BillionXP Trading Signal Telegram Bot

Async Telegram bot focused on formatting gold / XAUUSD signals, routing them to VIP and/or free Telegram channels, and tracking take-profit and stop-loss levels with automatic thread replies while a signal stays active.

## Features

- **Fast paste workflow** — admins paste unstructured signal text in a private chat; the bot replies with the premium template and asks where to publish.
- **Robust parsing** — understands multiple layouts, ignores case, and normalizes `Gold` / `gold` aliases to **XAUUSD** without hallucinating missing numbers.
- **Guided publishing** — inline buttons (`VIP`, `FREE CHANNEL`, `BOTH`, `CANCEL`).
- **Channel styling** — VIP posts include `🔥 VIP EXCLUSIVE SIGNAL`; free posts optionally append your CTA.
- **Background tracking** — lightweight SQLite-backed rows with status (`active`, `closed`, `completed`).
- **Pluggable quotes** — `MockPriceProvider` ships by default so you can run end-to-end before wiring HTTP quotes (`PRICE_PROVIDER` / `PRICE_API_KEY`).

## Requirements

- Python 3.11+
- A Telegram Bot token with permission to message your channels
- The bot added as administrator (usually with “Post messages”) to each monitored channel

## Quick setup

```bash
cd /path/to/billionxp-bot
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # populate values described below
python -m app.main
```

## Environment variables

| Key | Meaning |
| --- | --- |
| `BOT_TOKEN` | Telegram `@BotFather` token |
| `ADMIN_IDS` | Comma-separated numeric Telegram user IDs |
| `VIP_CHANNEL_ID` | VIP channel `@username` or numeric ID |
| `FREE_CHANNEL_ID` | Free/public channel `@username` or numeric ID |
| `FREE_CTA_USERNAME` | Username referenced in FREE CTA (no `@`). Required for FREE/BOTH publishes |
| `CHECK_INTERVAL_SECONDS` | Tracker cadence (`>= 1`). Default `5` |
| `PRICE_PROVIDER` | `mock` today; extend `services.price_provider` for live feeds |
| `PRICE_API_KEY` | Reserved for upcoming HTTP integrations |
| `SQLITE_PATH` | Optional SQLite file path (`signals.db` default) |

## Channel setup checklist

1. Create your VIP and FREE channels if they do not already exist.
2. Add your bot as an admin with posting rights for each destination channel you plan to hit.
3. Determine each channel identifier:
   - Public channels expose `@handles` you can reuse directly (`@my_signals_channel`).
   - Private IDs look like `-1001234567890` (`getUpdates` dumps or Telegram clients can reveal them).

## Operational commands

Only user IDs enumerated in `ADMIN_IDS` reach the routers.

| Command | Description |
| --- | --- |
| `/start` | Intro + onboarding copy |
| `/help` | Full operator guide inline |
| `/active` | Lists active trackers with DB `#id` references |
| `/close <id>` | Ends tracking without posting `SL HIT` |
| `/settings` | Echoes non-secret configuration for sanity checks |

Unprefixed private messages are treated as raw signals; parse errors return an actionable bullet list.

## How tracking works

1. Every `CHECK_INTERVAL_SECONDS`, `TrackerService` loads `status = active` rows.
2. Prices are fetched per symbol via `PriceProvider.get_current_price`. The mock provider random-walks around a seed near `2300` so you can observe behavior without market data.
3. **BUY** logic: take-profit triggers when `price >= tp_level`; stop-loss triggers when `price <= sl`.
4. **SELL** logic: take-profit triggers when `price <= tp_level`; stop-loss triggers when `price >= sl`.
5. Stop-loss has priority if both would trigger in the same evaluation.
6. Only one take-profit alert fires per tick to avoid spamming multiple milestones simultaneously.
7. Duplicate alerts are prevented by persisting `tp{n}_hit` / `sl_hit` flags before Telegram sends fire.
8. When every defined take-profit is marked hit, the row transitions to `completed`. Stop-loss moves the row to `closed`.
9. Follow-up posts use `ReplyParameters` so channel members see the conversation thread under the original broadcast.

## Deployment notes

- Run under `systemd`, `pm2`, Render, Fly.io, or any simple VPS — the stack is SQLite + asyncio polling; no Redis required yet.
- Back up `signals.db` regularly if you rely on audit history (`fetch_recent_signals` hook is available via `Database` if you need exports later).
- For horizontal scaling you'd want a singleton worker or external queue — this MVP intentionally keeps one tracker loop per running process.

## Plugging in a real price provider

Subclass `services.price_provider.PriceProvider` and extend `build_price_provider` based on `PRICE_PROVIDER`.

```python
class SpotPriceFeed(PriceProvider):
    async def get_current_price(self, symbol: str) -> float:
        # aiohttp REST call guarded with timeouts here
```

Then set `PRICE_PROVIDER` to whatever key you introduce and propagate `PRICE_API_KEY`.

## Troubleshooting

- **Bot answers “restricted to admins only”** — add your Telegram user ID to `.env`.
- **`Publish failed … missing channel`** — fill `VIP_CHANNEL_ID` / `FREE_CHANNEL_ID`.
- **`FREE_CTA_USERNAME` errors** — set the username slug or publish only via VIP-only buttons.
- **No TP/SL updates** — ensure the signal row is active (`/active`). Channels must permit thread replies (`send_message(..., reply_parameters=...)` will fail silently if Telegram rejects them — check stdout logs).
