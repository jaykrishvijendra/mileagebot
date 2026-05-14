import asyncio
import logging

from telegram import Update
from telegram.ext import (
    ContextTypes,
    ConversationHandler,
    CommandHandler,
    MessageHandler,
    filters,
)

from src.storage.users import (
    parse_spreadsheet_id,
    service_account_email,
    set_spreadsheet_id,
)
from src.sheets.client import validate_spreadsheet_access

log = logging.getLogger(__name__)

REGISTER_WAIT = 1


async def register_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    combined = " ".join(context.args or []).strip()
    if combined:
        sid = parse_spreadsheet_id(combined)
        if sid:
            await _try_save(update, sid)
            return ConversationHandler.END
        await update.message.reply_text(
            "Could not read a spreadsheet ID from that. "
            "Send the full Google Sheets URL or the ID, or run /register without arguments."
        )
        return ConversationHandler.END

    email = service_account_email()
    await update.message.reply_text(
        "Send your Google Sheet link (from the browser address bar) or the spreadsheet ID.\n\n"
        "The bot’s Google service account must have Editor access to that sheet. "
        "In Google Sheets: Share → add this address as Editor:\n\n"
        f"{email}\n\n"
        "Without that share, writes will fail.\n\n"
        "/cancel to stop."
    )
    return REGISTER_WAIT


async def register_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    sid = parse_spreadsheet_id(update.message.text)
    if not sid:
        await update.message.reply_text(
            "That doesn’t look like a Sheets URL or ID. Try again or /cancel."
        )
        return REGISTER_WAIT
    await _try_save(update, sid)
    return ConversationHandler.END


async def register_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text("Registration cancelled.")
    return ConversationHandler.END


async def _try_save(update: Update, spreadsheet_id: str) -> None:
    await update.message.reply_text("Checking access…")
    try:
        await asyncio.to_thread(validate_spreadsheet_access, spreadsheet_id)
    except Exception as e:
        log.exception("spreadsheet validation failed")
        await update.message.reply_text(
            f"Could not open that spreadsheet ({e}).\n\n"
            "Share the file with Editor access for:\n"
            f"{service_account_email()}"
        )
        return

    await set_spreadsheet_id(update.effective_user.id, spreadsheet_id)
    await update.message.reply_text(
        "Registration saved. You can use /add, /totals, and /totals_all with this sheet.\n\n"
        "Run /register again anytime to switch to another spreadsheet."
    )


def build_register_handler() -> ConversationHandler:
    return ConversationHandler(
        entry_points=[CommandHandler("register", register_start)],
        states={
            REGISTER_WAIT: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, register_message),
            ],
        },
        fallbacks=[CommandHandler("cancel", register_cancel)],
        allow_reentry=True,
    )
