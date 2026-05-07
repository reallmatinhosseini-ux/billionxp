from __future__ import annotations

from aiogram import Bot, F, Router
from aiogram.enums import ChatType
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, Message

from app.formatter import format_signal_elite
from app.keyboards import publish_destination_keyboard
from app.middlewares import AppContext
from app.parser import ParsedSignal, parse_signal_any
from app.replies import message_answer_logged
from services import publisher as publish_service
from utils.logger import get_logger

log = get_logger(__name__)

router = Router(name="signals")

_DM = F.chat.type == ChatType.PRIVATE


class PublishStates(StatesGroup):
    choosing_channel = State()


class ParsedSignalSerializationError(Exception):
    pass


def dump_signal(sig: ParsedSignal) -> dict[str, object]:
    payload: dict[str, object] = {
        "direction": sig.direction.upper(),
        "symbol": sig.symbol.upper(),
        "entry_min": sig.entry_min,
        "entry_max": sig.entry_max,
        "sl": sig.sl,
    }
    for i in range(1, 6):
        payload[f"tp{i}"] = sig.tp_levels.get(i)
    return payload


def load_signal(data: dict[str, object]) -> ParsedSignal:
    try:
        levels: dict[int, float] = {}
        for i in range(1, 6):
            raw = data.get(f"tp{i}")
            if raw is not None:
                levels[int(i)] = float(raw)
        order = sorted(levels.keys())
        if not levels:
            raise ValueError("no tp")
        return ParsedSignal(
            direction=str(data["direction"]),
            symbol=str(data["symbol"]),
            entry_min=float(data["entry_min"]),
            entry_max=float(data["entry_max"]),
            sl=float(data["sl"]),
            tp_levels=levels,
            tp_order=order,
        )
    except (KeyError, TypeError, ValueError) as exc:
        raise ParsedSignalSerializationError from exc


@router.message(F.text & ~F.text.startswith("/"), _DM)
async def ingest_signal(
    message: Message,
    state: FSMContext,
) -> None:
    log.info("RAW SIGNAL handler called chat=%s user=%s", message.chat.id, message.from_user.id)

    raw_text = message.text or ""
    parsed_ok, extras, errors = parse_signal_any(raw_text)
    if parsed_ok is None:
        log.info("PARSE FAILED: %s", errors)
        bullets = "\n".join(f"- {e}" for e in (errors or ["Unknown parsing error."]))
        explanation = (
            "Could not parse this as a signal.\n\n"
            "Tip: include direction (BUY/SELL), entry (one or two prices), SL, and at least one TP.\n\n"
            "Details:\n" + bullets
        )
        await message_answer_logged(message, explanation)
        return

    log.info("PARSE SUCCESS direction=%s entry=%s-%s", parsed_ok.direction, parsed_ok.entry_min, parsed_ok.entry_max)

    body = format_signal_elite(
        parsed_ok,
        order_type=extras.order_type,
    )
    preview_text = "Here is your formatted signal:\n\n" + body
    sent = await message_answer_logged(
        message,
        preview_text,
        reply_markup=publish_destination_keyboard(),
    )
    if sent is None:
        log.warning("Skipped FSM persist — preview failed to send")
        return

    await state.update_data(
        signal=dump_signal(parsed_ok),
        order_type=extras.order_type,
    )
    await state.set_state(PublishStates.choosing_channel)


async def _persist(
    bot: Bot,
    app_ctx: AppContext,
    sig: ParsedSignal,
    dest: str,
    *,
    order_type: str = "",
) -> str:
    s = app_ctx.settings
    if dest == "vip":
        msg = await publish_service.send_vip_signal(
            bot,
            s,
            sig,
            order_type=order_type,
        )
        sid = await app_ctx.db.insert_signal(
            symbol=sig.symbol.upper(),
            direction=sig.direction.upper(),
            entry_min=sig.entry_min,
            entry_max=sig.entry_max,
            sl=sig.sl,
            tp1=sig.tp_levels.get(1),
            tp2=sig.tp_levels.get(2),
            tp3=sig.tp_levels.get(3),
            tp4=sig.tp_levels.get(4),
            tp5=sig.tp_levels.get(5),
            channel_type="vip",
            telegram_message_id=msg.message_id,
            telegram_chat_id=str(msg.chat.id),
        )
        return f"VIP posted (#db {sid}, msg {msg.message_id})."

    if dest == "free":
        if not (s.free_cta_username.strip()):
            raise ValueError("FREE_CTA_USERNAME is missing in .env")
        msg = await publish_service.send_free_signal(
            bot,
            s,
            sig,
            order_type=order_type,
        )
        sid = await app_ctx.db.insert_signal(
            symbol=sig.symbol.upper(),
            direction=sig.direction.upper(),
            entry_min=sig.entry_min,
            entry_max=sig.entry_max,
            sl=sig.sl,
            tp1=sig.tp_levels.get(1),
            tp2=sig.tp_levels.get(2),
            tp3=sig.tp_levels.get(3),
            tp4=sig.tp_levels.get(4),
            tp5=sig.tp_levels.get(5),
            channel_type="free",
            telegram_message_id=msg.message_id,
            telegram_chat_id=str(msg.chat.id),
        )
        return f"FREE posted (#db {sid}, msg {msg.message_id})."

    raise ValueError("unknown destination")


_DM_CALLBACK = F.message.chat.type == ChatType.PRIVATE


@router.callback_query(F.data.startswith("pub:"), _DM_CALLBACK)
async def choose_destination(
    callback: CallbackQuery,
    bot: Bot,
    state: FSMContext,
    app_ctx: AppContext,
) -> None:
    action = callback.data.split(":", 1)[1] if callback.data else ""
    reply_dm = callback.message if isinstance(callback.message, Message) else None

    async def send_text_fallback(text: str) -> None:
        if reply_dm is not None:
            await message_answer_logged(reply_dm, text)
            return
        uid = callback.from_user.id if callback.from_user else None
        if uid is not None:
            try:
                await bot.send_message(uid, text)
                log.debug("finalize via send_message fallback uid=%s", uid)
            except Exception:
                log.exception("send_message finalize fallback failed uid=%s", uid)

    async def finalize(text: str | None) -> None:
        if callback.message:
            try:
                await callback.message.edit_reply_markup(reply_markup=None)
            except Exception:
                log.debug("edit_reply_markup skipped", exc_info=True)
        if text:
            await send_text_fallback(text)
        await state.clear()

    if action == "cancel":
        try:
            await callback.answer()
        except Exception:
            log.exception("callback.answer (cancel)")
        await finalize("Publishing cancelled.")
        return

    data = await state.get_data()
    raw = data.get("signal")
    order_type = str(data.get("order_type") or "")
    if not isinstance(raw, dict):
        try:
            await callback.answer("Session expired.", show_alert=True)
        except Exception:
            log.exception("callback.answer session")
        if reply_dm:
            await message_answer_logged(
                reply_dm, "Session expired. Paste the signal again."
            )
        elif callback.from_user:
            try:
                await bot.send_message(
                    callback.from_user.id,
                    "Session expired. Paste the signal again.",
                )
            except Exception:
                log.exception("send_message session-expired fallback")
        await state.clear()
        return

    try:
        sig = load_signal(raw)
    except ParsedSignalSerializationError:
        log.exception("load_signal deserialization")
        try:
            await callback.answer("Broken session data.", show_alert=True)
        except Exception:
            log.exception("callback.answer broken")
        if reply_dm:
            await message_answer_logged(
                reply_dm,
                "Session data was corrupted. Paste the signal again.",
            )
        elif callback.from_user:
            try:
                await bot.send_message(
                    callback.from_user.id,
                    "Session data was corrupted. Paste the signal again.",
                )
            except Exception:
                log.exception("send_message corrupt-session fallback")
        await state.clear()
        return

    s = app_ctx.settings

    async def exec_publish() -> None:
        notes: list[str] = []
        if action in {"vip", "both"}:
            if not s.vip_channel_id:
                raise ValueError("VIP_CHANNEL_ID missing")
            notes.append(
                await _persist(
                    bot,
                    app_ctx,
                    sig,
                    "vip",
                    order_type=order_type,
                )
            )
        if action in {"free", "both"}:
            if not s.free_channel_id:
                raise ValueError("FREE_CHANNEL_ID missing")
            notes.append(
                await _persist(
                    bot,
                    app_ctx,
                    sig,
                    "free",
                    order_type=order_type,
                )
            )

        summary = (
            "\n".join(notes)
            if notes
            else "Nothing published (unsupported action)."
        )
        await finalize(summary)

    try:
        await callback.answer()
    except Exception:
        log.exception("callback.answer (ack)")
    try:
        await exec_publish()
    except Exception as exc:
        log.exception("publish flow")
        await finalize(f"Publish failed: {exc!s}")
