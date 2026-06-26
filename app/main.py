from __future__ import annotations

import asyncio
import sys

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import BotCommand

from app.config import load_settings
from app.database import Database
from app.handlers import admin, followups, signals, start, tp_sender
from app.middlewares import AdminOnlyMiddleware, AppContext, InjectContextMiddleware
from services.price_provider import build_price_provider
from services.tracker import TrackerService
from utils.logger import get_logger

log = get_logger(__name__)


def assemble_dispatcher(settings, ctx: AppContext) -> Dispatcher:
    dp = Dispatcher(storage=MemoryStorage())
    dp.update.outer_middleware(InjectContextMiddleware(ctx))
    # Per-observer middleware: `event` is Message / CallbackQuery, not Update.
    admin_gate = AdminOnlyMiddleware(settings)
    dp.message.middleware(admin_gate)
    dp.callback_query.middleware(admin_gate)

    dp.include_router(start.router)
    dp.include_router(tp_sender.router)
    dp.include_router(signals.router)
    dp.include_router(followups.router)
    dp.include_router(admin.router)
    return dp


_BOT_COMMANDS: tuple[BotCommand, ...] = (
    BotCommand(command="menu", description="Open the main menu"),
    BotCommand(command="tp", description="TP Sender (TP1–TP7 / SL HIT)"),
    BotCommand(command="active", description="List active tracked signals"),
    BotCommand(command="history", description="Recent signals"),
    BotCommand(command="settings", description="Show bot configuration"),
    BotCommand(command="help", description="Help / usage"),
)


async def _register_bot_commands(bot: Bot) -> None:
    try:
        await bot.set_my_commands(list(_BOT_COMMANDS))
    except Exception:
        log.exception("set_my_commands failed; menu will fall back to defaults")


async def amain() -> None:
    settings = load_settings()
    if not settings.bot_token:
        log.error("BOT_TOKEN missing in environment")
        raise SystemExit(1)
    if not settings.admin_ids:
        log.warning("ADMIN_IDS empty — non-/start,/ping handlers will alert users")

    db_path = settings.sqlite_path
    db = Database(db_path)
    await db.init_schema()

    ctx = AppContext(settings=settings, db=db)
    dp = assemble_dispatcher(settings, ctx)

    async with Bot(settings.bot_token, default=DefaultBotProperties()) as bot:
        price_provider = build_price_provider(
            settings.price_provider, api_key=settings.price_api_key
        )
        tracker = TrackerService(
            settings=settings, db=db, bot=bot, price_provider=price_provider
        )

        await _register_bot_commands(bot)
        log.info("Polling started (%s)", db_path)
        tracker_task = asyncio.create_task(tracker.loop_forever(), name="tracker")
        try:
            await dp.start_polling(bot)
        finally:
            tracker_task.cancel()
            try:
                await tracker_task
            except (asyncio.CancelledError, Exception):
                pass


def main() -> None:
    try:
        asyncio.run(amain())
    except KeyboardInterrupt:
        sys.exit(0)


if __name__ == "__main__":
    main()
