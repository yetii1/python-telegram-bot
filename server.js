const express = require('express');
const axios = require('axios');
const fs = require('fs');
const path = require('path');

const app = express();
const PORT = process.env.PORT || 8080;

const BOT_TOKEN = process.env.BOT_TOKEN || '8889776236:AAE4jREquiZRhOHmLLC0BcSptBS2bPsfgXQ';
const ADMIN_IDS = process.env.ADMIN_IDS ? process.env.ADMIN_IDS.split(',').map(Number) : [2146907108, 1290896198];

const COUNTER_FILE = '/tmp/lead_counter.txt';

function getNextLeadNumber() {
  try {
    let current = 0;
    if (fs.existsSync(COUNTER_FILE)) {
      current = parseInt(fs.readFileSync(COUNTER_FILE, 'utf8').trim());
    }
    const newNum = current + 1;
    fs.writeFileSync(COUNTER_FILE, String(newNum));
    return newNum;
  } catch (e) {
    console.error('Counter error:', e);
    return 0;
  }
}

async function sendToTelegram(text) {
  for (const adminId of ADMIN_IDS) {
    try {
      await axios.post(`https://api.telegram.org/bot${BOT_TOKEN}/sendMessage`, {
        chat_id: adminId,
        text: text,
        parse_mode: 'HTML'
      }, { timeout: 10000 });
      console.log(`Message sent to ${adminId}`);
    } catch (e) {
      console.error(`Error sending to ${adminId}:`, e.message);
    }
  }
}

app.use(express.json());

// CORS middleware
app.use((req, res, next) => {
  res.header('Access-Control-Allow-Origin', '*');
  res.header('Access-Control-Allow-Methods', 'POST, OPTIONS, GET');
  res.header('Access-Control-Allow-Headers', 'Content-Type');
  if (req.method === 'OPTIONS') {
    return res.sendStatus(200);
  }
  next();
});

app.post('/api/lead', async (req, res) => {
  try {
    const { name, phone, email = '', ptype = '', message = '', page = '' } = req.body;

    if (!name || !phone) {
      return res.json({ ok: false, error: 'name and phone required' });
    }

    const clientIp = (req.headers['x-forwarded-for'] || req.ip || '—').split(',')[0].trim();
    const isTest = `${message} ${ptype}`.toUpperCase().includes('ТЕСТ');
    const leadNum = isTest ? null : getNextLeadNumber();

    const header = isTest ? '🌐 <b>ТЕСТОВАЯ ЗАЯВКА</b>' : `🌐 <b>ЗАЯВКА №${leadNum}</b>`;
    let msg = `${header}\n${'─'.repeat(30)}\n👤 <b>${name}</b>\n📞 <b>${phone}</b>`;

    if (email) msg += `\n📧 ${email}`;
    if (ptype) msg += `\n🏗 ${ptype}`;
    if (message) msg += `\n💬 ${message}`;

    msg += `\n${'─'.repeat(30)}\n🌍 IP: <code>${clientIp}</code>`;
    if (page) msg += `\n📄 ${page}`;

    await sendToTelegram(msg);
    return res.json({ ok: true, lead_num: leadNum });
  } catch (e) {
    console.error('API error:', e);
    return res.json({ ok: false, error: 'server error' });
  }
});

app.get('/health', (req, res) => {
  res.json({ ok: true, service: 'white-stone-api' });
});

app.get('/', (req, res) => {
  res.json({ ok: true });
});

app.listen(PORT, () => {
  console.log(`Server running on port ${PORT}`);
});
