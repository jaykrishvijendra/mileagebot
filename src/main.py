import logging

from telegram import BotCommand, MenuButtonCommands
from telegram.ext import Application, ApplicationBuilder, CommandHandler

from src.bot.conversation import build_conversation_handler
from src.bot.handlers import cmd_help, cmd_start, cmd_totals, cmd_totals_all
from src.bot.register_conv import build_register_handler
from src.config import TELEGRAM_BOT_TOKEN

logging.basicConfig(
    format="%(asctime)s %(levelname)s %(name)s — %(message)s",
    level=logging.INFO,
)
log = logging.getLogger(__name__)


async def _post_init(application: Application) -> None:
    """Register commands + menu button (Telegram shows these next to / and in the chat menu)."""
    commands = [
        BotCommand("start", "Welcome and command list"),
        BotCommand("register", "Link your Google Sheet"),
        BotCommand("add", "Log a driving entry"),
        BotCommand("totals", "Totals for current month"),
        BotCommand("totals_all", "Totals for all month tabs"),
        BotCommand("help", "Help"),
        BotCommand("cancel", "Cancel registration or entry"),
    ]
    await application.bot.set_my_commands(commands)
    await application.bot.set_chat_menu_button(menu_button=MenuButtonCommands())


def main():
    app = (
        ApplicationBuilder()
        .token(TELEGRAM_BOT_TOKEN)
        .post_init(_post_init)
        .build()
    )

    app.add_handler(build_register_handler())
    app.add_handler(build_conversation_handler())
    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("help", cmd_help))
    app.add_handler(CommandHandler("totals", cmd_totals))
    app.add_handler(CommandHandler("totals_all", cmd_totals_all))

    log.info("Bot started (per-user spreadsheets via /register).")
    app.run_polling()


if __name__ == "__main__":
    main()
