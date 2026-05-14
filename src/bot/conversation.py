import logging
from telegram import Update
from telegram.ext import (
    ContextTypes, ConversationHandler, CommandHandler,
    MessageHandler, CallbackQueryHandler, filters,
)
from src.models.entry import Entry, today_str
from src.bot.keyboards import date_keyboard, class_keyboard, confirm_keyboard, sanity_keyboard
from src.sheets.writer import write_entry_and_totals
from src.storage.log import log_entry
from src.storage.users import get_spreadsheet_id

log = logging.getLogger(__name__)

# Conversation states
(DATE, DATE_MANUAL, VEHICLE, CLASS, START, END, MILEAGE, CONFIRM, SANITY) = range(9)

ENTRY_KEY = "pending_entry"
WARNINGS_KEY = "pending_warnings"


# ── Guards ────────────────────────────────────────────────────────────────────

async def _start_add(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    uid = update.effective_user.id
    sid = await get_spreadsheet_id(uid)
    if not sid:
        await update.message.reply_text(
            "Link a Google Sheet first with /register (URL or spreadsheet ID)."
        )
        return ConversationHandler.END

    context.user_data.clear()
    today = today_str()
    await update.message.reply_text(
        "📅 What date?",
        reply_markup=date_keyboard(today),
    )
    return DATE


async def _date_button(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    data = query.data  # "date:08/05/26" or "date:manual"
    _, value = data.split(":", 1)

    if value == "manual":
        await query.edit_message_text("📅 Enter the date (DD/MM/YY):")
        return DATE_MANUAL

    context.user_data[ENTRY_KEY] = {"date_str": value}
    await query.edit_message_text(f"📅 {value}\n\n🚗 Vehicle number?")
    return VEHICLE


async def _date_manual(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    text = update.message.text.strip()
    parts = text.split("/")
    if len(parts) != 3 or not all(p.isdigit() for p in parts):
        await update.message.reply_text("❌ Invalid format. Please use DD/MM/YY (e.g. 08/05/26):")
        return DATE_MANUAL

    context.user_data[ENTRY_KEY] = {"date_str": text}
    await update.message.reply_text(f"📅 {text}\n\n🚗 Vehicle number?")
    return VEHICLE


async def _vehicle(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    vehicle = update.message.text.strip().upper()
    if not vehicle:
        await update.message.reply_text("❌ Vehicle number cannot be empty. Try again:")
        return VEHICLE

    context.user_data[ENTRY_KEY]["vehicle"] = vehicle
    await update.message.reply_text(
        f"🚗 {vehicle}\n\n🏷️ Vehicle class?",
        reply_markup=class_keyboard(),
    )
    return CLASS


async def _class_button(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    _, value = query.data.split(":", 1)
    context.user_data[ENTRY_KEY]["vehicle_class"] = int(value)
    await query.edit_message_text(
        f"🏷️ Class {value}\n\n🔢 Odometer START? (or type `skip`)"
    )
    return START


def _is_skip(text: str) -> bool:
    return text.strip().lower() in ("skip", "/skip", "-", "n/a", "na")


async def _start_odo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    text = update.message.text.strip()
    if _is_skip(text):
        context.user_data[ENTRY_KEY]["odo_start"] = None
    else:
        if not text.isdigit():
            await update.message.reply_text("❌ Enter a number or type /skip:")
            return START
        context.user_data[ENTRY_KEY]["odo_start"] = int(text)

    await update.message.reply_text("🔢 Odometer END? (or /skip)")
    return END


async def _end_odo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    text = update.message.text.strip()
    if _is_skip(text):
        context.user_data[ENTRY_KEY]["odo_end"] = None
    else:
        if not text.isdigit():
            await update.message.reply_text("❌ Enter a number or type /skip:")
            return END
        context.user_data[ENTRY_KEY]["odo_end"] = int(text)

    data = context.user_data[ENTRY_KEY]
    # If either start or end was skipped, ask for mileage
    if data.get("odo_start") is None or data.get("odo_end") is None:
        await update.message.reply_text("🔢 Mileage (km)?")
        return MILEAGE

    return await _build_and_confirm(update, context)


async def _mileage(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    text = update.message.text.strip()
    if not text.isdigit():
        await update.message.reply_text("❌ Enter a number:")
        return MILEAGE
    context.user_data[ENTRY_KEY]["mileage"] = int(text)
    return await _build_and_confirm(update, context)


async def _build_and_confirm(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    data = context.user_data[ENTRY_KEY]
    entry = Entry(
        date_str=data["date_str"],
        vehicle=data["vehicle"],
        vehicle_class=data["vehicle_class"],
        odo_start=data.get("odo_start"),
        odo_end=data.get("odo_end"),
        mileage=data.get("mileage"),
    )

    try:
        derive_warns = entry.derive_missing()
    except ValueError as e:
        await update.message.reply_text(f"❌ {e}\n\nStart over with /add")
        return ConversationHandler.END

    errors = entry.validate()
    if errors:
        msg = "❌ " + "\n".join(errors) + "\n\nStart over with /add"
        await update.message.reply_text(msg)
        return ConversationHandler.END

    sanity_warns = entry.sanity_warnings()
    all_warnings = derive_warns + sanity_warns
    context.user_data[ENTRY_KEY] = entry.__dict__
    context.user_data[WARNINGS_KEY] = all_warnings

    warn_text = ""
    if all_warnings:
        warn_text = "\n⚠️ " + "\n⚠️ ".join(all_warnings) + "\n"

    msg = f"✅ Mileage: {entry.mileage} km\n\nConfirm entry:\n{entry.summary()}{warn_text}"
    await update.message.reply_text(msg, reply_markup=confirm_keyboard())
    return CONFIRM


async def _confirm_button(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    _, action = query.data.split(":", 1)

    if action == "cancel":
        await query.edit_message_text("❌ Entry cancelled.")
        return ConversationHandler.END

    if action == "edit":
        await query.edit_message_text(
            "✏️ Starting over. Use /add to re-enter."
        )
        return ConversationHandler.END

    # action == "yes"
    warnings = context.user_data.get(WARNINGS_KEY, [])
    sanity_warns = [w for w in warnings if "over 1000" in w]

    if sanity_warns:
        context.user_data["awaiting_sanity"] = True
        warn_text = "\n⚠️ ".join(sanity_warns)
        await query.edit_message_text(
            f"⚠️ {warn_text}\n\nAre you sure you want to submit?",
            reply_markup=sanity_keyboard(),
        )
        return SANITY

    return await _do_submit(query, context)


async def _sanity_button(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    _, action = query.data.split(":", 1)

    if action == "cancel":
        await query.edit_message_text("❌ Entry cancelled.")
        return ConversationHandler.END

    return await _do_submit(query, context)


async def _do_submit(query, context: ContextTypes.DEFAULT_TYPE) -> int:
    data = context.user_data[ENTRY_KEY]
    entry = Entry(**{k: data[k] for k in Entry.__dataclass_fields__})

    uid = query.from_user.id
    sid = await get_spreadsheet_id(uid)
    if not sid:
        await query.edit_message_text(
            "❌ No spreadsheet linked. Use /register, then try /add again."
        )
        return ConversationHandler.END

    await query.edit_message_text("⏳ Writing to sheet…")
    try:
        row, sn, totals = await write_entry_and_totals(entry, sid, uid)
    except Exception as e:
        log.exception("write_entry failed")
        await query.edit_message_text(f"❌ Failed to write to sheet: {e}")
        return ConversationHandler.END

    try:
        await log_entry(query.from_user.id, entry, row)
    except Exception as e:
        log.exception("log_entry failed after sheet write")
        await query.edit_message_text(
            f"✅ Added as entry #{sn} in the sheet.\n\n"
            f"Running totals — Class 3: {totals['class3']} km | Class 4: {totals['class4']} km\n\n"
            f"⚠️ Sheet OK but local log failed: {e}"
        )
        return ConversationHandler.END

    await query.edit_message_text(
        f"✅ Added as entry #{sn} in the sheet.\n\n"
        f"Running totals — Class 3: {totals['class3']} km | Class 4: {totals['class4']} km"
    )

    return ConversationHandler.END


async def _cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text("❌ Entry cancelled.")
    return ConversationHandler.END


def build_conversation_handler() -> ConversationHandler:
    return ConversationHandler(
        entry_points=[
            CommandHandler("add", _start_add),
        ],
        states={
            DATE: [CallbackQueryHandler(_date_button, pattern="^date:")],
            DATE_MANUAL: [MessageHandler(filters.TEXT & ~filters.COMMAND, _date_manual)],
            VEHICLE: [MessageHandler(filters.TEXT & ~filters.COMMAND, _vehicle)],
            CLASS: [CallbackQueryHandler(_class_button, pattern="^class:")],
            START: [
                CommandHandler("skip", _start_odo),
                MessageHandler(filters.TEXT & ~filters.COMMAND, _start_odo),
            ],
            END: [
                CommandHandler("skip", _end_odo),
                MessageHandler(filters.TEXT & ~filters.COMMAND, _end_odo),
            ],
            MILEAGE: [MessageHandler(filters.TEXT & ~filters.COMMAND, _mileage)],
            CONFIRM: [CallbackQueryHandler(_confirm_button, pattern="^confirm:")],
            SANITY: [CallbackQueryHandler(_sanity_button, pattern="^sanity:")],
        },
        fallbacks=[CommandHandler("cancel", _cancel)],
        allow_reentry=True,
    )
