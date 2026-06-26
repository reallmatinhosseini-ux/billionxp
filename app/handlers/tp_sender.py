"""
TP Sender — manual broadcast of TP1..TP7 / SL HIT messages to a channel.

Flow:
    /tp                      → ask channel (VIP / Public / Both)
    tps:ch:<vip|free|both>   → ask level (TP1..TP7 + SL)
    tps:lvl:<code>           → preview message + Send/Cancel
    tps:confirm:send         → post to chosen channel(s)

Each step persists state via FSM so multiple admins can use it in parallel
without colliding. All messaging copy lives in `app.events` — this handler
only routes.
"""

from __future__ import annotations

from aiogram import Bot, F, Router
from aiogram.enums import ChatType
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, Message

from app.events import EventConfig, get_event
from app.keyboards import (
    tp_sender_channel_keyboard,
    tp_sender_confirm_keyboard,
    tp_sender_level_keyboard,
)
from app.middlewares import AppContext
from app.replies import message_answer_logged
from utils.logger import get_logger

log = get_logger(__name__)

router = Router(name="tp_sender")

_DM = F.chat.type == ChatType.PRIVATE
_DM_CALLBACK = F.message.chat.type == ChatType.PRIVATE


_DEFAULT_SYMBOL = "XAUUSD"


class TPSenderStates(StatesGroup):
    choosing_channel = State()
    choosing_level = State()
    confirming = State()


# ─────────────────────────────────────────────────────────────────────────────
# Entry — /tp or main-menu button
# ─────────────────────────────────────────────────────────────────────────────


async def _start_flow(state: FSMContext, send_text) -> None:
    await state.clear()
    await state.set_state(TPSenderStates.choosing_channel)
    await send_text(
        "📤 *TP Sender*\n\nWhich channel do you want to send the TP notification to?",
        reply_markup=tp_sender_channel_keyboard(),
    )


@router.message(Command("tp"), _DM)
async def cmd_tp(message: Message, state: FSMContext) -> None:
    async def send(text: str, **kw) -> None:
        await message_answer_logged(message, text, **kw)

    await _start_flow(state, send)


@router.callback_query(F.data == "menu:tpsender", _DM_CALLBACK)
async def menu_open_tp_sender(callback: CallbackQuery, state: FSMContext) -> None:
    if not callback.message:
        await callback.answer()
        return
    msg = callback.message  # type: ignore[assignment]

    async def send(text: str, **kw) -> None:
        if isinstance(msg, Message):
            await message_answer_logged(msg, text, **kw)

    try:
        await callback.answer()
    except Exception:
        log.exception("callback.answer (menu:tpsender)")
    await _start_flow(state, send)


# ─────────────────────────────────────────────────────────────────────────────
# Step 1: channel
# ─────────────────────────────────────────────────────────────────────────────


_CHANNEL_LABELS = {
    "vip": "🏆 VIP Channel",
    "free": "🌐 Public Channel",
    "both": "📣 VIP + Public",
}


@router.callback_query(F.data.startswith("tps:ch:"), _DM_CALLBACK)
async def on_pick_channel(
    callback: CallbackQuery,
    state: FSMContext,
) -> None:
    action = (callback.data or "").split(":", 2)[2]
    reply = callback.message if isinstance(callback.message, Message) else None

    if action == "cancel":
        await state.clear()
        try:
            await callback.answer("Cancelled.")
        except Exception:
            log.exception("callback.answer (tps cancel)")
        if reply:
            try:
                await reply.edit_reply_markup(reply_markup=None)
            except Exception:
                pass
            await message_answer_logged(reply, "TP Sender cancelled.")
        return

    if action not in _CHANNEL_LABELS:
        await callback.answer("Bad choice.", show_alert=True)
        return

    await state.update_data(channel=action)
    await state.set_state(TPSenderStates.choosing_level)
    try:
        await callback.answer()
    except Exception:
        log.exception("callback.answer (tps:ch)")
    if reply:
        try:
            await reply.edit_reply_markup(reply_markup=None)
        except Exception:
            pass
        await message_answer_logged(
            reply,
            f"Destination: {_CHANNEL_LABELS[action]}\n\nWhich TP level has been hit?",
            reply_markup=tp_sender_level_keyboard(),
        )


# ─────────────────────────────────────────────────────────────────────────────
# Step 2: level (TP1..TP7 or SL)
# ─────────────────────────────────────────────────────────────────────────────


@router.callback_query(F.data.startswith("tps:lvl:"), _DM_CALLBACK)
async def on_pick_level(
    callback: CallbackQuery,
    state: FSMContext,
    app_ctx: AppContext,
) -> None:
    code = (callback.data or "").split(":", 2)[2]
    reply = callback.message if isinstance(callback.message, Message) else None

    if code == "cancel":
        await state.clear()
        try:
            await callback.answer("Cancelled.")
        except Exception:
            log.exception("callback.answer (tps lvl cancel)")
        if reply:
            try:
                await reply.edit_reply_markup(reply_markup=None)
            except Exception:
                pass
            await message_answer_logged(reply, "TP Sender cancelled.")
        return

    event = get_event(code)
    if event is None or not (event.is_take_profit or event.code == "sl"):
        await callback.answer("Bad choice.", show_alert=True)
        return

    data = await state.get_data()
    channel = str(data.get("channel") or "")
    if channel not in _CHANNEL_LABELS:
        await callback.answer("Session expired. Use /tp to restart.", show_alert=True)
        await state.clear()
        return

    # Render preview against the default symbol (no live signal context here).
    preview = event.render(_DEFAULT_SYMBOL)
    await state.update_data(event_code=event.code)
    await state.set_state(TPSenderStates.confirming)

    try:
        await callback.answer()
    except Exception:
        log.exception("callback.answer (tps:lvl)")
    if reply:
        try:
            await reply.edit_reply_markup(reply_markup=None)
        except Exception:
            pass
        await message_answer_logged(
            reply,
            (
                f"Ready to post → {_CHANNEL_LABELS[channel]}\n"
                f"Event: {event.label}\n\n"
                "Preview:\n\n"
                f"{preview}"
            ),
            reply_markup=tp_sender_confirm_keyboard(),
        )


# ─────────────────────────────────────────────────────────────────────────────
# Step 3: confirm + post
# ─────────────────────────────────────────────────────────────────────────────


async def _post_to_targets(
    bot: Bot,
    app_ctx: AppContext,
    channel: str,
    event: EventConfig,
) -> tuple[list[str], list[str]]:
    """Returns (successes, errors)."""
    s = app_ctx.settings
    targets: list[tuple[str, str]] = []
    if channel in {"vip", "both"}:
        if s.vip_channel_id:
            targets.append(("VIP", s.vip_channel_id))
        else:
            return [], ["VIP_CHANNEL_ID is not configured."]
    if channel in {"free", "both"}:
        if s.free_channel_id:
            targets.append(("Public", s.free_channel_id))
        else:
            return [], ["FREE_CHANNEL_ID is not configured."]

    successes: list[str] = []
    errors: list[str] = []
    text = event.render(_DEFAULT_SYMBOL)
    for name, chat_id in targets:
        try:
            await bot.send_message(chat_id=chat_id, text=text)
            successes.append(name)
        except Exception as exc:
            log.exception("TP Sender post to %s failed", name)
            errors.append(f"{name}: {exc!s}")
    return successes, errors


@router.callback_query(F.data.startswith("tps:confirm:"), _DM_CALLBACK)
async def on_confirm(
    callback: CallbackQuery,
    bot: Bot,
    state: FSMContext,
    app_ctx: AppContext,
) -> None:
    action = (callback.data or "").split(":", 2)[2]
    reply = callback.message if isinstance(callback.message, Message) else None

    if action == "cancel":
        await state.clear()
        try:
            await callback.answer("Cancelled.")
        except Exception:
            log.exception("callback.answer (tps confirm cancel)")
        if reply:
            try:
                await reply.edit_reply_markup(reply_markup=None)
            except Exception:
                pass
            await message_answer_logged(reply, "TP Sender cancelled.")
        return

    if action != "send":
        await callback.answer("Bad action.", show_alert=True)
        return

    data = await state.get_data()
    channel = str(data.get("channel") or "")
    code = str(data.get("event_code") or "")
    event = get_event(code)
    if not event or channel not in _CHANNEL_LABELS:
        await callback.answer("Session expired. Use /tp again.", show_alert=True)
        await state.clear()
        return

    successes, errors = await _post_to_targets(bot, app_ctx, channel, event)

    try:
        await callback.answer("Posted." if successes else "Failed.")
    except Exception:
        log.exception("callback.answer (tps confirm send)")
    if reply:
        try:
            await reply.edit_reply_markup(reply_markup=None)
        except Exception:
            pass
        parts: list[str] = []
        if successes:
            parts.append(f"✅ Sent ({event.label}) → {', '.join(successes)}")
        if errors:
            parts.append("⚠️ Errors:\n" + "\n".join(f"- {e}" for e in errors))
        await message_answer_logged(
            reply, "\n\n".join(parts) if parts else "Nothing sent."
        )

    log.info(
        "TP Sender: %s -> %s by admin=%s",
        event.label,
        channel,
        callback.from_user.id if callback.from_user else None,
    )
    await state.clear()
