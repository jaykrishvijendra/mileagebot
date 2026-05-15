import asyncio
import logging
import os
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

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


class _HealthHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"ok")

    def log_message(self, *args):
        pass


def _start_health_server():
    port = int(os.environ.get("PORT", 8080))
    server = HTTPServer(("0.0.0.0", port), _HealthHandler)
    log.info("Health check server on port %d", port)
    server.serve_forever()


async def _post_init(application: Application) -> None:
    commands = [
        BotCommand("start", "Welcome and command list"),
        BotCommand("register", "Link your Google Sheet"),
        BotCommand("add", "Log a driving entry"),
        BotCommand("totals", "Totals for current month"),
        BotCommand("totals_all", "Totals for all months"),
        BotCommand("help", "Help"),
        BotCommand("cancel", "Cancel registration or entry"),
    ]
    await application.bot.set_my_commands(commands)
    await application.bot.set_chat_menu_button(menu_button=MenuButtonCommands())


async def _error_handler(update, context):
    log.exception("Unhandled error", exc_info=context.error)
    if update and update.effective_message:
        await update.effective_message.reply_text(
            f"❌ Internal error: {context.error}"
        )


async def _run_bot():
    app = (
        ApplicationBuilder()
        .token(TELEGRAM_BOT_TOKEN)
        .post_init(_post_init)
        .build()
    )

    app.add_error_handler(_error_handler)
    app.add_handler(build_register_handler())
    app.add_handler(build_conversation_handler())
    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("help", cmd_help))
    app.add_handler(CommandHandler("totals", cmd_totals))
    app.add_handler(CommandHandler("totals_all", cmd_totals_all))

    log.info("Bot started.")
    async with app:
        await app.start()
        await app.updater.start_polling()
        await asyncio.Event().wait()  # run forever


def main():
    threading.Thread(target=_start_health_server, daemon=True).start()
    asyncio.run(_run_bot())


if __name__ == "__main__":
    main()
