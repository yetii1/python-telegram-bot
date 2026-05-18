"""Entrypoint for the Telegram bot with web API."""
import logging
import os
import threading
from telegram import Update
from telegram.ext import Application, ApplicationBuilder
from aiohttp import web
import asyncio
from bot.config import Settings
from bot.handlers import error_handler, register_handlers, set_bot_commands

logger = logging.getLogger(__name__)

COUNTER_FILE = '/tmp/lead_counter.txt'

def get_next_lead_number():
    try:
        if os.path.exists(COUNTER_FILE):
            current = int(open(COUNTER_FILE).read().strip())
        else:
            current = 0
        new_num = current + 1
        with open(COUNTER_FILE, 'w') as f:
            f.write(str(new_num))
        return new_num
    except:
        return 0

async def send_to_telegram(text, bot):
    settings = Settings.from_env()
    for admin_id in settings.admin_ids:
        try:
            await bot.send_message(chat_id=admin_id, text=text, parse_mode='HTML')
            logger.info(f"Message sent to {admin_id}")
        except Exception as e:
            logger.error(f"Error: {e}")

async def handle_lead(request, bot):
    try:
        data = await request.json()
    except:
        return web.json_response({'ok': False}, status=400, headers={'Access-Control-Allow-Origin': '*'})

    name = data.get('name', '').strip()
    phone = data.get('phone', '').strip()
    
    if not name or not phone:
        return web.json_response({'ok': False}, status=400, headers={'Access-Control-Allow-Origin': '*'})

    email = data.get('email', '').strip()
    ptype = data.get('ptype', '').strip()
    message = data.get('message', '').strip()
    page = data.get('page', '').strip()

    client_ip = request.headers.get('X-Forwarded-For', request.remote or '—').split(',')[0].strip()
    is_test = 'ТЕСТ' in f"{message} {ptype}".upper()
    lead_num = None if is_test else get_next_lead_number()

    header = f"🌐 <b>ЗАЯВКА №{lead_num}</b>" if not is_test else "🌐 <b>ТЕСТОВАЯ</b>"
    msg = f"{header}\n{'─'*30}\n👤 <b>{name}</b>\n📞 <b>{phone}</b>"
    if email:
        msg += f"\n📧 {email}"
    if ptype:
        msg += f"\n🏗 {ptype}"
    if message:
        msg += f"\n💬 {message}"
    msg += f"\n{'─'*30}\n🌍 IP: <code>{client_ip}</code>"
    if page:
        msg += f"\n📄 {page}"

    await send_to_telegram(msg, bot)
    return web.json_response({'ok': True, 'lead_num': lead_num}, headers={'Access-Control-Allow-Origin': '*'})

async def handle_options(request):
    return web.Response(status=200, headers={
        'Access-Control-Allow-Origin': '*',
        'Access-Control-Allow-Methods': 'POST, OPTIONS, GET',
        'Access-Control-Allow-Headers': 'Content-Type'
    })

async def handle_health(request):
    return web.json_response({'ok': True}, headers={'Access-Control-Allow-Origin': '*'})

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

async def web_server(bot, port):
    async def lead_handler(request):
        return await handle_lead(request, bot)
    
    app = web.Application()
    app.router.add_post('/api/lead', lead_handler)
    app.router.add_options('/api/lead', handle_options)
    app.router.add_get('/health', handle_health)
    app.router.add_get('/', handle_health)
    
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, '0.0.0.0', port)
    await site.start()
    logger.info(f'API server on port {port}')
    await asyncio.Event().wait()

def run_web(bot):
    port = int(os.environ.get('PORT', 8080))
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(web_server(bot, port))

def main() -> None:
    settings = Settings.from_env()
    configure_logging(settings.log_level)
    application = build_application(settings)
    
    # Запускаем веб-сервер в отдельном потоке
    web_thread = threading.Thread(target=run_web, args=(application.bot,), daemon=True)
    web_thread.start()
    
    # Запускаем бот в основном потоке
    logger.info("Bot is running with polling.")
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
