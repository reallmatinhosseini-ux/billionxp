from __future__ import annotations

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup


def publish_destination_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="VIP", callback_data="pub:vip"),
                InlineKeyboardButton(text="FREE CHANNEL", callback_data="pub:free"),
            ],
            [
                InlineKeyboardButton(text="BOTH", callback_data="pub:both"),
                InlineKeyboardButton(text="CANCEL", callback_data="pub:cancel"),
            ],
        ]
    )


def followup_approval_keyboard(alert_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="SEND", callback_data=f"alert:send:{alert_id}"),
                InlineKeyboardButton(text="CANCEL", callback_data=f"alert:cancel:{alert_id}"),
            ]
        ]
    )
