from __future__ import annotations

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from app.events import manual_tp_events


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


def main_menu_keyboard() -> InlineKeyboardMarkup:
    """Top-level menu shown by /menu and /start."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="📤 TP Sender", callback_data="menu:tpsender")],
            [InlineKeyboardButton(text="📋 Active Signals", callback_data="menu:active")],
            [InlineKeyboardButton(text="📜 Recent History", callback_data="menu:history")],
            [InlineKeyboardButton(text="⚙️ Settings", callback_data="menu:settings")],
        ]
    )


def tp_sender_channel_keyboard() -> InlineKeyboardMarkup:
    """Step 1 of TP Sender: pick the destination."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="🏆 VIP Channel", callback_data="tps:ch:vip"),
                InlineKeyboardButton(text="🌐 Public Channel", callback_data="tps:ch:free"),
            ],
            [
                InlineKeyboardButton(text="📣 Both", callback_data="tps:ch:both"),
                InlineKeyboardButton(text="❌ Cancel", callback_data="tps:ch:cancel"),
            ],
        ]
    )


def tp_sender_level_keyboard() -> InlineKeyboardMarkup:
    """Step 2 of TP Sender: pick TP1..TP7 or SL."""
    tp_buttons = [
        InlineKeyboardButton(
            text=f"TP{e.tp_index}",
            callback_data=f"tps:lvl:{e.code}",
        )
        for e in manual_tp_events()
    ]
    # Grid TPs 4 per row.
    rows: list[list[InlineKeyboardButton]] = []
    for i in range(0, len(tp_buttons), 4):
        rows.append(tp_buttons[i : i + 4])
    rows.append([InlineKeyboardButton(text="⛔️ SL HIT", callback_data="tps:lvl:sl")])
    rows.append([InlineKeyboardButton(text="❌ Cancel", callback_data="tps:lvl:cancel")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def tp_sender_confirm_keyboard() -> InlineKeyboardMarkup:
    """Step 3 of TP Sender: confirm publish."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="✅ Send", callback_data="tps:confirm:send"),
                InlineKeyboardButton(text="❌ Cancel", callback_data="tps:confirm:cancel"),
            ]
        ]
    )
