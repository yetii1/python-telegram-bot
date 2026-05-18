import logging
import os
from aiohttp import web

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

try:
    from bot.config import BOT_TOKEN, ADMIN_IDS
except ImportError:
    BOT_TOKEN = os.environ.get('BOT_TOKEN', '8889776236:AAE4jREquiZRhOHmLLC0BcSptBS2bPsfgXQ')
    ADMIN_IDS = [2146907108, 1290896198]

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

async def send_to_telegram(text, bot_token, admin_ids):
    import aiohttp
    for admin_id in admin_ids:
        try:
            async with aiohttp.ClientSession() as session:
                url = f'https://api.telegram.org/bot{bot_token}/sendMessage'
                payload = {'chat_id': admin_id, 'text': text, 'parse_mode': 'HTML'}
                async with session.post(url, json=payload, timeout=aiohttp.ClientTimeout(total=10)) as resp:
                    logger.info(f"Message sent: {resp.status}")
        except Exception as e:
            logger.error(f"Error: {e}")

async def handle_lead(request):
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

    await send_to_telegram(msg, BOT_TOKEN, ADMIN_IDS)
    return web.json_response({'ok': True, 'lead_num': lead_num}, headers={'Access-Control-Allow-Origin': '*'})

async def handle_options(request):
    return web.Response(status=200, headers={
        'Access-Control-Allow-Origin': '*',
        'Access-Control-Allow-Methods': 'POST, OPTIONS, GET',
        'Access-Control-Allow-Headers': 'Content-Type'
    })

async def handle_health(request):
    return web.json_response({'ok': True}, headers={'Access-Control-Allow-Origin': '*'})

app = web.Application()
app.router.add_post('/api/lead', handle_lead)
app.router.add_options('/api/lead', handle_options)
app.router.add_get('/health', handle_health)
app.router.add_get('/', handle_health)

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8080))
    web.run_app(app, host='0.0.0.0', port=port)
