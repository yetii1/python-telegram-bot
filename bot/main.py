"""Telegram bot with webhook instead of polling."""
import logging
from telegram import Update
from telegram.ext import Application, ApplicationBuilder
from aiohttp import web
import os
from bot.config import Settings
from bot.handlers import error_handler, register_handlers, set_bot_commands

logger = logging.getLogger(__name__)

def configure_logging(level_name: str) -> None:
    level = getattr(logging, level_name, logging.INFO)
    logging.basicConfig(
        format="%(asctime)s %(name)s [%(levelname)s] %(message)s",
        level=level,
    )

def build_application(settings: Settings) -> Application:
    application = (
        ApplicationBuilder()
        .token(settings.bot_token)
        .post_init(set_bot_commands)
        .build()
    )
    register_handlers(application)
    application.add_error_handler(error_handler)
    return application

async def handle_telegram(request, application):
    """Handle Telegram webhook updates."""
    try:
        data = await request.json()
        update = Update.de_json(data, application.bot)
        await application.process_update(update)
        return web.Response(status=200)
    except Exception as e:
        logger.error(f"Webhook error: {e}")
        return web.Response(status=400)

async def handle_health(request):
    return web.json_response({'ok': True})

async def start_webhook(application):
    """Start webhook server."""
    port = int(os.environ.get('PORT', 8080))
    
    async def telegram_handler(request):
        return await handle_telegram(request, application)
    
    app = web.Application()
    app.router.add_post('/webhook', telegram_handler)
    app.router.add_get('/health', handle_health)
    
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, '0.0.0.0', port)
    await site.start()
    logger.info(f'Webhook server on port {port}')
    
    # Set webhook URL
    webhook_url = os.environ.get('WEBHOOK_URL', f'https://python-telegram-bot-production-6f13.up.railway.app/webhook')
    await application.bot.set_webhook(webhook_url, allowed_updates=['message', 'callback_query'])
    logger.info(f'Webhook set to {webhook_url}')
    
    await application.start()
    
    # Keep running
    import asyncio
    await asyncio.Event().wait()

async def main() -> None:
    settings = Settings.from_env()
    configure_logging(settings.log_level)
    application = build_application(settings)
    
    await start_webhook(application)

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
