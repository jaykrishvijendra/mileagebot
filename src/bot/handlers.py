import asyncio
import logging

from telegram import Update
from telegram.ext import ContextTypes

from src.models.entry import today_str
from src.sheets.reader import get_month_totals, get_all_totals
from src.storage.users import get_spreadsheet_id

log = logging.getLogger(__name__)

HELP_TEXT = """
/register — Link your Google Sheet (required once)
/add — Log a new driving entry
/totals — Running totals for current month
/totals_all — Totals for all months
/cancel — Abort current entry or registration
/help — This message
""".strip()


def registered_required(func):
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE):
        uid = update.effective_user.id
        sid = await get_spreadsheet_id(uid)
        if not sid:
            await update.message.reply_text(
                "Link a Google Sheet first with /register (send the spreadsheet URL or ID).\n"
                "You must share that sheet as Editor with the bot’s service account — "
                "/register shows the email to add."
            )
            return
        return await func(update, context, spreadsheet_id=sid)

    wrapper.__name__ = func.__name__
    return wrapper


async def cmd_help(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(HELP_TEXT)


async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 Transport Logbook Bot\n\n"
        + HELP_TEXT
        + "\n\nNew here? Run /register with your sheet link or ID first."
    )


@registered_required
async def cmd_totals(update: Update, context: ContextTypes.DEFAULT_TYPE, *, spreadsheet_id: str):
    await update.message.reply_text("⏳ Fetching totals…")
    try:
        totals = await asyncio.to_thread(get_month_totals, today_str(), spreadsheet_id)
        await update.message.reply_text(
            f"📊 This month:\n"
            f"  Class 3: {totals['class3']} km\n"
            f"  Class 4: {totals['class4']} km"
        )
    except Exception as e:
        log.exception("totals failed")
        await update.message.reply_text(f"❌ Failed to fetch totals: {e}")


@registered_required
async def cmd_totals_all(update: Update, context: ContextTypes.DEFAULT_TYPE, *, spreadsheet_id: str):
    await update.message.reply_text("⏳ Fetching totals…")
    try:
        rows = await asyncio.to_thread(get_all_totals, spreadsheet_id)
        if not rows:
            await update.message.reply_text("No month data found.")
            return
        lines = ["📊 All month totals:"]
        sum3 = sum4 = 0
        for r in rows:
            sum3 += r["class3"]
            sum4 += r["class4"]
            lines.append(
                f"  {r['month']}: Class 3 = {r['class3']} km | Class 4 = {r['class4']} km"
            )
        lines.append("")
        lines.append(
            f"  Total — Class 3 = {sum3} km | Class 4 = {sum4} km"
        )
        lines.append(f"  Combined mileage: {sum3 + sum4} km")
        await update.message.reply_text("\n".join(lines))
    except Exception as e:
        log.exception("totals_all failed")
        await update.message.reply_text(f"❌ Failed to fetch totals: {e}")
