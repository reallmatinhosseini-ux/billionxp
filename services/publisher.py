from __future__ import annotations

from typing import TYPE_CHECKING

from aiogram import Bot
from aiogram.types import Message

from app.formatter import add_free_cta, add_vip_header, format_signal_elite
from app.parser import ParsedSignal

if TYPE_CHECKING:
    from app.config import Settings


async def send_vip_signal(
    bot: Bot,
    settings: Settings,
    sig: ParsedSignal,
    *,
    order_type: str = "",
) -> Message:
    body = format_signal_elite(
        sig,
        order_type=order_type,
    )
    text = add_vip_header(body)
    return await bot.send_message(chat_id=settings.vip_channel_id, text=text)


async def send_free_signal(
    bot: Bot,
    settings: Settings,
    sig: ParsedSignal,
    *,
    order_type: str = "",
) -> Message:
    body = format_signal_elite(
        sig,
        order_type=order_type,
    )
    uname = settings.free_cta_username.strip().lstrip("@")
    text = body if not uname else add_free_cta(body, uname)
    return await bot.send_message(chat_id=settings.free_channel_id, text=text)
