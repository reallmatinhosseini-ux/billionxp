from __future__ import annotations

import asyncio
import sys

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.fsm.storage.memory import MemoryStorage

from app.config import load_settings
from app.database import Database
from app.handlers import admin, signals, start
from app.middlewares import AdminOnlyMiddleware, AppContext, InjectContextMiddleware
from utils.logger import get_logger

log = get_logger(__name__)


def assemble_dispatcher(settings, ctx: AppContext) -> Dispatcher:
    dp = Dispatcher(storage=MemoryStorage())
    dp.update.outer_middleware(InjectContextMiddleware(ctx))
    # Per-observer middleware: `event` is Message / CallbackQuery, not Update (no .answer on Update).
    admin_gate = AdminOnlyMiddleware(settings)
    dp.message.middleware(admin_gate)
    dp.callback_query.middleware(admin_gate)

    dp.include_router(start.router)
    dp.include_router(signals.router)
    dp.include_router(admin.router)
    return dp


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
        log.info("Polling started (%s)", db_path)
        await dp.start_polling(bot)


def main() -> None:
    try:
        asyncio.run(amain())
    except KeyboardInterrupt:
        sys.exit(0)


if __name__ == "__main__":
    main()
