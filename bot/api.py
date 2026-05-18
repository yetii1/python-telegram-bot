"""
api.py - Веб-сервер для приёма заявок с сайта White Stone
Работает вместе с существующим ботом (bot/main.py)
Слушает на /api/lead и отправляет заявки в Telegram
"""

import asyncio
import logging
import json
from aiohttp import web
from bot.config import BOT_TOKEN, ADMIN_IDS

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Счётчик заявок (простой файл)
COUNTER_FILE = '/tmp/lead_counter.txt'

def get_next_lead_number() -> int:
    """Возвращает следующий номер заявки."""
    try:
        if import_os_exists(COUNTER_FILE):
            current = int(open(COUNTER_FILE).read().strip())
        else:
            current = 0
        new_num = current + 1
        open(COUNTER_FILE, 'w').write(str(new_num))
        return new_num
    except Exception as e:
        logger.error(f"Counter error: {e}")
        return 0

def import_os_exists(path):
    """Проверяет существование файла."""
    import os
    return os.path.exists(path)

async def send_to_telegram(text: str, bot_token: str, admin_ids: list):
    """Отправляет сообщение в Telegram всем админам."""
    import aiohttp
    for admin_id in admin_ids:
        try:
            async with aiohttp.ClientSession() as session:
                url = f'https://api.telegram.org/bot{bot_token}/sendMessage'
                payload = {
                    'chat_id': admin_id,
                    'text': text,
                    'parse_mode': 'HTML'
                }
                async with session.post(url, json=payload) as resp:
                    if resp.status == 200:
                        logger.info(f"Message sent to {admin_id}")
                    else:
                        logger.error(f"Failed to send to {admin_id}: {resp.status}")
        except Exception as e:
            logger.error(f"Telegram error for {admin_id}: {e}")

async def handle_lead(request: web.Request) -> web.Response:
    """Принимает заявку с сайта и отправляет в Telegram."""
    try:
        data = await request.json()
    except Exception as e:
        logger.error(f"Invalid JSON: {e}")
        return web.json_response({'ok': False, 'error': 'invalid json'}, status=400)

    # Извлекаем данные
    name = data.get('name', '').strip()
    phone = data.get('phone', '').strip()
    email = data.get('email', '').strip()
    ptype = data.get('ptype', '').strip()
    message = data.get('message', '').strip()
    page = data.get('page', '').strip()
    recaptcha_token = data.get('recaptcha_token', '').strip()

    # Валидация
    if not name or not phone:
        return web.json_response({'ok': False, 'error': 'name and phone required'}, status=400)

    # IP клиента
    client_ip = request.headers.get('X-Forwarded-For', request.remote or '—').split(',')[0].strip()

    # Тестовая заявка?
    full_text = f"{message} {ptype}".upper()
    is_test = 'ТЕСТ' in full_text
    lead_num = None if is_test else get_next_lead_number()

    # Формируем сообщение
    header = f"🌐 <b>ЗАЯВКА №{lead_num}</b>" if not is_test else "🌐 <b>ТЕСТОВАЯ ЗАЯВКА</b>"
    
    msg_lines = [
        header,
        '─' * 30,
        f"👤 <b>{name}</b>",
        f"📞 <b>{phone}</b>",
    ]
    
    if email:
        msg_lines.append(f"📧 {email}")
    if ptype:
        msg_lines.append(f"🏗 {ptype}")
    if message:
        msg_lines.append(f"💬 {message}")
    
    msg_lines.extend([
        '─' * 30,
        f"🌍 IP: <code>{client_ip}</code>",
    ])
    
    if page:
        msg_lines.append(f"📄 Страница: {page}")
    
    if recaptcha_token:
        msg_lines.append(f"✓ reCAPTCHA: пройдена")

    final_message = '\n'.join(msg_lines)

    # Отправляем в Telegram
    try:
        await send_to_telegram(final_message, BOT_TOKEN, ADMIN_IDS)
        logger.info(f"Lead #{lead_num} sent successfully")
        return web.json_response({'ok': True, 'lead_num': lead_num})
    except Exception as e:
        logger.error(f"Failed to send lead: {e}")
        return web.json_response({'ok': False, 'error': 'telegram send failed'}, status=500)

async def handle_health(request: web.Request) -> web.Response:
    """Проверка здоровья сервера."""
    return web.json_response({'ok': True, 'service': 'white-stone-api'})

def create_app():
    """Создаёт aiohttp приложение."""
    app = web.Application()
    app.router.add_post('/api/lead', handle_lead)
    app.router.add_get('/', handle_health)
    app.router.add_get('/health', handle_health)
    return app

async def run_server():
    """Запускает сервер на порту из переменной окружения."""
    import os
    app = create_app()
    port = int(os.environ.get('PORT', 8080))
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, '0.0.0.0', port)
    await site.start()
    logger.info(f'API server running on port {port}')
    # Бесконечный цикл для держания сервера живым
    await asyncio.Event().wait()

if __name__ == '__main__':
    asyncio.run(run_server())
