"""Entrypoint for the Telegram bot."""

import logging

from telegram import Update
from telegram.ext import Application, ApplicationBuilder

from bot.config import Settings
from bot.handlers import error_handler, register_handlers


logger = logging.getLogger(__name__)


def configure_logging(level_name: str) -> None:
    level = getattr(logging, level_name, logging.INFO)
    logging.basicConfig(
        format="%(asctime)s %(name)s [%(levelname)s] %(message)s",
        level=level,
    )


def build_application(settings: Settings) -> Application:
    application = ApplicationBuilder().token(settings.bot_token).build()
    register_handlers(application)
    application.add_error_handler(error_handler)
    return application


def main() -> None:
    settings = Settings.from_env()
    configure_logging(settings.log_level)

    application = build_application(settings)
    logger.info("Bot berjalan dengan polling.")
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
