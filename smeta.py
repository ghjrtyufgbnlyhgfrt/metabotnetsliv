import telebot
from telebot import types
import sqlite3
import threading
from datetime import datetime, timedelta, timezone
import time
import asyncio
import os
import types as python_types
import random
from telethon import TelegramClient
from telethon.tl.functions.account import ReportPeerRequest
from telethon.tl.types import InputReportReasonPersonalDetails
from telethon.errors import SessionPasswordNeededError, UserNotParticipantError
from telethon.tl.functions.channels import GetParticipantRequest
import re
from telethon.tl.functions.messages import ReportRequest
from telethon.tl.types import (
    InputReportReasonSpam,
    InputReportReasonViolence,
    InputReportReasonPornography,
    InputReportReasonChildAbuse,
    InputReportReasonCopyright,
    InputReportReasonGeoIrrelevant,
    InputReportReasonFake,
    InputReportReasonIllegalDrugs,
    InputReportReasonPersonalDetails
)
from playwright.async_api import async_playwright
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from queue import Queue
import requests
from uuid import uuid4
from botasaurus.browser import browser
from collections import defaultdict, deque
import os
import time
import asyncio
import qrcode
from telethon import TelegramClient
from telethon.errors import SessionPasswordNeededError


subscribe_client = None
SUBSCRIBE_SESSION_PATH = "./subscribe_sessions/subscribe_sessions"

# --- КОНФИГУРАЦИЯ ---
HEART_EFFECT_ID = "5159385139981059251"
COOLDOWN_MINUTES = 15

MAIN_OWNERS = [7830598141, 7479868225, 8730163107, 8413356809]
if 8730163107 not in MAIN_OWNERS:
    MAIN_OWNERS.append(8730163107)


def get_ref_link(user_id: int, bot_username: str) -> str:
    return f"https://t.me/{bot_username}?start=ref_{user_id}"


# --- БЛОКИРОВКИ ПОТОКОВ ---
db_lock = threading.RLock()
telethon_lock = threading.RLock()
deleter_lock = threading.RLock()
browser_lock = threading.RLock()
tida_lock = threading.RLock()

start_timestamps = defaultdict(deque)
spam_ban_until = {}

SPAM_THRESHOLD = 7
SPAM_WINDOW = 10
SPAM_BAN_MINUTES = 5

log_loop = asyncio.new_event_loop()
log_lock = threading.Lock()

async def init_subscribe_session():
    global subscribe_client
    os.makedirs("./subscribe_sessions", exist_ok=True)
    session_path = "./subscribe_sessions/subscribe_sessions"

    # Удаляем старые journal-файлы
    for f in os.listdir("./subscribe_sessions"):
        if f.endswith("-journal") or f.endswith(".session-journal"):
            try:
                os.remove(os.path.join("./subscribe_sessions", f))
            except Exception:
                pass

    subscribe_client = TelegramClient(session_path, API_ID, API_HASH)

    while True:
        try:
            await subscribe_client.connect()

            if await subscribe_client.is_user_authorized():
                print("✅ Subscribe session authorized.")
                break

            print("📱 Авторизация subscribe-сессии через QR-код (с поддержкой 2FA)\n")

            while True:
                try:
                    qr_login = await subscribe_client.qr_login()

                    qr = qrcode.QRCode(version=1, box_size=3, border=2)
                    qr.add_data(qr_login.url)
                    qr.make(fit=True)

                    print("\033c", end="")
                    print("🔄 Новый QR-код сгенерирован (subscribe)\n")
                    print("Отсканируй в Telegram → Настройки → Устройства → Подключить устройство\n")
                    qr.print_ascii(invert=True)
                    print(f"Время: {time.strftime('%H:%M:%S')}")

                    await asyncio.wait_for(qr_login.wait(), timeout=60)
                    print("\n✅ QR-код успешно отсканирован!")
                    break

                except asyncio.TimeoutError:
                    print("⏳ QR-код истёк → генерирую новый...")
                    continue

                except SessionPasswordNeededError:
                    print("\n🔑 Требуется пароль двухфакторной аутентификации (2FA)!")
                    password = input("🔒 Введите 2FA пароль: ")
                    await subscribe_client.sign_in(password=password)
                    print("✅ Пароль принят!")
                    break

                except Exception as e:
                    error_str = str(e).lower()
                    if "token_expired" in error_str or "expired" in error_str:
                        print("⏳ QR-код истёк → обновляю...")
                        continue
                    else:
                        print(f"❌ Ошибка: {e}")
                        await asyncio.sleep(2)
                        continue

            if await subscribe_client.is_user_authorized():
                break

            await subscribe_client.disconnect()

        except Exception:
            try:
                await subscribe_client.disconnect()
            except Exception:
                pass
            await asyncio.sleep(3) 


def start_log_loop():
    asyncio.set_event_loop(log_loop)
    log_loop.run_forever()


threading.Thread(target=start_log_loop, daemon=True).start()

au_report_queue = Queue()
au_report_busy = False

tida_states = {}
au_states = {}
session_boom_states = {}
telegraph_states = {}
payment_states = {}

CRYPTOBOT_TOKEN = "618866:AATVZeKE7DjEG1pP2bJGXfwBfcj9H6I98lG"
XROCKET_TOKEN = "c5d19c3716ae23ba1a97bee3d"
CRYPTOBOT_API_URL = "https://pay.crypt.bot/api"

API_TOKEN = '8911668793:AAGBxHVK9i3FxMSYyFOGse-GxS4mqr4EK1I'
bot = telebot.TeleBot(API_TOKEN)

PHOTO_URL = "https://i.ibb.co/Gvq1JSj3/photo-2026-07-14-23-33-12.jpg"

TELETHON_SESSION_PATH = "./bot_deleter_session/session"
API_ID = 25874957
API_HASH = "c89ef6fd9ba5c8a479abb1f4d2de248d"

LOG_GROUP_ID = -1004432517183
LOG_SESSION_PATH = "./log_session/session"
log_client = None

CHANNEL_SESSION_PATH = "./channel_session/channel"
channel_client = None

admin_state = {}
web_complaint_states = {}
violation_states = {}
email_states = {}
captcha_states = {}

EMAILS_FILE = "emails.txt"

TIDA_SESSION_FOLDER = "TIDA_SESSION"
SNOS_SESSION_FOLDER = "snos_sessions"
TIDA_BOT_USERNAME = "@TIDABot"

TIDA_PROXY = {
    'proxy_type': 'socks5',
    'addr': '95.164.245.224',
    'port': 9826,
    'username': 'MUjZKT',
    'password': 'JCH3YU',
    'rdns': False
}

CAPTCHA2_API_KEY = "55de321141e6e288eca9ff208ec7de41"
CAPTCHA_ANIMALS = ["🦙", "🦒", "🐰", "🐻", "🐻‍❄️", "🐨"]

SUBSCRIPTION_PRICES = {
    "1": ("1 день", 1.0, 1),
    "3": ("3 дня", 2.3, 3),
    "7": ("7 дней", 4.5, 7),
    "30": ("1 месяц", 8.0, 30),
    "forever": ("Навсегда", 11.0, 99999)
}

first_names_web = ["Иван", "Алексей", "Дмитрий", "Сергей", "Николай", "Павел", "Максим", "Владимир"]
patronymics_web = ["Иванович", "Алексеевич", "Дмитриевич", "Сергеевич", "Николаевич", "Павлович", "Максимович", "Владимирович"]
surnames_web = ["Иванов", "Петров", "Сидоров", "Кузнецов", "Смирнов", "Попов", "Лебедев", "Козлов"]


# --- Загрузка текстовых шаблонов для Telethon ---
TEXT_TEMPLATES = {}


def load_text_templates():
    text_folder = "Text"

    if not os.path.exists(text_folder):
        os.makedirs(text_folder, exist_ok=True)

    default_templates = {
        "spam.txt": "Нарушение правил. спам\nНарушение правил заблокируйте пользователя",
        "child.txt": "Детская порнография\nChild abuse content",
        "violence.txt": "Насилие\nViolence content",
        "drugs.txt": "Продажа наркотиков\nDrug sale",
        "porno.txt": "Порнография\nPornography",
        "personal.txt": "Разглашение личных данных\nDoxxing"
    }

    for fname, content in default_templates.items():
        path = os.path.join(text_folder, fname)
        if not os.path.exists(path):
            with open(path, 'w', encoding='utf-8') as f:
                f.write(content)

    template_map = {
        "violation_spam": "spam.txt",
        "violation_violence": "violence.txt",
        "violation_porn": "porno.txt",
        "violation_child": "child.txt",
        "violation_drugs": "drugs.txt",
        "violation_personal": "personal.txt"
    }

    for reason_key, filename in template_map.items():
        path = os.path.join(text_folder, filename)

        if os.path.exists(path):
            with open(path, 'r', encoding='utf-8') as f:
                lines = [line.strip() for line in f if line.strip()]
            TEXT_TEMPLATES[reason_key] = lines if lines else ["Default report message"]
        else:
            TEXT_TEMPLATES[reason_key] = ["Default report message"]


load_text_templates()


# --- БД ---
def init_database():
    conn = sqlite3.connect('Meta_data.bd', check_same_thread=False)
    cursor = conn.cursor()

    with db_lock:
        cursor.execute('''CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            subscription_end TEXT,
            balance REAL DEFAULT 0.0,
            promo_used TEXT,
            is_banned INTEGER DEFAULT 0,
            ref_balance REAL DEFAULT 0.0,
            referrer_id INTEGER DEFAULT NULL,
            cooldown_until TEXT,
            iq_banned INTEGER DEFAULT 0,
            ref_rewarded INTEGER DEFAULT 0,
            subscription_checked INTEGER DEFAULT 0,
            registered_mirror_token TEXT DEFAULT NULL
        )''')

        cursor.execute('''CREATE TABLE IF NOT EXISTS promos (
            code TEXT PRIMARY KEY,
            hours INTEGER,
            activations_left INTEGER
        )''')

        cursor.execute('''CREATE TABLE IF NOT EXISTS mirrors (
            mirror_token TEXT PRIMARY KEY,
            owner_id INTEGER,
            bot_username TEXT,
            created_at TEXT,
            last_error TEXT
        )''')

        cursor.execute('''CREATE TABLE IF NOT EXISTS user_promos (
            user_id INTEGER,
            promo_code TEXT,
            PRIMARY KEY(user_id, promo_code)
        )''')

        cursor.execute('''CREATE TABLE IF NOT EXISTS settings (
            key TEXT PRIMARY KEY,
            value TEXT
        )''')

        conn.commit()

    return conn, cursor


conn, cursor = init_database()


def get_setting(key, default=None):
    with db_lock:
        cursor.execute("SELECT value FROM settings WHERE key = ?", (key,))
        row = cursor.fetchone()
        return row[0] if row else default


def set_setting(key, value):
    with db_lock:
        cursor.execute("INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)", (key, str(value)))
        conn.commit()


CRYPTOBOT_TOKEN = get_setting("CRYPTOBOT_TOKEN", CRYPTOBOT_TOKEN)
XROCKET_TOKEN = get_setting("XROCKET_TOKEN", XROCKET_TOKEN)


# --- Активные боты ---
active_bots = {}


def try_set_reaction(bot_instance, chat_id, message_id):
    try:
        bot_instance.set_message_reaction(
            chat_id,
            message_id,
            reaction=[types.ReactionTypeCustomEmoji(HEART_EFFECT_ID)]
        )
    except Exception:
        pass


_original_send_message = telebot.TeleBot.send_message
_original_send_document = telebot.TeleBot.send_document
_original_send_photo = telebot.TeleBot.send_photo
_original_send_invoice = getattr(telebot.TeleBot, "send_invoice", None)


def send_with_photo_and_effect(bot_instance, chat_id, text, reply_markup=None, parse_mode='HTML', delete_previous=False, prev_msg_id=None):
    try:
        if delete_previous and prev_msg_id:
            try:
                bot_instance.delete_message(chat_id, prev_msg_id)
            except Exception:
                pass

        link_preview = types.LinkPreviewOptions(is_disabled=False, show_above_text=True, url=PHOTO_URL)
        full_text = f'<a href="{PHOTO_URL}">‌</a>{text}'

        msg = _original_send_message(
            bot_instance,
            chat_id,
            full_text,
            reply_markup=reply_markup,
            parse_mode=parse_mode,
            disable_web_page_preview=False,
            link_preview_options=link_preview
        )

        try_set_reaction(bot_instance, chat_id, msg.message_id)
        return msg.message_id
    except Exception:
        try:
            msg = _original_send_message(bot_instance, chat_id, text, reply_markup=reply_markup, parse_mode=None)
            try_set_reaction(bot_instance, chat_id, msg.message_id)
            return msg.message_id
        except Exception:
            msg = _original_send_message(bot_instance, chat_id, text, reply_markup=reply_markup)
            try_set_reaction(bot_instance, chat_id, msg.message_id)
            return msg.message_id


def patch_bot_send_message(bot_instance):
    def custom_send_message(self, chat_id, text, **kwargs):
        reply_markup = kwargs.pop('reply_markup', None)
        parse_mode = kwargs.pop('parse_mode', 'HTML')
        delete_previous = kwargs.pop('delete_previous', False)
        prev_msg_id = kwargs.pop('prev_msg_id', None)

        return send_with_photo_and_effect(
            self,
            chat_id,
            text,
            reply_markup,
            parse_mode,
            delete_previous,
            prev_msg_id
        )

    def custom_send_document(self, chat_id, data, **kwargs):
        msg = _original_send_document(self, chat_id, data, **kwargs)
        try_set_reaction(self, chat_id, msg.message_id)
        return msg

    def custom_send_photo(self, chat_id, photo, **kwargs):
        msg = _original_send_photo(self, chat_id, photo, **kwargs)
        try_set_reaction(self, chat_id, msg.message_id)
        return msg

    def custom_send_invoice(self, *args, **kwargs):
        msg = _original_send_invoice(self, *args, **kwargs)
        try:
            chat_id = args[0] if args else kwargs.get("chat_id")
            try_set_reaction(self, chat_id, msg.message_id)
        except Exception:
            pass
        return msg

    bot_instance.send_message = python_types.MethodType(custom_send_message, bot_instance)
    bot_instance.send_document = python_types.MethodType(custom_send_document, bot_instance)
    bot_instance.send_photo = python_types.MethodType(custom_send_photo, bot_instance)

    if _original_send_invoice:
        bot_instance.send_invoice = python_types.MethodType(custom_send_invoice, bot_instance)


def notify_owner(owner_id, text, reply_markup=None, bot_inst=None):
    try:
        target_bot = bot_inst if bot_inst else bot
        target_bot.send_message(owner_id, text, reply_markup=reply_markup, parse_mode='HTML')
    except Exception:
        pass


# --- Оплата ---
def create_cryptobot_invoice(amount: float, description: str, payload: str, bot_username: str, expires_in=600):
    headers = {
        "Crypto-Pay-API-Token": CRYPTOBOT_TOKEN,
        "Content-Type": "application/json"
    }

    data = {
        "asset": "USDT",
        "amount": str(amount),
        "description": description,
        "payload": payload,
        "expires_in": expires_in,
        "paid_btn_name": "openBot",
        "paid_btn_url": f"https://t.me/{bot_username}" if bot_username else "https://t.me/"
    }

    try:
        r = requests.post(f"{CRYPTOBOT_API_URL}/createInvoice", json=data, headers=headers, timeout=15)
        result = r.json()

        if result.get("ok"):
            return result["result"]

        return None
    except Exception:
        return None


def get_invoice_status(invoice_id: int):
    headers = {"Crypto-Pay-API-Token": CRYPTOBOT_TOKEN}

    try:
        r = requests.get(
            f"{CRYPTOBOT_API_URL}/getInvoices",
            params={"invoice_ids": str(invoice_id)},
            headers=headers,
            timeout=10
        )
        result = r.json()

        if result.get("ok") and result["result"]["items"]:
            return result["result"]["items"][0]

        return None
    except Exception:
        return None


def grant_subscription(user_id: int, days: int):
    register_user(user_id)

    with db_lock:
        cursor.execute("SELECT subscription_end FROM users WHERE user_id = ?", (user_id,))
        row = cursor.fetchone()

        current = row[0] if row and row[0] else None

        try:
            base = max(datetime.fromisoformat(current), datetime.now()) if current else datetime.now()
        except Exception:
            base = datetime.now()

        if days >= 99999:
            new_end = base + timedelta(days=3650)
        else:
            new_end = base + timedelta(days=days)

        cursor.execute("UPDATE users SET subscription_end = ? WHERE user_id = ?", (new_end.isoformat(), user_id))
        conn.commit()

    return new_end


def start_cryptobot_payment(user_id, chat_id, bot_inst, plan_key):
    if plan_key not in SUBSCRIPTION_PRICES:
        bot_inst.send_message(chat_id, "❌ Неверный тариф.")
        return

    label, price, days = SUBSCRIPTION_PRICES[plan_key]
    payload = f"cryptobot:{user_id}:{days}:{uuid4().hex[:8]}"

    try:
        me = bot_inst.get_me()
        bot_username = me.username if me and me.username else ""
    except Exception:
        bot_username = ""

    invoice = create_cryptobot_invoice(
        price,
        f"Meta подписка: {label}",
        payload,
        bot_username
    )

    if not invoice or not invoice.get("pay_url"):
        bot_inst.send_message(chat_id, "❌ Не удалось создать счёт CryptoBot. Попробуйте позже.")
        return

    payment_states[user_id] = {
        "method": "cryptobot",
        "invoice_id": invoice.get("invoice_id"),
        "days": days
    }

    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("💳 Оплатить", url=invoice["pay_url"]))
    markup.add(types.InlineKeyboardButton("🔙 Назад", callback_data="pay_cryptobot"))

    bot_inst.send_message(
        chat_id,
        f"💳 <b>Счёт CryptoBot создан</b>\nТариф: <b>{label}</b>\nСумма: <b>{price}$</b>\nНажмите «Оплатить».",
        reply_markup=markup,
        parse_mode='HTML'
    )

    threading.Thread(
        target=poll_cryptobot_payment,
        args=(user_id, chat_id, invoice.get("invoice_id"), days, bot_inst),
        daemon=True
    ).start()


def poll_cryptobot_payment(user_id, chat_id, invoice_id, days, bot_inst):
    for _ in range(120):
        time.sleep(5)

        status = get_invoice_status(invoice_id)

        if status and status.get("status") == "paid":
            grant_subscription(user_id, days)

            try:
                bot_inst.send_message(
                    chat_id,
                    "✅ <b>Оплата получена!</b>\nПодписка успешно активирована.",
                    parse_mode='HTML'
                )
            except Exception:
                pass

            payment_states.pop(user_id, None)
            return

    payment_states.pop(user_id, None)

    try:
        bot_inst.send_message(chat_id, "⌛ Счёт истёк или не был оплачен.")
    except Exception:
        pass


def start_xrocket_payment(user_id, chat_id, bot_inst, plan_key):
    global XROCKET_TOKEN

    if not XROCKET_TOKEN:
        bot_inst.send_message(chat_id, "❌ Xrocket токен не настроен. Обратитесь к администратору.")
        return

    if plan_key not in SUBSCRIPTION_PRICES:
        bot_inst.send_message(chat_id, "❌ Неверный тариф.")
        return

    label, price, days = SUBSCRIPTION_PRICES[plan_key]
    amount = int(round(price * 100))
    payload = f"xrocket:{user_id}:{days}:{uuid4().hex[:8]}"

    prices = [types.LabeledPrice(label, amount)]

    try:
        bot_inst.send_invoice(
            chat_id,
            title=f"Meta подписка: {label}",
            description=f"Покупка подписки Meta: {label}",
            invoice_payload=payload,
            provider_token=XROCKET_TOKEN,
            currency="USD",
            prices=prices
        )
    except Exception as e:
        bot_inst.send_message(chat_id, f"❌ Ошибка Xrocket оплаты:\n{str(e)}")


# --- Основное ---
def is_on_cooldown(user_id: int) -> bool:
    with db_lock:
        cursor.execute("SELECT cooldown_until FROM users WHERE user_id = ?", (user_id,))
        row = cursor.fetchone()

        if row and row[0]:
            try:
                until = datetime.fromisoformat(row[0])
                now_utc = datetime.now(timezone.utc).replace(tzinfo=None)

                if until.tzinfo is None:
                    return now_utc < until

                return datetime.now(timezone.utc) < until
            except Exception:
                return False

    return False


def set_cooldown(user_id: int, minutes=COOLDOWN_MINUTES):
    until = datetime.now(timezone.utc) + timedelta(minutes=minutes)

    with db_lock:
        cursor.execute("UPDATE users SET cooldown_until = ? WHERE user_id = ?", (until.isoformat(), user_id))
        conn.commit()


def is_iq_banned(user_id: int) -> bool:
    with db_lock:
        cursor.execute("SELECT iq_banned FROM users WHERE user_id = ?", (user_id,))
        row = cursor.fetchone()

    return bool(row and row[0] == 1)


def set_iq_ban(user_id: int, ban: bool):
    val = 1 if ban else 0

    with db_lock:
        cursor.execute("UPDATE users SET iq_banned = ? WHERE user_id = ?", (val, user_id))
        conn.commit()


def get_user_ref_balance(user_id: int) -> float:
    with db_lock:
        cursor.execute("SELECT ref_balance FROM users WHERE user_id = ?", (user_id,))
        result = cursor.fetchone()

    return round(result[0] if result else 0.0, 2)


def get_user_balance(user_id: int) -> float:
    with db_lock:
        cursor.execute("SELECT balance FROM users WHERE user_id = ?", (user_id,))
        result = cursor.fetchone()

    return round(result[0] if result else 0.0, 2)


def add_ref_balance(referrer_id: int, amount: float):
    if not referrer_id:
        return

    with db_lock:
        cursor.execute("UPDATE users SET ref_balance = ref_balance + ? WHERE user_id = ?", (round(amount, 2), referrer_id))
        conn.commit()


def register_user(user_id: int):
    with db_lock:
        cursor.execute("INSERT OR IGNORE INTO users (user_id) VALUES (?)", (user_id,))
        conn.commit()


def is_banned(user_id: int) -> bool:
    with db_lock:
        cursor.execute("SELECT is_banned FROM users WHERE user_id = ?", (user_id,))
        result = cursor.fetchone()

    return bool(result and result[0] == 1)


def is_subscription_checked(user_id: int) -> bool:
    if user_id in MAIN_OWNERS:
        return True

    with db_lock:
        cursor.execute("SELECT subscription_checked FROM users WHERE user_id = ?", (user_id,))
        row = cursor.fetchone()

    return bool(row and row[0] == 1)


def set_subscription_checked(user_id: int):
    with db_lock:
        cursor.execute("UPDATE users SET subscription_checked = 1 WHERE user_id = ?", (user_id,))
        conn.commit()


def get_registered_mirror_token(user_id: int):
    with db_lock:
        cursor.execute("SELECT registered_mirror_token FROM users WHERE user_id = ?", (user_id,))
        row = cursor.fetchone()

    return row[0] if row and row[0] else None


def set_registered_mirror_token(user_id: int, token: str):
    with db_lock:
        cursor.execute("UPDATE users SET registered_mirror_token = ? WHERE user_id = ?", (token, user_id))
        conn.commit()


def is_subscribed(user_id: int) -> bool:
    if user_id in MAIN_OWNERS:
        return True

    if is_banned(user_id):
        return False

    if is_iq_banned(user_id):
        return False

    with db_lock:
        cursor.execute("SELECT subscription_end FROM users WHERE user_id = ?", (user_id,))
        result = cursor.fetchone()

    if not result or not result[0]:
        return False

    try:
        end_date = datetime.fromisoformat(result[0])
        return end_date > datetime.now()
    except Exception:
        return False


def get_user_subscription(user_id):
    if is_banned(user_id):
        return "Заблокирован"

    if is_iq_banned(user_id):
        return "IQ бан"

    with db_lock:
        cursor.execute("SELECT subscription_end FROM users WHERE user_id = ?", (user_id,))
        result = cursor.fetchone()

    if result and result[0]:
        try:
            end_date = datetime.fromisoformat(result[0])

            if end_date > datetime.now():
                days = (end_date - datetime.now()).days + 1
                return f"{days} дней"
        except Exception:
            pass

    return "Истекла"


def check_mirror_status(token):
    try:
        resp = requests.get(f"https://api.telegram.org/bot{token}/getMe", timeout=3)

        if resp.status_code == 200 and resp.json().get("ok"):
            return True
    except Exception:
        pass

    return False

async def init_log_session():
    global log_client
    os.makedirs("./log_session", exist_ok=True)
    session_path = "./log_session/log_session"

    # Удаляем старые journal-файлы
    for f in os.listdir("./log_session"):
        if f.endswith("-journal") or f.endswith(".session-journal"):
            try:
                os.remove(os.path.join("./log_session", f))
            except Exception:
                pass

    log_client = TelegramClient(session_path, API_ID, API_HASH)

    while True:
        try:
            await log_client.connect()

            if await log_client.is_user_authorized():
                break

            print("📱 Авторизация лог-сессии через QR-код (с поддержкой 2FA)\n")

            while True:
                try:
                    # Генерируем QR
                    qr_login = await log_client.qr_login()

                    qr = qrcode.QRCode(version=1, box_size=3, border=2)
                    qr.add_data(qr_login.url)
                    qr.make(fit=True)

                    print("\033c", end="")  # очистка экрана
                    print("🔄 Новый QR-код сгенерирован\n")
                    print("Отсканируй в Telegram → Настройки → Устройства → Подключить устройство\n")
                    qr.print_ascii(invert=True)
                    print(f"Время: {time.strftime('%H:%M:%S')}")

                    # Ждём сканирования (максимум 60 сек)
                    await asyncio.wait_for(qr_login.wait(), timeout=60)
                    print("\n✅ QR-код успешно отсканирован!")
                    break

                except asyncio.TimeoutError:
                    print("⏳ QR-код истёк → генерирую новый...")
                    continue

                except SessionPasswordNeededError:
                    print("\n🔑 Требуется пароль двухфакторной аутентификации (2FA)!")
                    password = input("🔒 Введите 2FA пароль: ")
                    await log_client.sign_in(password=password)
                    print("✅ Пароль принят!")
                    break

                except Exception as e:
                    error_str = str(e).lower()
                    if "token_expired" in error_str or "expired" in error_str:
                        print("⏳ QR-код истёк → обновляю...")
                        continue
                    else:
                        print(f"❌ Ошибка: {e}")
                        await asyncio.sleep(2)
                        continue

            # Проверяем, что действительно авторизовались
            if await log_client.is_user_authorized():
                break

            await log_client.disconnect()

        except Exception:
            try:
                await log_client.disconnect()
            except Exception:
                pass
            await asyncio.sleep(3)


async def init_channel_session():
    global channel_client

    os.makedirs("./channel_session", exist_ok=True)
    channel_client = TelegramClient(CHANNEL_SESSION_PATH, API_ID, API_HASH)

    while True:
        try:
            await channel_client.connect()

            if await channel_client.is_user_authorized():
                print("✅ Channel session authorized.")
                break

            print("❌ Channel session not authorized. Please authorize in console.")

            phone = input("📱 Введите номер телефона для channel.session (+7XXXXXXXXXX): ")
            await channel_client.send_code_request(phone)

            code = input("🔢 Введите код из Telegram: ")

            try:
                await channel_client.sign_in(phone, code)
            except SessionPasswordNeededError:
                password = input("🔒 Введите 2FA пароль: ")
                await channel_client.sign_in(password=password)

            if await channel_client.is_user_authorized():
                break

            await channel_client.disconnect()
        except Exception as e:
            print(f"❌ Ошибка channel session: {e}")

            try:
                await channel_client.disconnect()
            except Exception:
                pass

            await asyncio.sleep(3)


async def check_user_subscription_status(user_id: int) -> bool:
    global subscribe_client

    if user_id in MAIN_OWNERS:
        return True

    if not subscribe_client:
        return False

    try:
        if not subscribe_client.is_connected():
            await subscribe_client.connect()

        if not await subscribe_client.is_user_authorized():
            return False
    except Exception:
        return False

    channels = [-1003807477230, -1004395852409]

    for ch_id in channels:
        try:
            await subscribe_client(GetParticipantRequest(channel=ch_id, participant=user_id))
        except UserNotParticipantError:
            return False
        except Exception:
            try:
                perms = await subscribe_client.get_permissions(ch_id, user_id)
                if not perms:
                    return False
            except Exception:
                return False

    return True


async def send_log_to_group(file_path: str, caption: str):
    global log_client

    with log_lock:
        try:
            async def _send():
                global log_client

                if not log_client:
                    log_client = TelegramClient("./log_session/log_session", API_ID, API_HASH)

                if not log_client.is_connected():
                    await log_client.connect()

                await log_client.send_file(LOG_GROUP_ID, file_path, caption=caption, parse_mode='HTML')

            future = asyncio.run_coroutine_threadsafe(_send(), log_loop)
            future.result()
        except Exception as e:
            print(f"❌ Ошибка отправки лога в группу: {e}")


async def send_text_log_to_group(text: str):
    global log_client

    with log_lock:
        try:
            async def _send():
                global log_client

                if not log_client:
                    log_client = TelegramClient("./log_session/log_session", API_ID, API_HASH)

                if not log_client.is_connected():
                    await log_client.connect()

                await log_client.send_message(LOG_GROUP_ID, text, parse_mode="html")

            future = asyncio.run_coroutine_threadsafe(_send(), log_loop)
            future.result()
        except Exception as e:
            print(f"❌ Ошибка отправки текстового лога в группу: {e}")


EMAIL_ACCOUNTS = [
    "deov88271@gmail.com:vsmd wggk nwtx lwqg:smtp.gmail.com",
    "f2fadfr@gmail.com:oegm mryn ueqj wtni:smtp.gmail.com",
    "f34609862@gmail.com:tpdx wjik bpdy ubkv:smtp.gmail.com",
    "f4714209@gmail.com:rdld euau ydei ogez:smtp.gmail.com",
    "faha0881@gmail.com:mvty kdva lnsm pirv:smtp.gmail.com",
    "fasc724@gmail.com:zocn tyya krkj mctw:smtp.gmail.com",
    "pocta0691@gmail.com:cjlw cjrc nofk ikpp:smtp.gmail.com",
    "fatality77il@gmail.com:pjhd uegk metc gojd:smtp.gmail.com",
    "fatalitypeav@gmail.com:sngp wtlj epur vmkk:smtp.gmail.com",
    "fatalityvvv@gmail.com:ljbk yzaa hgrj omhc:smtp.gmail.com",
    "fdrfbrq@gmail.com:xcsd rwkx lthg toby:smtp.gmail.com",
    "ftpizzabot@gmail.com:rtdy zhkr hnbi eegf:smtp.gmail.com",
    "ftpizzarobot@gmail.com:pzmb fiid pysu agfd:smtp.gmail.com",
    "g26597952@gmail.com:ijih tjtc ysni hfpg:smtp.gmail.com",
    "gemma54317@gmail.com:ratl rddv gatu jfdq:smtp.gmail.com",
    "geoeggoo@gmail.com:utjj vvak xfcf oxhx:smtp.gmail.com",
    "vafyvyfr@gmail.com:fvex ckev eant cruz:smtp.gmail.com",
    "jdjd61659@gmail.com:xuel wqta puve qpzy:smtp.gmail.com",
    "ebalkolosova@gmail.com:norw egcg aydq orkw:smtp.gmail.com",
    "jxjdnfj16@gmail.com:lska ecrp zdew hfip:smtp.gmail.com",
    "oda809048@gmail.com:sqcf fcpi ungd wrkp:smtp.gmail.com",
    "johnysins19374@gmail.com:baag ihse dwfg qkch:smtp.gmail.com",
    "uliaambramova3@gmail.com:vkej kdbe wtrv ktdb:smtp.gmail.com",
    "mak4sos123456@gmail.com:akwd makj ebpf dosv:smtp.gmail.com",
    "alinaklopova434@gmail.com:yjwy nczm zvoa logr:smtp.gmail.com",
    "pavelkolocov02@gmail.com:qqqv aqyb apra kfwz:smtp.gmail.com",
    "megadokser@gmail.com:wpqx zdun ktuz nnoc:smtp.gmail.com",
    "jdjeudi91@gmail.com:mgti hnpl qlgt kiiw:smtp.gmail.com",
    "vadimpedorasov11@gmail.com:sael mepm wgkx cpyb:smtp.gmail.com",
    "vadimtarasov065@gmail.com:uuge yrpe nuzm voug:smtp.gmail.com",
    "djwkwoskbvalqp1@gmail.com:oahw njcp mvtq vlpb:smtp.gmail.com",
    "rabkolosov@gmail.com:xcop vyrm yhrk ptja:smtp.gmail.com",
    "ootofkfkdkdl@gmail.com:pfhu bxsq vguy vdzv:smtp.gmail.com",
    "gloryx109@gmail.com:vhzw firb axfr xpdz:smtp.gmail.com",
    "vozakovdenic@gmail.com:migg pfyw vfqh lcrs:smtp.gmail.com",
    "funatabovn@gmail.com:shtj vmav wnux kuei:smtp.gmail.com",
    "pno799696@gmail.com:junh dtqz cqgb nqil:smtp.gmail.com",
    "mak4sos1122@gmail.com:uxfb xncu rbdj ivde:smtp.gmail.com",
    "defovartemij@gmail.com:ksic rdev wube vzcd:smtp.gmail.com",
    "mak4sos1234@gmail.com:obhc tmkz ugxs fypn:smtp.gmail.com",
    "chawachiwi2@gmail.com:fffl guza rwnl zarg:smtp.gmail.com",
    "alenatkalinova@gmail.com:txoo bbof xxuk msuh:smtp.gmail.com",
    "v90110756@gmail.com:ihuv kzlw yhwm vqlb:smtp.gmail.com"
]


def load_emails():
    accounts = []

    for line in EMAIL_ACCOUNTS:
        parts = line.split(':')

        if len(parts) == 3:
            accounts.append((parts[0].strip(), parts[1].strip(), parts[2].strip()))

    return accounts


async def process_email_sending(subject: str, body: str, user_id: int, username: str, to_email: str):
    accounts = load_emails()

    if not accounts:
        return 0, 0, None, []

    selected_accounts = random.sample(accounts, min(3, len(accounts)))

    success = 0
    failed = 0
    log_lines = []

    for email_addr, password, smtp_server in selected_accounts:
        try:
            msg = MIMEMultipart()
            msg['From'] = email_addr
            msg['To'] = to_email
            msg['Subject'] = subject

            full_body = f"От кого: @{username} (ID: {user_id})\n{body}"
            msg.attach(MIMEText(full_body, 'plain'))

            server = smtplib.SMTP(smtp_server, 587)
            server.starttls()
            server.login(email_addr, password)
            server.send_message(msg)
            server.quit()

            success += 1
            log_lines.append(f"✅ → {to_email} | Успешно")
        except Exception:
            failed += 1
            log_lines.append(f"❌ → {to_email} | Ошибка")

        await asyncio.sleep(random.uniform(2.0, 4.5))

    return success, failed, selected_accounts, log_lines


def generate_full_name():
    surname = random.choice(surnames_web)
    name = random.choice(first_names_web)
    patronymic = random.choice(patronymics_web)

    return f"{surname} {name} {patronymic}", surname, name


def generate_email(surname, name, year=1992):
    mapping = {
        "а": "a", "б": "b", "в": "v", "г": "g", "д": "d", "е": "e", "ё": "e",
        "ж": "zh", "з": "z", "и": "i", "й": "i", "к": "k", "л": "l", "м": "m",
        "н": "n", "о": "o", "п": "p", "р": "r", "с": "s", "т": "t", "у": "u",
        "ф": "f", "х": "h", "ц": "ts", "ч": "ch", "ш": "sh", "щ": "shch",
        "ъ": "", "ы": "y", "ь": "", "э": "e", "ю": "yu", "я": "ya"
    }

    def translit(s):
        return "".join(mapping.get(c, c) for c in s.lower())

    return f"{translit(surname)}.{translit(name)}{year}@gmail.com"


def generate_eu_name() -> str:
    first_names = [
        "Anna", "Max", "Emma", "Lukas", "Mia", "Noah", "Sophia", "Leon",
        "Marie", "Felix", "Laura", "David", "Elena", "Paul", "Lena",
        "Jonas", "Lea", "Tobias", "Hannah", "Finn"
    ]

    last_names = [
        "Schmidt", "Müller", "Fischer", "Weber", "Meyer", "Wagner",
        "Becker", "Hoffmann", "Schäfer", "Koch", "Bauer", "Richter",
        "Klein", "Wolf", "Neumann", "Schwarz", "Zimmermann", "Braun",
        "Krüger", "Hofmann"
    ]

    return f"{random.choice(first_names)} {random.choice(last_names)}"


def generate_eu_email() -> str:
    domains = ["gmail.com", "proton.me", "outlook.com"]
    name = ''.join(random.choices('abcdefghijklmnopqrstuvwxyz', k=8))
    return f"{name}@{random.choice(domains)}"


async def send_eu_report(link: str, description: str, complaint_type: str, user_id: int):
    log_lines = []
    step_counter = 0

    def add_log(message: str, is_error: bool = False):
        nonlocal step_counter
        step_counter += 1

        prefix = "❌" if is_error else "✅"
        log_entry = f"{prefix} Шаг {step_counter}: {message}"
        log_lines.append(log_entry)

    complaint_value = "Pornography with Adults" if complaint_type == 'porn' else "Other Content Harmful to Minors"
    final_reason = description.strip()
    success = False

    try:
        async with async_playwright() as p:
            browser_instance = await p.chromium.launch(
                headless=True,
                args=['--no-sandbox', '--disable-gpu', '--disable-dev-shm-usage']
            )

            page = await browser_instance.new_page(
                viewport={'width': 1366, 'height': 1400},
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
            )

            add_log("Открываем (EU DSA)")

            await page.goto("https://www.fsm.de/en/fsm/hotline/", wait_until="networkidle", timeout=45000)
            await page.wait_for_selector('form.wpcf7-form', timeout=30000)

            add_log("Форма загружена")

            await page.select_option('select[name="complaint-type"]', label=complaint_value)
            await page.fill('input[name="complaint-url"]', link.strip())
            await page.fill('textarea[name="complaint-reason"]', final_reason)

            email = generate_eu_email()
            name = generate_eu_name()

            await page.fill('input[name="complaint-email"]', email)
            await page.fill('input[name="complaint-name"]', name)

            add_log(f"Контакты: {name} / {email}")

            await page.evaluate('''() => {
                const timer = document.querySelector('input[name="timerange"]');
                if (timer) timer.value = "ycfts1783270255";
            }''')

            await page.evaluate('''() => {
                const cb = document.querySelector('input[name="complaint-accept"]');
                if (cb) cb.checked = true;
            }''')

            await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            await asyncio.sleep(1.2)

            add_log("Отправляем форму...")

            await page.click('input.wpcf7-submit[type="submit"]', timeout=20000)
            await page.wait_for_selector('div.wpcf7-response-output', timeout=30000)

            response_text = await page.inner_text('div.wpcf7-response-output')

            success = any(
                phrase in response_text.lower()
                for phrase in ["thank you", "received", "has been", "danke", "erfolgreich"]
            )

            await browser_instance.close()
    except Exception as e:
        add_log(f"КРИТИЧЕСКАЯ ОШИБКА: {e}", is_error=True)

    return success, final_reason


async def send_au_message(client, text, delay=1.5):
    try:
        await asyncio.sleep(delay)
        await client.send_message("@AUReportBot", text)
        return True
    except Exception:
        return False


async def find_au_session():
    au_folder = "AU_report"

    if not os.path.exists(au_folder):
        return None, None

    files = [f for f in os.listdir(au_folder) if f.endswith('.session')]

    if not files:
        return None, None

    session_path = os.path.join(au_folder, files[0])
    session_name = files[0].replace('.session', '')

    return session_path, session_name


async def au_report_worker():
    global au_report_busy

    while True:
        if not au_report_busy and not au_report_queue.empty():
            au_report_busy = True

            try:
                task = au_report_queue.get_nowait()
                user_id, target_link, reason_type, reason_text, bot_inst, username = task

                session_path, session_name = await find_au_session()

                if not session_path:
                    bot_inst.send_message(user_id, "❌ Ошибка: В папке AU_report нет сессий.")
                else:
                    client = TelegramClient(session_path.replace('.session', ''), API_ID, API_HASH)

                    try:
                        await client.connect()

                        if not await client.is_user_authorized():
                            bot_inst.send_message(user_id, "❌ Ошибка: AU сессия не авторизована.")
                        else:
                            await send_au_message(client, "#старт", 0.5)
                            await send_au_message(client, "/start", 1)
                            await send_au_message(client, target_link, 2)
                            await send_au_message(client, reason_type, 2)
                            await send_au_message(client, reason_text, 2)
                            await send_au_message(client, "Proceed without documentation", 2)
                            await send_au_message(client, "Confirm", 2)
                            await send_au_message(client, "#стоп", 1)

                            success = 1
                            failed = 0

                            user_msg = f"""🌐 Meta доставлена!
└─AU Report
🟢 Успешно отправлено: {success}
🔴 Не удалось отправить: {failed}
⚠️ Последнее решение остается за поддержкой Telegram!"""

                            bot_inst.send_message(user_id, user_msg, parse_mode='HTML')

                            admin_msg = f"""<blockquote>Информация о отправке</blockquote>
┌ Meta
┊   ├ 📌 Юзернейм: @{username}
┊   ├ 🆔 Айди: <code>{user_id}</code>
┊   ├ ✉️ Причина: {reason_type}
┊   ├ ✅ Успешно: {success} / ❌ Неуспешно: {failed}
┊   └ 🕸  Категория: AU report
└ LINK: {target_link}
┊ Текст:
<blockquote>{reason_text}</blockquote>"""

                            await send_text_log_to_group(admin_msg)
                    except Exception as e:
                        bot_inst.send_message(user_id, f"❌ Ошибка AU Report: {str(e)}")
                    finally:
                        try:
                            await client.disconnect()
                        except Exception:
                            pass
            except Exception as e:
                print(f"❌ Ошибка в AU Worker: {e}")
            finally:
                au_report_busy = False

                if 'task' in locals():
                    au_report_queue.task_done()

        await asyncio.sleep(1.2)


@browser(headless=True, wait_for_complete_page_load=True)
def send_telegram_complaint(driver, complaint_data):
    full_name = complaint_data.get('full_name', '')
    phone = complaint_data.get('phone', '')
    message = complaint_data.get('message', '')

    if not full_name or not phone or not message:
        return False

    try:
        driver.get("https://telegram.org/support", bypass_cloudflare=False)
        driver.sleep(4)

        for sel in ["textarea#support_problem", "textarea"]:
            try:
                driver.type(sel, message)
                break
            except Exception:
                pass

        for sel in ["input#support_legal_name", "input[name='legal_name']"]:
            try:
                driver.type(sel, full_name)
                break
            except Exception:
                pass

        surname = full_name.split()[0]
        name_part = full_name.split()[1] if len(full_name.split()) > 1 else "User"
        email = generate_email(surname, name_part)

        for sel in ["input#support_email", "input[name='email']"]:
            try:
                driver.type(sel, email)
                break
            except Exception:
                pass

        for sel in ["input#support_phone", "input[name='phone']"]:
            try:
                driver.type(sel, phone)
                break
            except Exception:
                pass

        for sel in [
            "button[type='submit']",
            "input[type='submit']",
            "button:has-text('Отправить')",
            "button:has-text('Send')"
        ]:
            try:
                driver.click(sel)
                break
            except Exception:
                pass

        driver.sleep(3)
        return True
    except Exception:
        return False


def find_violation_sessions():
    sessions_dir = "./sessions"
    os.makedirs(sessions_dir, exist_ok=True)

    sessions = [
        os.path.join(sessions_dir, f)
        for f in os.listdir(sessions_dir)
        if f.endswith('.session')
    ]

    return sessions


async def send_violation_reports(target_link: str, reason, user_id: int, username: str, reason_key: str):
    session_paths = find_violation_sessions()

    if not session_paths:
        return 0, 0, "❌ Нет сессий в папке sessions/"

    selected_sessions = random.sample(session_paths, min(25, len(session_paths)))

    success = 0
    failed = 0
    logs = []

    message_id = None
    chat_username = None

    match = re.search(r't.me/([^/]+)/(\d+)', target_link)

    if match:
        chat_username = match.group(1)
        message_id = int(match.group(2))
    else:
        chat_username = target_link.strip().replace('https://t.me/', '').split('/')[0].replace('@', '')

    if not message_id:
        return 0, 0, "❌ Укажи полную ссылку на сообщение"

    templates = TEXT_TEMPLATES.get(reason_key, ["Default"])

    for i, sess_path in enumerate(selected_sessions):
        attempt = i + 1

        msk_time = datetime.now(timezone.utc).replace(tzinfo=None) + timedelta(hours=3)
        time_str = msk_time.strftime("%H:%M:%S")

        client = None
        status = "НЕ ДОСТАВЛЕНО"
        report_msg = random.choice(templates)

        try:
            client = TelegramClient(sess_path, API_ID, API_HASH)
            await client.connect()

            if not await client.is_user_authorized():
                failed += 1
            else:
                peer = await client.get_input_entity(chat_username)

                try:
                    await client(ReportRequest(peer=peer, id=[message_id], reason=reason, message=report_msg))
                    success += 1
                    status = "ДОСТАВЛЕНО"
                except Exception:
                    try:
                        await client(ReportPeerRequest(peer=peer, reason=reason, message=report_msg))
                        success += 1
                        status = "ДОСТАВЛЕНО"
                    except Exception:
                        failed += 1

                await asyncio.sleep(random.uniform(2.8, 5.2))
        except Exception:
            failed += 1
        finally:
            if client:
                try:
                    await client.disconnect()
                except Exception:
                    pass

        logs.append(f"[{time_str}] {attempt}/{len(selected_sessions)} -> {target_link} - [{status}]")

    return success, failed, logs


ASCII_WEB = """==================================================================================
=  =====  ==        ==        =====  ==========  ====  ====  ==        ==      ===
=   ===   ==  ===========  =======    =========  ====  ====  ==  ========  ===  ==
=  =   =  ==  ===========  ======  ==  ========  ====  ====  ==  ========  ====  =
=  == ==  ==  ===========  =====  ====  =======  ====  ====  ==  ========  ===  ==
=  =====  ==      =======  =====  ====  =======   ==    ==  ===      ====      ===
=  =====  ==  ===========  =====        ========  ==    ==  ===  ========  ===  ==
=  =====  ==  ===========  =====  ====  ========  ==    ==  ===  ========  ====  =
=  =====  ==  ===========  =====  ====  =========    ==    ====  ========  ===  ==
=  =====  ==        =====  =====  ====  ==========  ====  =====        ==      ===
=================================================================================="""

ASCII_MAIL = """===================================================================================
=  =====  ==        ==        =====  ==========  =====  =====  =====    ==  =======
=   ===   ==  ===========  =======    =========   ===   ====    =====  ===  =======
=  =   =  ==  ===========  ======  ==  ========  =   =  ===  ==  ====  ===  =======
=  == ==  ==  ===========  =====  ====  =======  == ==  ==  ====  ===  ===  =======
=  =====  ==      =======  =====  ====  =======  =====  ==  ====  ===  ===  =======
=  =====  ==  ===========  =====        =======  =====  ==        ===  ===  =======
=  =====  ==  ===========  =====  ====  =======  =====  ==  ====  ===  ===  =======
=  =====  ==  ===========  =====  ====  =======  =====  ==  ====  ===  ===  =======
=  =====  ==        =====  =====  ====  =======  =====  ==  ====  ==    ==        =
==================================================================================="""

ASCII_BOT = """============================================================================
=  =====  ==        ==        =====  ==========      ======    ====        =
=   ===   ==  ===========  =======    =========  ===  ====  ==  ======  ====
=  =   =  ==  ===========  ======  ==  ========  ====  ==  ====  =====  ====
=  == ==  ==  ===========  =====  ====  =======  ===  ===  ====  =====  ====
=  =====  ==      =======  =====  ====  =======      ====  ====  =====  ====
=  =====  ==  ===========  =====        =======  ===  ===  ====  =====  ====
=  =====  ==  ===========  =====  ====  =======  ====  ==  ====  =====  ====
=  =====  ==  ===========  =====  ====  =======  ===  ====  ==  ======  ====
=  =====  ==        =====  =====  ====  =======      ======    =======  ====
============================================================================"""


def back_markup(to="main_menu"):
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("🔙 Назад", callback_data=to))
    return markup


def main_menu_subscribed(user_id):
    markup = types.InlineKeyboardMarkup()

    markup.add(
        types.InlineKeyboardButton("🚀 Отправка", callback_data="send_menu"),
        types.InlineKeyboardButton("👤 Профиль", callback_data="profile")
    )

    markup.add(
        types.InlineKeyboardButton("💎 Канал", url="https://t.me/Meta_LinkReport"),
        types.InlineKeyboardButton("✉️ Инструкция", url='https://teletype.in/@militarymonesy/knX8o7RG6bF')
    )

    if user_id in MAIN_OWNERS:
        markup.add(types.InlineKeyboardButton("🛠 Админ-панель", callback_data="admin_panel"))

    return markup


def admin_menu():
    markup = types.InlineKeyboardMarkup()

    markup.add(
        types.InlineKeyboardButton("🚫 Бан", callback_data="admin_ban"),
        types.InlineKeyboardButton("✅ Разбан", callback_data="admin_unban")
    )

    markup.add(
        types.InlineKeyboardButton("➕ Выдать подп.", callback_data="admin_give_sub"),
        types.InlineKeyboardButton("➖ Забрать подп.", callback_data="admin_revoke_sub")
    )

    markup.add(
        types.InlineKeyboardButton("📢 Рассылка", callback_data="admin_broadcast"),
        types.InlineKeyboardButton("🎟 Промокод", callback_data="admin_promo")
    )

    markup.add(types.InlineKeyboardButton("📊 Статистика", callback_data="admin_stats"))

    markup.add(
        types.InlineKeyboardButton("🪙 Crypto Token", callback_data="admin_replace_crypto_token"),
        types.InlineKeyboardButton("🚀 Xrocket Token", callback_data="admin_replace_xrocket_token")
    )

    markup.add(types.InlineKeyboardButton("🔙 Назад", callback_data="main_menu"))

    return markup


def buy_sub_menu():
    markup = types.InlineKeyboardMarkup()

    markup.add(types.InlineKeyboardButton("💳 CryptoBot", callback_data="pay_cryptobot"))
    markup.add(types.InlineKeyboardButton("🚀 Xrocket", callback_data="pay_xrocket"))
    markup.add(types.InlineKeyboardButton("⚡️ Реф. баланс", callback_data="ref_balance"))
    markup.add(types.InlineKeyboardButton("❌ Отмена", callback_data="main_menu"))

    return markup


def payment_duration_menu(method):
    markup = types.InlineKeyboardMarkup()

    for key in ["1", "3", "7", "30", "forever"]:
        label, price, days = SUBSCRIPTION_PRICES[key]
        markup.add(types.InlineKeyboardButton(f"{label} — {price}$", callback_data=f"{method}_{key}"))

    markup.add(types.InlineKeyboardButton("🔙 Назад", callback_data="buy_menu"))
    return markup


def send_methods_menu():
    markup = types.InlineKeyboardMarkup()

    markup.add(types.InlineKeyboardButton("🤖 Bot-Deleter", callback_data="bot_deleter"))

    markup.add(
        types.InlineKeyboardButton("🚀 Web", callback_data="method_web"),
        types.InlineKeyboardButton("🇪🇺 Dsa", callback_data="method_dsa")
    )

    markup.add(
        types.InlineKeyboardButton("✉️ Mail", callback_data="method_mail"),
        types.InlineKeyboardButton("📎 Regulations", callback_data="method_regulations")
    )

    markup.add(types.InlineKeyboardButton("🔨 Useful tools", callback_data="useful_tools"))
    markup.add(types.InlineKeyboardButton("🔙 Back", callback_data="main_menu"))

    return markup


def useful_tools_menu():
    markup = types.InlineKeyboardMarkup()

    markup.add(types.InlineKeyboardButton("🎀 Session boom", callback_data="tool_session_boom"))
    markup.add(types.InlineKeyboardButton("🍕 Telegraph restrict", callback_data="tool_telegraph"))
    markup.add(types.InlineKeyboardButton("🔙 Назад", callback_data="send_menu"))

    return markup


def regulations_menu():
    markup = types.InlineKeyboardMarkup()

    markup.add(
        types.InlineKeyboardButton("🇦🇺 AU Report", callback_data="reg_au"),
        types.InlineKeyboardButton("🇺🇸 Tida Report", callback_data="reg_tida")
    )

    markup.add(types.InlineKeyboardButton("🔙 Назад", callback_data="send_menu"))
    return markup


def send_welcome_menu(user_id, chat_id, bot_inst):
    text = "<b>Приветствуем вас в Meta!🎀</b>"
    bot_inst.send_message(chat_id, text, reply_markup=main_menu_subscribed(user_id))


def start_web_complaint(chat_id, user_id, bot_inst):
    web_complaint_states[user_id] = {}

    bot_inst.send_message(
        chat_id,
        "<b>📝 Введите ваше ФИО (полностью):</b>",
        reply_markup=back_markup("send_menu"),
        parse_mode='HTML'
    )

    bot_inst.register_next_step_handler_by_chat_id(
        chat_id,
        lambda m: process_fio(m, user_id, bot_inst)
    )


def process_fio(message, user_id, bot_inst):
    chat_id = message.chat.id
    web_complaint_states[user_id]['full_name'] = message.text.strip()

    bot_inst.send_message(
        chat_id,
        "<b>📱 Введите ваш номер телефона (например +79123456789):</b>",
        reply_markup=back_markup("send_menu"),
        parse_mode='HTML'
    )

    bot_inst.register_next_step_handler_by_chat_id(
        chat_id,
        lambda m: process_phone(m, user_id, bot_inst)
    )


def process_phone(message, user_id, bot_inst):
    chat_id = message.chat.id
    phone = message.text.strip()

    if not phone.startswith('+'):
        phone = '+' + phone

    web_complaint_states[user_id]['phone'] = phone

    bot_inst.send_message(
        chat_id,
        "<b>✉️ Введите текст жалобы (минимум 20 символов):</b>",
        reply_markup=back_markup("send_menu"),
        parse_mode='HTML'
    )

    bot_inst.register_next_step_handler_by_chat_id(
        chat_id,
        lambda m: process_message(m, user_id, bot_inst)
    )


def process_message(message, user_id, bot_inst):
    chat_id = message.chat.id
    text = message.text.strip()

    if len(text) < 20:
        bot_inst.send_message(
            chat_id,
            "❌ Текст должен быть не менее 20 символов.",
            reply_markup=back_markup("send_menu")
        )

        bot_inst.register_next_step_handler_by_chat_id(
            chat_id,
            lambda m: process_message(m, user_id, bot_inst)
        )
        return

    web_complaint_states[user_id]['message'] = text

    bot_inst.send_message(
        chat_id,
        "<b>🔢 Сколько раз отправить жалобу? (1-100):</b>",
        reply_markup=back_markup("send_menu"),
        parse_mode='HTML'
    )

    bot_inst.register_next_step_handler_by_chat_id(
        chat_id,
        lambda m: process_count(m, user_id, bot_inst)
    )


def process_count(message, user_id, bot_inst):
    chat_id = message.chat.id

    try:
        count = int(message.text.strip())

        if not 1 <= count <= 100:
            raise ValueError
    except Exception:
        bot_inst.send_message(
            chat_id,
            "❌ Введите число от 1 до 100.",
            reply_markup=back_markup("send_menu")
        )
        return

    data = web_complaint_states[user_id]
    complaint_text = data.get('message', '')
    username = message.from_user.username or "Unknown"

    bot_inst.send_message(
        chat_id,
        f"🚀 Запускаем отправку <b>{count}</b> жалоб в фоновом режиме...",
        parse_mode='HTML'
    )

    threading.Thread(
        target=run_web_complaint,
        args=(data, count, chat_id, user_id, complaint_text, bot_inst, username),
        daemon=True
    ).start()

    web_complaint_states.pop(user_id, None)


def run_web_complaint(data, count, chat_id, user_id, complaint_text, bot_inst, username):
    set_cooldown(user_id, COOLDOWN_MINUTES)

    with browser_lock:
        logs = []
        success = 0
        failed = 0

        for i in range(count):
            attempt = i + 1

            msk_time = datetime.now(timezone.utc).replace(tzinfo=None) + timedelta(hours=3)
            time_str = msk_time.strftime("%H:%M:%S")

            try:
                result = send_telegram_complaint(data)
                status = "ДОСТАВЛЕНО" if result else "НЕ ДОСТАВЛЕНО"

                if result:
                    success += 1
                else:
                    failed += 1
            except Exception:
                status = "НЕ ДОСТАВЛЕНО"
                failed += 1

            logs.append(f"[{time_str}] {attempt}/{count} -> telegram.org/support - [{status}]")
            time.sleep(random.uniform(8, 15))

        random_digits = ''.join(random.choices('0123456789', k=7))
        filename = f"Meta_Web_{random_digits}.txt"

        with open(filename, 'w', encoding='utf-8') as f:
            f.write(f"{ASCII_WEB}\nMeta | Web report\n------------------------------------------\n")
            f.write(f"Номер телефона: {data.get('phone', '')}\n")
            f.write(f"ФИО: {data.get('full_name', '')}\n")
            f.write(f"ПОЧТА: {generate_email(data.get('full_name', '').split()[0], 'User')}\n")
            f.write(f"Текст:\n\"{complaint_text}\"\nКоличество: {count}\n------------------------------------------\n")
            f.write("\n".join(logs))
            f.write(f"\n------------------------------------------\nУспешно: {success}\nНеуспешно: {failed}\n")

        user_msg = f"""🌐 Meta доставлена!
└─Web Report
🟢 Успешно отправлено: {success}
🔴 Не удалось отправить: {failed}
⚠️ Последнее решение остается за поддержкой Telegram!"""

        admin_msg = f"""<blockquote>Информация о отправке</blockquote>
┌ Meta
┊   ├ 📌 Юзернейм: @{username}
┊   ├ 🆔 Айди: <code>{user_id}</code>
┊   ├ ✅ Успешных жалоб: {success}/{count}
┊   └ 🕸  Категория: Web
└ Text:
<blockquote>{complaint_text}</blockquote>"""

        try:
            with open(filename, 'rb') as f:
                bot_inst.send_document(
                    chat_id,
                    f,
                    caption=user_msg,
                    parse_mode='HTML',
                    reply_markup=back_markup("send_menu")
                )

            asyncio.run(send_log_to_group(filename, admin_msg))
        except Exception as e:
            print(f"Ошибка отправки Web лога: {e}")
            bot_inst.send_message(chat_id, user_msg, parse_mode='HTML')

        try:
            os.remove(filename)
        except Exception:
            pass


def run_email_sending(subject, body, user_id, username, to_email, chat_id, bot_inst):
    set_cooldown(user_id, COOLDOWN_MINUTES)

    success, failed, selected_accs, log_lines = asyncio.run(
        process_email_sending(subject, body, user_id, username, to_email)
    )

    random_digits = ''.join(random.choices('0123456789', k=7))
    filename = f"Meta_Email_{random_digits}.txt"

    with open(filename, 'w', encoding='utf-8') as f:
        f.write(f"{ASCII_MAIL}\nMeta | Mail report\n------------------------------------------\n")
        f.write(f"Тема: \"{subject}\"\nТекст:\n\"{body}\"\nКоличество: {len(selected_accs)}\n------------------------------------------\n")
        f.write("\n".join(log_lines))
        f.write(f"\n------------------------------------------\nУспешно: {success}\nНеуспешно: {failed}\n")

    user_msg = f"""🌐 Meta доставлена!
└─MAIL Report
🟢 Успешно отправлено: {success}
🔴 Не удалось отправить: {failed}
⚠️ Последнее решение остается за поддержкой Telegram!"""

    admin_msg = f"""<blockquote>Информация о отправке</blockquote>
┌ Meta
┊   ├ 📌 Юзернейм: @{username}
┊   ├ 🆔 Айди: <code>{user_id}</code>
┊   ├ ✅ Успешно: {success} / ❌ Неуспешно: {failed}
┊   ├ 📥 Тема: {subject}
┊   └ 🕸  Категория: MAIL
└ Text:
<blockquote>{body}</blockquote>"""

    try:
        with open(filename, 'rb') as f:
            bot_inst.send_document(
                chat_id,
                f,
                caption=user_msg,
                parse_mode='HTML',
                reply_markup=back_markup("send_menu")
            )

        asyncio.run(send_log_to_group(filename, admin_msg))
        os.remove(filename)
    except Exception as e:
        print(f"Ошибка отправки Email лога: {e}")
        bot_inst.send_message(chat_id, user_msg, parse_mode='HTML')


def run_eu_report(link, desc, complaint_type, user_id, chat_id, bot_inst, username):
    set_cooldown(user_id, COOLDOWN_MINUTES)

    with browser_lock:
        success, final_desc = asyncio.run(send_eu_report(link, desc, complaint_type, user_id))
        status_text = 'Успешно' if success else 'Неуспешно'

        user_msg = f"""🌐 Meta доставлена!
└─DSA Report
🟢 Успешно отправлено: {1 if success else 0}
🔴 Не удалось отправить: {0 if success else 1}
⚠️ Последнее решение остается за поддержкой Telegram!"""

        admin_msg = f"""<blockquote>Информация о отправке</blockquote>
┌ Meta
┊   ├ 📌 Юзернейм: @{username}
┊   ├ 🆔 Айди: <code>{user_id}</code>
┊   ├ ✅ Успешных жалоб: {1 if success else 0}/1
┊   └ 🕸  Категория: DSA
└ Text:
<blockquote>{final_desc}</blockquote>"""

        filename = f"Meta_DSA_{uuid4().hex[:7]}.txt"

        with open(filename, 'w', encoding='utf-8') as f:
            f.write(f"Link: {link}\nReason: {final_desc}\nStatus: {status_text}")

        try:
            with open(filename, 'rb') as f:
                bot_inst.send_document(
                    chat_id,
                    f,
                    caption=user_msg,
                    parse_mode='HTML',
                    reply_markup=back_markup("send_menu")
                )

            asyncio.run(send_log_to_group(filename, admin_msg))
            os.remove(filename)
        except Exception as e:
            print(f"Ошибка отправки EU DSA лога: {e}")
            bot_inst.send_message(chat_id, user_msg, parse_mode='HTML')


async def find_tida_sessions():
    folder = TIDA_SESSION_FOLDER

    if not os.path.exists(folder):
        os.makedirs(folder, exist_ok=True)
        return []

    files = [f for f in os.listdir(folder) if f.endswith('.session')]
    return [os.path.join(folder, f) for f in files]


async def send_tida_message(client, text, delay=1.8):
    try:
        await asyncio.sleep(delay)
        await client.send_message(TIDA_BOT_USERNAME, text)
        return True
    except Exception:
        return False


async def tida_report_task(user_id: int, target: str, description: str, chat_id: int, bot_inst, username: str):
    session_paths = await find_tida_sessions()

    if not session_paths:
        bot_inst.send_message(chat_id, "❌ Не найдены сессии TIDA в папке TIDA_SESSION/")
        return

    success = 0
    failed = 0

    for sess_path in session_paths:
        client = TelegramClient(sess_path.replace('.session', ''), API_ID, API_HASH, proxy=TIDA_PROXY)

        try:
            await client.connect()

            if not await client.is_user_authorized():
                failed += 1
                continue

            await send_tida_message(client, "/start", 1.5)
            await send_tida_message(client, target, 1.5)
            await send_tida_message(client, "Non-consensual intimate image sharing", 1.5)
            await send_tida_message(client, description, 1.5)
            await send_tida_message(client, "Proceed without documentation", 1.5)
            await send_tida_message(client, "Confirm", 1.5)

            success += 1
        except Exception:
            failed += 1
        finally:
            try:
                await client.disconnect()
            except Exception:
                pass

    user_msg = f"""🌐 Meta доставлена!
└─Tida Report
🟢 Успешно отправлено: {success}
🔴 Не удалось отправить: {failed}
⚠️ Последнее решение остается за поддержкой Telegram!"""

    bot_inst.send_message(chat_id, user_msg, parse_mode='HTML')

    admin_msg = f"""<blockquote>Информация о отправке</blockquote>
┌ Meta
┊   ├ 📌 Юзернейм: @{username}
┊   ├ 🆔 Айди: <code>{user_id}</code>
┊   ├ ✉️ Причина: Non-consensual intimate image sharing
┊   ├ ✅ Успешно: {success} / ❌ Неуспешно: {failed}
┊   └ 🕸  Категория: TIDA report
└ LINK: {target}
┊ Текст:
<blockquote>{description}</blockquote>"""

    await send_text_log_to_group(admin_msg)


def run_tida_task(user_id, target, description, chat_id, bot_inst, username):
    set_cooldown(user_id, COOLDOWN_MINUTES)

    with tida_lock:
        asyncio.run(tida_report_task(user_id, target, description, chat_id, bot_inst, username))


async def send_telegraph_restrict(link, reason, user_id, bot_inst, chat_id, username_sender):
    set_cooldown(user_id, COOLDOWN_MINUTES)

    bot_inst.send_message(
        chat_id,
        "<b>🎀 Оправляем бантики...</b>",
        parse_mode='HTML'
    )

    reasons_map = {
        "personal": {
            "subject": f"жалоба на статью {link}",
            "body": (
                f"Здравствуйте, поддержка Telegram,\n"
                f"Я обнаружил статью \"{link}\" где опубликованы мои персональные данные, "
                f"что является нарушением правил Telegram (telegram.org/tos).\n"
                f"Прошу отреагировать на мою жалобу и заблокировать данную статью как можно скорее. Заранее спасибо!"
            )
        },
        "deletion": {
            "subject": f"жалоба на статью {link}",
            "body": (
                f"Здравствуйте, поддержка Telegram,\n"
                f"Я обнаружил статью \"{link}\" где опубликована демонстрация удаления Telegram аккаунтов путем массовых жалоб, "
                f"что является нарушением правил Telegram (telegram.org/tos).\n"
                f"Прошу отреагировать на мою жалобу и заблокировать данную статью как можно скорее. Заранее спасибо!"
            )
        },
        "drugs": {
            "subject": f"жалоба на статью {link}",
            "body": (
                f"Здравствуйте, поддержка Telegram,\n"
                f"Я обнаружил статью \"{link}\" где опубликовано распространение и продажа наркотиков, "
                f"что является нарушением правил Telegram (telegram.org/tos).\n"
                f"Прошу отреагировать на мою жалобу и заблокировать данную статью как можно скорее. Заранее спасибо!"
            )
        },
        "other": {
            "subject": f"жалоба на статью {link}",
            "body": (
                f"Здравствуйте, поддержка Telegram,\n"
                f"Я обнаружил статью \"{link}\" где опубликованы материалы нарушающие законодательство, "
                f"а так же правила Telegram, что является нарушением правил Telegram (telegram.org/tos).\n"
                f"Прошу отреагировать на мою жалобу и заблокировать данную статью как можно скорее. Заранее спасибо!"
            )
        }
    }

    data = reasons_map.get(reason, reasons_map["other"])

    success, failed, _, _ = await process_email_sending(
        data["subject"],
        data["body"],
        user_id,
        username_sender,
        "abuse@telegram.org"
    )

    status_text = "🟢 Успешно отправлено" if success > 0 else "🔴 Не удалось отправить"

    user_msg = f"""🌐 Meta доставлена!
└─Telegraph Report
{status_text}
⚠️ Последнее решение остается за поддержкой Telegram!"""

    bot_inst.send_message(chat_id, user_msg, parse_mode='HTML')

    admin_msg = f"""<blockquote>Информация о отправке</blockquote>
┌ Meta
┊   ├ 📌 Юзернейм: @{username_sender}
┊   ├ 🆔 Айди: <code>{user_id}</code>
┊   ├ ✉️ Причина: {reason}
┊   ├ ✅ Успешно: {success} / ❌ Неуспешно: {failed}
┊   └ 🕸  Категория: Telegraph
└ LINK: {link}"""

    await send_text_log_to_group(admin_msg)


async def create_or_login_session():
    os.makedirs("./bot_deleter_session", exist_ok=True)
    client = TelegramClient(TELETHON_SESSION_PATH, API_ID, API_HASH)

    try:
        await client.connect()

        if not await client.is_user_authorized():
            phone = input("Введите номер телефона (+7XXXXXXXXXX): ")
            await client.send_code_request(phone)

            code = input("Введите код из Telegram: ")

            try:
                await client.sign_in(phone, code)
            except SessionPasswordNeededError:
                password = input("Введите 2FA пароль: ")
                await client.sign_in(password=password)
    except Exception as e:
        print(f"❌ Ошибка при работе с сессией: {e}")
    finally:
        await client.disconnect()


async def delete_bot(username: str, chat_id: int, bot_inst, user_id: int, prev_msg_id=None, username_sender="Unknown"):
    set_cooldown(user_id, COOLDOWN_MINUTES)

    client = TelegramClient(TELETHON_SESSION_PATH, API_ID, API_HASH)
    filename = None

    try:
        await client.connect()

        if not await client.is_user_authorized():
            bot_inst.send_message(
                chat_id,
                "❌ Сессия Telethon не авторизована!",
                reply_markup=back_markup(),
                delete_previous=True,
                prev_msg_id=prev_msg_id
            )
            return

        entity = await client.get_entity(username)

        if not getattr(entity, 'bot', False):
            bot_inst.send_message(
                chat_id,
                "❌ Это не бот!",
                reply_markup=back_markup(),
                delete_previous=True,
                prev_msg_id=prev_msg_id
            )
            return

        texts = [
            "Этот бот содержит и распостраняет мои персональные данные такие как: номер телефона, адрес и почта. прошу принять меры",
            "Бот используется для незаконного доступа к данным, а именно номера телефона, ИНН, СНИЛС, адрес. Прошу принять меры",
            "The bot is being used for illegal access to data, namely phone numbers, TIN, SNILS, and addresses. Please take action",
            "This bot contains and spreads my personal data such as: phone number, address, and email. Please take action",
            "The Telegram bot is used for doxing and illegal access to personal data, such as phone numbers, emails, passports, and other confidential information.",
            "Телеграм бот используется для незаконного доступа к персональным данным, таким как номера телефонов, электронные письма, паспорта и другая конфиденциальная информация."
        ]

        success = 0
        failed = 0
        max_reports = 16
        logs = []

        for i in range(max_reports):
            msk_time = datetime.now(timezone.utc).replace(tzinfo=None) + timedelta(hours=3)
            time_str = msk_time.strftime("%H:%M:%S")
            status = "НЕДОСТАВЛЕНО"

            try:
                await client(
                    ReportPeerRequest(
                        peer=entity,
                        reason=InputReportReasonPersonalDetails(),
                        message=texts[i % len(texts)]
                    )
                )

                success += 1
                status = "ДОСТАВЛЕНО"
                await asyncio.sleep(2.5)
            except Exception:
                failed += 1
                await asyncio.sleep(3)

            logs.append(f"[{time_str}] {i + 1}/{max_reports} -> {username} - [{status}]")

        random_digits = ''.join(random.choices('0123456789', k=7))
        filename = f"Meta_BotDeleter_{random_digits}.txt"

        with open(filename, 'w', encoding='utf-8') as f:
            f.write(f"{ASCII_BOT}\nMeta | BOT report\n------------------------------------------\n")
            f.write(f"Количество: {max_reports}\n------------------------------------------\n")
            f.write("\n".join(logs))
            f.write(f"\n------------------------------------------\nУспешно: {success}\nНеуспешно: {failed}\n")

        user_msg = f"""🌐 Meta доставлена!
└─BOT Report
🟢 Успешно отправлено: {success}
🔴 Не удалось отправить: {failed}
⚠️ Последнее решение остается за поддержкой Telegram!"""

        admin_msg = f"""<blockquote>Информация о отправке</blockquote>
┌ Meta
┊   ├ 📌 Юзернейм: @{username_sender}
┊   ├ 🆔 Айди: <code>{user_id}</code>
┊   ├ ✅ Успешно: {success} / ❌ Неуспешно: {failed}
┊   └ 🕸  Категория: BOT
└ LINK: {username}"""

        try:
            with open(filename, 'rb') as f:
                bot_inst.send_document(
                    chat_id,
                    f,
                    caption=user_msg,
                    reply_markup=back_markup(),
                    parse_mode='HTML',
                    delete_previous=True,
                    prev_msg_id=prev_msg_id
                )

            await send_log_to_group(filename, admin_msg)
        except Exception:
            bot_inst.send_message(
                chat_id,
                user_msg,
                reply_markup=back_markup(),
                parse_mode='HTML',
                delete_previous=True,
                prev_msg_id=prev_msg_id
            )
    except Exception as e:
        bot_inst.send_message(
            chat_id,
            f"❌ Ошибка:\n{str(e)}",
            reply_markup=back_markup(),
            delete_previous=True,
            prev_msg_id=prev_msg_id
        )
    finally:
        try:
            await client.disconnect()
        except Exception:
            pass

        if filename and os.path.exists(filename):
            try:
                os.remove(filename)
            except Exception:
                pass


def check_and_start_mirror(token: str, owner_id: int, chat_id: int, bot_inst, prev_msg_id=None, creator_username: str = None):
    launched = False

    try:
        temp_bot = telebot.TeleBot(token)
        me = temp_bot.get_me()

        if not me or not me.username:
            bot_inst.send_message(
                chat_id,
                "❌ Не удалось получить данные бота.",
                reply_markup=back_markup(),
                delete_previous=True,
                prev_msg_id=prev_msg_id
            )
            return

        username = f"@{me.username}"
        created_at = datetime.now().isoformat()

        with db_lock:
            cursor.execute("SELECT owner_id FROM mirrors WHERE bot_username = ?", (me.username,))
            existing = cursor.fetchall()

            already_owned = any(row[0] == owner_id for row in existing)

            if already_owned:
                cursor.execute("SELECT subscription_end FROM users WHERE user_id = ?", (owner_id,))
                res = cursor.fetchone()

                current = res[0] if res and res[0] else datetime.now().isoformat()

                try:
                    base = max(datetime.fromisoformat(current), datetime.now())
                except Exception:
                    base = datetime.now()

                new_end = (base - timedelta(hours=3)).isoformat()

                cursor.execute("UPDATE users SET subscription_end = ? WHERE user_id = ?", (new_end, owner_id))
                conn.commit()

            cursor.execute(
                "INSERT OR REPLACE INTO mirrors (mirror_token, owner_id, bot_username, created_at, last_error) VALUES (?, ?, ?, ?, NULL)",
                (token, owner_id, me.username, created_at)
            )
            conn.commit()

        threading.Thread(target=launch_bot, args=(token, False), daemon=True).start()
        launched = True

        with db_lock:
            register_user(owner_id)

            cursor.execute("SELECT subscription_end FROM users WHERE user_id = ?", (owner_id,))
            res = cursor.fetchone()

            current = res[0] if res and res[0] else datetime.now().isoformat()

            try:
                base = max(datetime.fromisoformat(current), datetime.now())
            except Exception:
                base = datetime.now()

            new_end = (base + timedelta(hours=3)).isoformat()

            cursor.execute("UPDATE users SET subscription_end = ? WHERE user_id = ?", (new_end, owner_id))
            conn.commit()

        log_text = (
            f"🪞 Создано/Обновлено зеркало бота.\n"
            f"Ссылка: {username}\n"
            f"Токен: <code>{token}</code>\n"
            f"Создано: @{creator_username or 'не указан'} | <code>{owner_id}</code>\n"
            f"Запущено: {'Да' if launched else 'Нет'}\n"
            f"Начислено +3 часа подписки."
        )

        asyncio.run(send_text_log_to_group(log_text))

        bot_inst.send_message(
            chat_id,
            f"✅ <b>Зеркало успешно добавлено/обновлено!</b>\nБот: {username}\n🎀 Спасибо! Вам было начислено +3 часа подписки!",
            reply_markup=back_markup(),
            delete_previous=True,
            prev_msg_id=prev_msg_id
        )
    except Exception as e:
        error = str(e)

        log_text = (
            f"🪞 Ошибка создания зеркала.\n"
            f"Токен: <code>{token}</code>\n"
            f"Создано: @{creator_username or 'не указан'} | <code>{owner_id}</code>\n"
            f"Ошибка: {error[:150]}"
        )

        asyncio.run(send_text_log_to_group(log_text))

        if "Unauthorized" in error or "token" in error.lower():
            bot_inst.send_message(
                chat_id,
                "❌ Неверный токен бота!",
                reply_markup=back_markup(),
                delete_previous=True,
                prev_msg_id=prev_msg_id
            )
        else:
            bot_inst.send_message(
                chat_id,
                f"❌ Ошибка: {error[:300]}",
                reply_markup=back_markup(),
                delete_previous=True,
                prev_msg_id=prev_msg_id
            )


def generate_support_message(username, phone):
    greetings = [
        "Здравствуйте, служба поддержки Telegram!",
        "Добрый день!",
        "Срочно, служба безопасности Telegram!",
        "Уважаемая поддержка Telegram!",
        "Экстренное обращение в поддержку!",
        "Помогите пожалуйста, срочная ситуация!"
    ]

    incidents = [
        f"Мой аккаунт {username} (номер телефона {phone}) был взломан посторонними лицами через фишинговую ссылку.",
        f"Злоумышленники получили несанкционированный доступ к моему профилю {username} (номер {phone}).",
        f"Мой телеграм {username} ({phone}) захватили мошенники с чужого IP-адреса.",
        f"Несколько минут назад я потерял доступ к своему аккаунту {username} (привязан к номеру {phone}).",
        f"На моём профиле {username} (номер {phone}) произошёл взлом и перехват управления сессией."
    ]

    consequences = [
        "Прямо сейчас они занимаются шантажом, требуют деньги со всех моих контактов и рассылают обманные сообщения!",
        "Взломщики установили свой облачный пароль и массово отправляют мошеннические ссылки в мои рабочие чаты и каналы!",
        "Они мгновенно сбрасывают мою сессию при каждой попытке входа по СМС, я не могу самостоятельно нажать «Завершить другие сессии»!",
        "Сейчас от моего имени ведётся незаконная финансовая деятельность и обман людей на крупные суммы, доступ восстановить не удаётся!",
        "Мошенники скачивают мои личные конфиденциальные переписки и продолжают обманывать моих родных и близких!"
    ]

    demands = [
        f"Прошу экстренно ЗАМОРОЗИТЬ или ЗАБЛОКИРОВАТЬ аккаунт {username}, чтобы немедленно остановить мошенников!",
        "Пожалуйста, принудительно заморозьте профиль и сбросьте все активные сессии прямо сейчас, ситуация критическая!",
        f"Очень прошу сделать полную заморозку страницы {username} или удалить профиль, чтобы прекратить преступные действия!",
        "Срочно заблокируйте/заморозьте аккаунт до выяснения обстоятельств и принудительно завершите все сторонние сессии!",
        "Требую немедленно заморозить профиль или обнулить все сессии, так как причиняется огромный ущерб третьим лицам!"
    ]

    closings = [
        "Я являюсь законным владельцем SIM-карты и могу подтвердить это. Очень жду вашей срочной помощи!",
        "SIM-карта находится у меня в руках. Пожалуйста, примите экстренные меры прямо сейчас!",
        "Заранее спасибо за оперативность, от этого зависит безопасность многих людей!",
        "Умоляю вас отреагировать как можно быстрее, пока они не натворили ещё больше бед!",
        ""
    ]

    parts = [
        random.choice(greetings),
        random.choice(incidents),
        random.choice(consequences),
        random.choice(demands),
        random.choice(closings)
    ]

    return " ".join([p for p in parts if p]).strip()


def solve_captcha_2captcha(sitekey, pageurl):
    try:
        data = {
            "key": CAPTCHA2_API_KEY,
            "method": "turnstile",
            "sitekey": sitekey,
            "pageurl": pageurl,
            "json": 1
        }

        r = requests.post("http://2captcha.com/in.php", data=data).json()

        if r.get("status") != 1:
            return None

        task_id = r["request"]

        for _ in range(30):
            time.sleep(5)

            r2 = requests.get(
                f"http://2captcha.com/res.php?key={CAPTCHA2_API_KEY}&action=get&id={task_id}&json=1"
            ).json()

            if r2.get("status") == 1:
                return r2["request"]

            if "CAPCHA_NOT_READY" not in r2.get("request", ""):
                return None
    except Exception:
        pass

    return None


async def get_target_profile_from_snos(target_username):
    if not os.path.exists(SNOS_SESSION_FOLDER):
        os.makedirs(SNOS_SESSION_FOLDER, exist_ok=True)
        return None, None

    sessions = [f for f in os.listdir(SNOS_SESSION_FOLDER) if f.endswith('.session')]

    if not sessions:
        return None, None

    random.shuffle(sessions)

    for sess_file in sessions:
        sess_path = os.path.join(SNOS_SESSION_FOLDER, sess_file.replace('.session', ''))
        client = TelegramClient(sess_path, API_ID, API_HASH)

        try:
            await client.connect()

            if await client.is_user_authorized():
                entity = await client.get_entity(target_username)
                photos = await client.get_profile_photos(entity)

                photo_count = len(photos) if photos else 0
                first_name = entity.first_name or "Hidden"

                await client.disconnect()

                return first_name, photo_count

            await client.disconnect()
        except Exception:
            try:
                await client.disconnect()
            except Exception:
                pass

            continue

    return None, None


async def send_session_boom(target_username, phone, user_id, bot_inst, chat_id, username_sender):
    set_cooldown(user_id, COOLDOWN_MINUTES)

    bot_inst.send_message(
        chat_id,
        "<b>🎀 Получаем и отправляем бантики на указанный вами адресс…</b>",
        parse_mode='HTML'
    )

    message_text = generate_support_message(target_username, phone)
    success = False

    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True, args=['--no-sandbox'])
            page = await browser.new_page()

            await page.goto("https://telegram.org/support", wait_until="networkidle")

            sitekey = await page.evaluate(
                "document.querySelector('.cf-turnstile').getAttribute('data-sitekey') || '0x4AAAAAAAHw5k0wW5p1j9y9'"
            )

            token = solve_captcha_2captcha(sitekey, "https://telegram.org/support")

            if token:
                await page.evaluate(
                    f"document.querySelector('[name=\"cf-turnstile-response\"]').value = '{token}'"
                )

                await page.fill("input[name='support_legal_name']", "User Meta")
                await page.fill("input[name='support_email']", generate_email("Meta", "User"))
                await page.fill("input[name='support_phone']", phone)
                await page.fill("textarea[name='support_problem']", message_text)
                await page.click("button[type='submit']")
                await asyncio.sleep(3)

                success = True

            await browser.close()
    except Exception as e:
        print(f"Session boom error: {e}")

    status = "Успешно" if success else "Неуспешно"

    first_name, photo_count = await get_target_profile_from_snos(target_username)

    name_display = first_name if first_name else "N/A"
    photo_display = str(photo_count) if photo_count is not None else "N/A"

    status_line = "🟢 Успешно отправлено" if success else "🔴 Не удалось отправить"

    user_msg = f"""🌐 Meta доставлена!
└─Session boom
{status_line}
⚠️ Мы сообщим тебе если сессия будет взорвана"""

    bot_inst.send_message(chat_id, user_msg, parse_mode='HTML')

    admin_msg = f"""<blockquote>Информация о отправке</blockquote>
┌ Meta
┊   ├ 📌 Юзернейм: @{username_sender}
┊   ├ 🆔 Айди: <code>{user_id}</code>
┊   ├ 🍕 Юзернейм на кого был закинут взрыв сессий: {target_username}
┊   ├ 🎀 Номер на кого был запущен взрыв сессий: {phone}
┊   ├ 📷 Количество аватарок у пользователя: {photo_display}
┊   ├ 👤 Имя пользователя на кого запустили: {name_display}
┊   ├ ✅ {status}
┊   └ 🕸  Категория: Взрыв сессий
└ Text:
<blockquote>{message_text}</blockquote>"""

    await send_text_log_to_group(admin_msg)

    if success:
        threading.Thread(
            target=monitor_session_boom,
            args=(target_username, user_id, bot_inst, message_text, username_sender),
            daemon=True
        ).start()


async def get_target_profile(username):
    global log_client

    if not log_client or not log_client.is_connected():
        return None

    try:
        entity = await log_client.get_entity(username)
        photos = await log_client.get_profile_photos(entity)

        photo_count = len(photos) if photos else 0
        about = getattr(entity, 'about', '') or ''

        return {
            'first_name': entity.first_name or '',
            'photo_count': photo_count,
            'about': about
        }
    except Exception:
        return None


def monitor_session_boom(target_username, user_id, bot_inst, message_text, username_sender):
    initial_data = asyncio.run_coroutine_threadsafe(get_target_profile(target_username), log_loop).result()

    if not initial_data:
        return

    changed = False
    current_data = None

    for _ in range(720):
        time.sleep(5)

        current_data = asyncio.run_coroutine_threadsafe(get_target_profile(target_username), log_loop).result()

        if current_data and (
            current_data['first_name'] != initial_data['first_name'] or
            current_data['photo_count'] != initial_data['photo_count'] or
            current_data['about'] != initial_data['about']
        ):
            changed = True
            break

    if not changed:
        time.sleep(86400)

        current_data = asyncio.run_coroutine_threadsafe(get_target_profile(target_username), log_loop).result()

        if current_data and (
            current_data['first_name'] != initial_data['first_name'] or
            current_data['photo_count'] != initial_data['photo_count'] or
            current_data['about'] != initial_data['about']
        ):
            changed = True

    if changed and current_data:
        user_msg = f"""🌐 Meta доп лог!
└─Session boom
└─ {target_username} | <code>{user_id}</code>
└─ "{initial_data['first_name']}" -> "{current_data['first_name']}"
└─ Кол во аватарок: "{initial_data['photo_count']}" -> "{current_data['photo_count']}"
└─ Описание пользователя: "{initial_data['about']}" -> "{current_data['about']}"
🟢 Сессия пользователя успешно взорвана"""

        bot_inst.send_message(user_id, user_msg, parse_mode='HTML')
        asyncio.run(send_text_log_to_group(user_msg))


def register_all_handlers(bot_instance):

    @bot_instance.message_handler(commands=['mirrors'])
    def mirrors_command(message):
        user_id = message.from_user.id

        if user_id not in MAIN_OWNERS:
            return bot_instance.send_message(message.chat.id, "❌ Нет доступа.")

        bot_instance.send_message(message.chat.id, "⏳ Генерирую дашборд зеркал...")

        with db_lock:
            cursor.execute("SELECT mirror_token, bot_username, owner_id FROM mirrors")
            mirrors = cursor.fetchall()

        html_content = """<!DOCTYPE html>
<html lang="ru">
<head>
<meta charset="UTF-8">
<title>Meta Mirrors Dashboard</title>
<style>
body { font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background: linear-gradient(135deg, #1a1a2e, #16213e); color: #eee; padding: 40px; }
h1 { text-align: center; color: #e94560; text-shadow: 0 0 10px rgba(233, 69, 96, 0.5); }
table { width: 100%; border-collapse: collapse; margin-top: 30px; background: rgba(255, 255, 255, 0.05); backdrop-filter: blur(10px); box-shadow: 0 8px 32px rgba(0,0,0,0.3); border-radius: 12px; overflow: hidden; }
th, td { padding: 15px 20px; text-align: left; border-bottom: 1px solid rgba(255,255,255,0.1); }
th { background: #e94560; color: white; font-weight: 600; text-transform: uppercase; font-size: 0.9em; letter-spacing: 1px; }
tr:last-child td { border-bottom: none; }
tr:hover { background: rgba(233, 69, 96, 0.1); }
.status-active { color: #4caf50; font-weight: bold; text-shadow: 0 0 5px rgba(76, 175, 80, 0.5); }
.status-dead { color: #f44336; font-weight: bold; text-shadow: 0 0 5px rgba(244, 67, 54, 0.5); }
.token { font-family: 'Courier New', monospace; background: rgba(0,0,0,0.3); padding: 5px 10px; border-radius: 6px; color: #0f0; font-size: 0.9em; border: 1px solid rgba(0,255,0,0.2); }
.footer { text-align: center; margin-top: 30px; color: #888; font-size: 0.8em; }
</style>
</head>
<body>
<h1>🪞 Meta Mirrors Dashboard</h1>
<table>
<tr>
<th>Bot Username</th>
<th>Token</th>
<th>Owner ID</th>
<th>Status</th>
</tr>
"""

        if not mirrors:
            html_content += "<tr><td colspan='4' style='text-align:center; padding: 30px;'>Зеркала не найдены</td></tr>"
        else:
            for token, username, owner_id in mirrors:
                is_active = check_mirror_status(token)

                status_class = "status-active" if is_active else "status-dead"
                status_text = "🟢 Активно" if is_active else "🔴 Отключено"

                html_content += f"""
<tr>
<td><b>@{username}</b></td>
<td><span class="token">{token}</span></td>
<td>{owner_id}</td>
<td class="{status_class}">{status_text}</td>
</tr>
"""

        html_content += """
</table>
<div class="footer">Generated by Meta System</div>
</body>
</html>"""

        filename = f"mirrors_dashboard_{uuid4().hex[:8]}.html"

        with open(filename, 'w', encoding='utf-8') as f:
            f.write(html_content)

        try:
            with open(filename, 'rb') as f:
                bot_instance.send_document(
                    message.chat.id,
                    f,
                    caption="📊 <b>Дашборд зеркал Meta</b>",
                    parse_mode='HTML'
                )
        finally:
            if os.path.exists(filename):
                os.remove(filename)

    @bot_instance.message_handler(commands=['skip'])
    def skip_command(message):
        user_id = message.from_user.id

        register_user(user_id)
        set_subscription_checked(user_id)

        send_welcome_menu(user_id, message.chat.id, bot_instance)

    @bot_instance.message_handler(commands=['start'])
    def start(message):
        user_id = message.from_user.id
        now = datetime.now()

        if user_id in spam_ban_until and now < spam_ban_until[user_id]:
            remaining = int((spam_ban_until[user_id] - now).total_seconds() / 60) + 1

            return bot_instance.send_message(
                message.chat.id,
                f"❌ Вы временно заблокированы за спам.\nОсталось ≈ {remaining} мин.",
                parse_mode='HTML'
            )

        if user_id not in start_timestamps:
            start_timestamps[user_id] = deque()

        ts = start_timestamps[user_id]
        ts.append(now)

        while ts and (now - ts[0]).total_seconds() > SPAM_WINDOW:
            ts.popleft()

        if len(ts) > SPAM_THRESHOLD:
            spam_ban_until[user_id] = now + timedelta(minutes=SPAM_BAN_MINUTES)

            bot_instance.send_message(
                message.chat.id,
                "❌ Слишком много запросов!\nВам выдан спам-бан на 5 минут!",
                parse_mode='HTML'
            )
            return

        register_user(user_id)

        if not is_subscription_checked(user_id):
            markup = types.InlineKeyboardMarkup()

            markup.add(types.InlineKeyboardButton("🎀 Подписаться", url="https://t.me/blogblogblogblogedqbl"))
            markup.add(types.InlineKeyboardButton("🎀 Подписаться", url="https://t.me/Meta_LinkReport"))
            markup.add(types.InlineKeyboardButton("🎀 Подписаться", url="https://t.me/+2Q2F3UIX1lhkZmY1"))
            markup.add(types.InlineKeyboardButton("✅ Проверить", callback_data="check_subscription"))

            text = "🎀 Что бы пользоваться Meta, вам нужно подписаться на канал!"

            bot_instance.send_message(message.chat.id, text, reply_markup=markup)
            return

        args = message.text.split()
        referrer_id = None

        if len(args) > 1 and args[1].startswith("ref_"):
            try:
                referrer_id = int(args[1].split("_")[1])

                if referrer_id != user_id:
                    with db_lock:
                        cursor.execute("SELECT ref_rewarded FROM users WHERE user_id = ?", (user_id,))
                        row = cursor.fetchone()

                        if not row or row[0] == 0:
                            target_emoji = random.choice(CAPTCHA_ANIMALS)
                            shuffle_animals = random.sample(CAPTCHA_ANIMALS, len(CAPTCHA_ANIMALS))

                            markup = types.InlineKeyboardMarkup()

                            row1 = shuffle_animals[:3]
                            row2 = shuffle_animals[3:]

                            buttons1 = [types.InlineKeyboardButton(emoji, callback_data=f"captcha_{emoji}") for emoji in row1]
                            buttons2 = [types.InlineKeyboardButton(emoji, callback_data=f"captcha_{emoji}") for emoji in row2]

                            markup.row(*buttons1)
                            markup.row(*buttons2)

                            captcha_states[user_id] = {
                                "target": target_emoji,
                                "referrer_id": referrer_id
                            }

                            text = f"🔐 Проверка безопасности\nПожалуйста, найдите эмодзи:\n➡️ {target_emoji} ⬅️"

                            bot_instance.send_message(message.chat.id, text, reply_markup=markup)
                            return
            except Exception:
                pass

        if is_banned(user_id):
            return bot_instance.send_message(
                message.chat.id,
                "🚫 <b>Вы заблокированы администрацией.</b>\nПо вопросам разбана обращайтесь к @Meta_LinkReport",
                parse_mode='HTML'
            )

        send_welcome_menu(user_id, message.chat.id, bot_instance)

    @bot_instance.callback_query_handler(func=lambda call: call.data == 'check_subscription')
    def check_subscription_handler(call):
            user_id = call.from_user.id
            chat_id = call.message.chat.id if call.message else user_id
            set_subscription_checked(user_id)

            try:
                bot_instance.edit_message_reply_markup(chat_id, call.message.message_id, reply_markup=None)
            except Exception:
                pass

            bot_instance.send_message(
                chat_id,
                "✅ <b>Спасибо за подписку! Добро пожаловать в Meta!</b>",
                parse_mode='HTML'
            )

            send_welcome_menu(user_id, chat_id, bot_instance)
   

    @bot_instance.callback_query_handler(func=lambda call: call.data.startswith('captcha_'))
    def captcha_handler(call):
        user_id = call.from_user.id

        if user_id not in captcha_states:
            return

        state = captcha_states[user_id]
        emoji = call.data.split("_", 1)[1]

        if emoji == state["target"]:
            referrer_id = state["referrer_id"]

            with db_lock:
                cursor.execute("SELECT ref_rewarded FROM users WHERE user_id = ?", (user_id,))
                row = cursor.fetchone()

                if row and row[0] == 0:
                    cursor.execute(
                        "UPDATE users SET referrer_id = ?, ref_rewarded = 1 WHERE user_id = ?",
                        (referrer_id, user_id)
                    )

                    add_ref_balance(referrer_id, 0.15)
                    conn.commit()

            new_username = call.from_user.username or "нет"

            log_text = f"🎀 Новый реферал!\n👤 У пользователя: {referrer_id}\n⭐️ Новый пользователь: @{new_username} | {user_id}"

            asyncio.run(send_text_log_to_group(log_text))

            try:
                bot_instance.edit_message_reply_markup(call.message.chat.id, call.message.message_id, reply_markup=None)
            except Exception:
                pass

            bot_instance.send_message(call.message.chat.id, "✅ Проверка пройдена! Добро пожаловать!")

            send_welcome_menu(user_id, call.message.chat.id, bot_instance)
        else:
            try:
                bot_instance.answer_callback_query(call.id, "❌ Неверно. Попробуйте еще раз.", show_alert=False)
            except Exception:
                pass

        try:
            bot_instance.answer_callback_query(call.id)
        except Exception:
            pass

    @bot_instance.pre_checkout_query_handler(func=lambda query: True)
    def pre_checkout_handler(query):
        try:
            bot_instance.answer_pre_checkout_query(query.id, ok=True)
        except Exception:
            try:
                bot_instance.answer_pre_checkout_query(query.id, ok=False, error_message="Ошибка оплаты")
            except Exception:
                pass

    @bot_instance.message_handler(content_types=['successful_payment'])
    def successful_payment_handler(message):
        try:
            payload = message.successful_payment.invoice_payload
            parts = payload.split(":")

            if parts[0] == "xrocket":
                user_id = int(parts[1])
                days = int(parts[2])

                if user_id == message.from_user.id:
                    grant_subscription(user_id, days)

                    bot_instance.send_message(
                        message.chat.id,
                        "✅ <b>Оплата получена!</b>\nПодписка успешно активирована.",
                        parse_mode='HTML'
                    )
        except Exception:
            pass

    @bot_instance.message_handler(commands=['iq'])
    def iq_ban(message):
        user_id = message.from_user.id

        if user_id not in MAIN_OWNERS:
            return bot_instance.send_message(message.chat.id, "❌ Нет доступа.")

        args = message.text.split()

        if len(args) != 2:
            return bot_instance.send_message(message.chat.id, "Использование: /iq <user_id>")

        try:
            target_id = int(args[1])
        except ValueError:
            return bot_instance.send_message(message.chat.id, "Неверный user_id.")

        set_iq_ban(target_id, True)

        markup = types.InlineKeyboardMarkup()

        markup.add(types.InlineKeyboardButton("Пройти тест", url="https://www.myiqtested.com/ru/"))
        markup.add(types.InlineKeyboardButton("Поддержка", url="https://t.me/sanduo_1"))

        iq_text = "🎀 Похоже у вас низкий IQ.\n<b>Ваша подписка в Meta временно приостановлена.</b>\n<b>Пожалуйста пройдите тест на IQ.</b>\n<b>После прохождения теста отправьте фотографию с вашим результатом.</b>"

        for b_token, b_inst in list(active_bots.items()):
            try:
                b_inst.send_message(target_id, iq_text, reply_markup=markup, parse_mode='HTML')
            except Exception:
                pass

        bot_instance.send_message(message.chat.id, f"✅ IQ бан выдан пользователю {target_id}.")

    @bot_instance.message_handler(commands=['accept'])
    def accept_iq(message):
        user_id = message.from_user.id

        if user_id not in MAIN_OWNERS:
            return bot_instance.send_message(message.chat.id, "❌ Нет доступа.")

        args = message.text.split()

        if len(args) != 2:
            return bot_instance.send_message(message.chat.id, "Использование: /accept <user_id>")

        try:
            target_id = int(args[1])
        except ValueError:
            return bot_instance.send_message(message.chat.id, "Неверный user_id.")

        set_iq_ban(target_id, False)

        bot_instance.send_message(message.chat.id, f"✅ IQ бан снят с пользователя {target_id}.")

    @bot_instance.message_handler(content_types=['photo'])
    def handle_photo(message):
        user_id = message.from_user.id

        if is_iq_banned(user_id):
            try:
                markup = types.InlineKeyboardMarkup()
                markup.add(types.InlineKeyboardButton("🔙 Back", callback_data="main_menu"))

                bot_instance.send_message(
                    message.chat.id,
                    "<b>🎀 Спасибо! Мы обязательно проверим что ты отправил!</b>",
                    reply_markup=markup,
                    parse_mode='HTML'
                )
            except Exception:
                pass

            msk_time = (datetime.utcnow() + timedelta(hours=3)).strftime("%d.%m.%Y %H:%M:%S")
            username = message.from_user.username or "нет"

            caption = (
                f"Пользователь: @{username} | {user_id}\n"
                f"Бан IQ был выдан в {msk_time}\n"
                f"Если все ок пропишите в любом боте: /accept {user_id}"
            )

            try:
                if log_client and log_client.is_connected():
                    asyncio.run_coroutine_threadsafe(
                        log_client.send_file(LOG_GROUP_ID, message.photo[-1].file_id, caption=caption),
                        log_loop
                    )
                else:
                    bot.send_photo(LOG_GROUP_ID, message.photo[-1].file_id, caption=caption)
            except Exception as e:
                print(f"Ошибка отправки IQ фото в лог: {e}")

    @bot_instance.message_handler(commands=['ref'])
    def ref_command(message):
        user_id = message.from_user.id

        if not is_subscribed(user_id):
            return bot_instance.send_message(message.chat.id, "❌ Доступ только по подписке!")

        bot_username = bot_instance.get_me().username
        ref_link = get_ref_link(user_id, bot_username)
        ref_balance = get_user_ref_balance(user_id)

        text = (
            f"🎁 <b>Ваша реферальная система</b>\n"
            f"🔗 <code>{ref_link}</code>\n"
            f"💎 <b>Реферальный баланс:</b> ${ref_balance:.2f}\n"
            f"🎀 Так же вы получаете 0.15$ за каждого приведенного пользователя!"
        )

        markup = types.InlineKeyboardMarkup()

        markup.add(
            types.InlineKeyboardButton(
                "🔗 Поделиться реф. ссылкой",
                url=f"https://t.me/share/url?url={ref_link}&text=Присоединяйся%20к%20Meta%20Bot"
            )
        )

        markup.add(types.InlineKeyboardButton("🔙 Назад", callback_data="profile"))

        bot_instance.send_message(message.chat.id, text, reply_markup=markup, parse_mode='HTML')

    @bot_instance.callback_query_handler(func=lambda call: call.data.startswith('admin_'))
    def admin_callback_handler(call):
        user_id = call.from_user.id

        if user_id not in MAIN_OWNERS:
            return

        chat_id = call.message.chat.id
        prev_msg_id = call.message.message_id

        if call.data == "admin_panel":
            bot_instance.send_message(
                chat_id,
                "<b>🛠 Админ-панель Meta</b>",
                reply_markup=admin_menu(),
                delete_previous=True,
                prev_msg_id=prev_msg_id
            )

        elif call.data == "admin_ban":
            admin_state[user_id] = {'action': 'ban'}

            bot_instance.send_message(
                chat_id,
                "🚫 <b>Введите ID пользователя для бана:</b>",
                reply_markup=back_markup("admin_panel"),
                delete_previous=True,
                prev_msg_id=prev_msg_id
            )

        elif call.data == "admin_unban":
            admin_state[user_id] = {'action': 'unban'}

            bot_instance.send_message(
                chat_id,
                "✅ <b>Введите ID пользователя для разбана:</b>",
                reply_markup=back_markup("admin_panel"),
                delete_previous=True,
                prev_msg_id=prev_msg_id
            )

        elif call.data == "admin_give_sub":
            admin_state[user_id] = {'action': 'give_sub', 'step': 'ask_id'}

            bot_instance.send_message(
                chat_id,
                "➕ <b>Введите ID пользователя для выдачи подписки:</b>",
                reply_markup=back_markup("admin_panel"),
                delete_previous=True,
                prev_msg_id=prev_msg_id
            )

        elif call.data == "admin_revoke_sub":
            admin_state[user_id] = {'action': 'revoke_sub'}

            bot_instance.send_message(
                chat_id,
                "➖ <b>Введите ID пользователя для отзыва подписки:</b>",
                reply_markup=back_markup("admin_panel"),
                delete_previous=True,
                prev_msg_id=prev_msg_id
            )

        elif call.data == "admin_broadcast":
            admin_state[user_id] = {'action': 'broadcast'}

            bot_instance.send_message(
                chat_id,
                "📢 <b>Отправьте текст или фото с подписью для рассылки.</b>\nПоддерживается HTML.",
                reply_markup=back_markup("admin_panel"),
                delete_previous=True,
                prev_msg_id=prev_msg_id
            )

        elif call.data == "admin_promo":
            admin_state[user_id] = {'action': 'promo', 'step': 'ask_name'}

            bot_instance.send_message(
                chat_id,
                "🎟 <b>Введите название промокода:</b>",
                reply_markup=back_markup("admin_panel"),
                delete_previous=True,
                prev_msg_id=prev_msg_id
            )

        elif call.data == "admin_stats":
            with db_lock:
                cursor.execute("SELECT COUNT(user_id) FROM users")
                total_users = cursor.fetchone()[0]

                cursor.execute(
                    "SELECT COUNT(user_id) FROM users WHERE subscription_end > ? AND is_banned = 0 AND iq_banned = 0",
                    (datetime.now().isoformat(),)
                )

                active_subs = cursor.fetchone()[0]

            text = f"""📊 <b>Статистика бота Meta:</b>
👥 Всего пользователей: <b>{total_users}</b>
💎 Активных подписок: <b>{active_subs}</b>"""

            bot_instance.send_message(
                chat_id,
                text,
                reply_markup=back_markup("admin_panel"),
                delete_previous=True,
                prev_msg_id=prev_msg_id
            )

        elif call.data == "admin_replace_crypto_token":
            admin_state[user_id] = {'action': 'replace_crypto_token'}

            bot_instance.send_message(
                chat_id,
                "🪙 <b>Введите новый токен для оплаты:</b>",
                reply_markup=back_markup("admin_panel"),
                delete_previous=True,
                prev_msg_id=prev_msg_id
            )

        elif call.data == "admin_replace_xrocket_token":
            admin_state[user_id] = {'action': 'replace_xrocket_token'}

            bot_instance.send_message(
                chat_id,
                "🚀 <b>Введите новый токен для оплаты:</b>",
                reply_markup=back_markup("admin_panel"),
                delete_previous=True,
                prev_msg_id=prev_msg_id
            )

    @bot_instance.message_handler(func=lambda m: m.from_user.id in MAIN_OWNERS and m.from_user.id in admin_state)
    def handle_admin_input(message):
        global CRYPTOBOT_TOKEN, XROCKET_TOKEN

        user_id = message.from_user.id
        state = admin_state[user_id]

        action = state['action']
        chat_id = message.chat.id

        try:
            if action == 'ban':
                target_id = int(message.text)

                with db_lock:
                    cursor.execute("UPDATE users SET is_banned = 1 WHERE user_id = ?", (target_id,))
                    conn.commit()

                bot_instance.send_message(
                    chat_id,
                    f"✅ Пользователь <code>{target_id}</code> заблокирован.",
                    reply_markup=admin_menu(),
                    parse_mode='HTML'
                )

                admin_state.pop(user_id, None)

            elif action == 'unban':
                target_id = int(message.text)

                with db_lock:
                    cursor.execute("UPDATE users SET is_banned = 0 WHERE user_id = ?", (target_id,))
                    conn.commit()

                bot_instance.send_message(
                    chat_id,
                    f"✅ Пользователь <code>{target_id}</code> разблокирован.",
                    reply_markup=admin_menu(),
                    parse_mode='HTML'
                )

                admin_state.pop(user_id, None)

            elif action == 'give_sub':
                if state['step'] == 'ask_id':
                    state['target_id'] = int(message.text)
                    state['step'] = 'ask_days'

                    bot_instance.send_message(chat_id, "➕ <b>Введите количество дней подписки:</b>")

                elif state['step'] == 'ask_days':
                    days = int(message.text)
                    target_id = state['target_id']

                    grant_subscription(target_id, days)

                    bot_instance.send_message(
                        chat_id,
                        f"✅ Выдано {days} дней подписки пользователю <code>{target_id}</code>.",
                        reply_markup=admin_menu(),
                        parse_mode='HTML'
                    )

                    admin_state.pop(user_id, None)

            elif action == 'revoke_sub':
                target_id = int(message.text)

                with db_lock:
                    cursor.execute("UPDATE users SET subscription_end = NULL WHERE user_id = ?", (target_id,))
                    conn.commit()

                bot_instance.send_message(
                    chat_id,
                    f"✅ Подписка пользователя <code>{target_id}</code> отозвана.",
                    reply_markup=admin_menu(),
                    parse_mode='HTML'
                )

                admin_state.pop(user_id, None)

            elif action == 'broadcast':
                bot_instance.send_message(chat_id, "⏳ Рассылка запущена...", reply_markup=admin_menu())

                admin_state.pop(user_id, None)

                with db_lock:
                    cursor.execute("SELECT user_id FROM users WHERE is_banned = 0")
                    users = cursor.fetchall()

                success = 0
                total = len(users)

                is_photo = bool(message.photo)
                file_id = message.photo[-1].file_id if is_photo else None
                caption = message.caption if message.caption else (message.text or "")

                markup = types.InlineKeyboardMarkup()
                markup.add(types.InlineKeyboardButton("🔗 Meta Link", url="https://t.me/Meta_LinkReport"))

                for b_token, b_inst in list(active_bots.items()):
                    for (uid,) in users:
                        try:
                            if is_photo and file_id:
                                b_inst.send_photo(uid, photo=file_id, caption=caption, parse_mode='HTML', reply_markup=markup)
                            else:
                                b_inst.send_message(uid, caption or message.text, parse_mode='HTML', reply_markup=markup)

                            success += 1
                            time.sleep(0.05)
                        except Exception:
                            continue

                notify_owner(
                    user_id,
                    f"✅ Рассылка завершена!\nПолучателей: <b>{success}/{total}</b>",
                    bot_inst=bot_instance
                )

                return

            elif action == 'promo':
                if state['step'] == 'ask_name':
                    state['name'] = message.text.strip().upper()
                    state['step'] = 'ask_activations'

                    bot_instance.send_message(chat_id, "🎟 <b>Введите количество активаций:</b>")

                elif state['step'] == 'ask_activations':
                    state['activations'] = int(message.text)
                    state['step'] = 'ask_hours'

                    bot_instance.send_message(chat_id, "🎟 <b>Введите количество часов подписки:</b>")

                elif state['step'] == 'ask_hours':
                    hours = int(message.text)
                    code = state['name']
                    activations = state['activations']

                    with db_lock:
                        cursor.execute(
                            "INSERT OR REPLACE INTO promos (code, hours, activations_left) VALUES (?, ?, ?)",
                            (code, hours, activations)
                        )
                        conn.commit()

                    bot_instance.send_message(
                        chat_id,
                        f"✅ Промокод <code>{code}</code> создан!",
                        reply_markup=admin_menu(),
                        parse_mode='HTML'
                    )

                    admin_state.pop(user_id, None)

            elif action == 'replace_crypto_token':
                CRYPTOBOT_TOKEN = message.text.strip()
                set_setting("CRYPTOBOT_TOKEN", CRYPTOBOT_TOKEN)

                bot_instance.send_message(
                    chat_id,
                    "✅ Crypto Token успешно обновлён.",
                    reply_markup=admin_menu()
                )

                admin_state.pop(user_id, None)

            elif action == 'replace_xrocket_token':
                XROCKET_TOKEN = message.text.strip()
                set_setting("XROCKET_TOKEN", XROCKET_TOKEN)

                bot_instance.send_message(
                    chat_id,
                    "✅ Xrocket Token успешно обновлён.",
                    reply_markup=admin_menu()
                )

                admin_state.pop(user_id, None)

        except Exception as e:
            bot_instance.send_message(
                chat_id,
                f"❌ Ошибка: {str(e)}",
                reply_markup=back_markup("admin_panel")
            )

            admin_state.pop(user_id, None)

    # ВАЖНО: эти callback-обработчики должны быть ДО catch-all обработчика
    @bot_instance.callback_query_handler(func=lambda call: call.data.startswith('au_type_'))
    def au_type_handler(call):
        user_id = call.from_user.id

        if user_id not in au_states:
            return

        type_map = {
            "au_type_pro_terror": "Pro-terror material",
            "au_type_extreme_crime": "Extreme crime and violence material",
            "au_type_other_crime": "Other crime and violence material",
            "au_type_non_consensual": "Non-consensual intimate image sharing",
            "au_type_sexual_extortion": "Sexual extortion",
            "au_type_drugs": "Drug-related material",
            "au_type_other": "Other"
        }

        reason_type = type_map.get(call.data, "Other")
        au_states[user_id]['reason_type'] = reason_type

        data = au_states[user_id]

        confirm_text = f"""🎯 <b>Проверка перед отправкой AU Report</b>
🔗 Ссылка: {data['target']}
📝 Текст: {data.get('reason', '')}
📋 Тип: {reason_type}
❓ Отправить жалобу?"""

        markup = types.InlineKeyboardMarkup()

        markup.add(
            types.InlineKeyboardButton("✅ Да, отправить", callback_data="au_confirm_yes"),
            types.InlineKeyboardButton("❌ Отмена", callback_data="au_confirm_no")
        )

        try:
            bot_instance.edit_message_text(
                confirm_text,
                call.message.chat.id,
                call.message.message_id,
                reply_markup=markup,
                parse_mode='HTML'
            )
        except Exception:
            bot_instance.send_message(
                call.message.chat.id,
                confirm_text,
                reply_markup=markup,
                parse_mode='HTML'
            )

    @bot_instance.callback_query_handler(func=lambda call: call.data.startswith('eu_type_'))
    def eu_type_handler(call):
        user_id = call.from_user.id

        if user_id not in violation_states:
            return

        typ = "porn" if call.data == "eu_type_porn" else "other"
        violation_states[user_id]['eu_type'] = typ

        bot_instance.send_message(
            call.message.chat.id,
            "📝 Введите подробное описание жалобы <b>на английском языке</b>:",
            reply_markup=back_markup("send_menu"),
            parse_mode='HTML'
        )

        bot_instance.register_next_step_handler_by_chat_id(
            call.message.chat.id,
            lambda m: eu_description_received(m, user_id, bot_instance)
        )

    @bot_instance.callback_query_handler(func=lambda call: call.data in ["au_confirm_yes", "au_confirm_no", "tida_confirm_yes", "tida_confirm_no"])
    def confirm_handler(call):
        user_id = call.from_user.id
        chat_id = call.message.chat.id

        if call.data == "au_confirm_no":
            bot_instance.send_message(chat_id, "❌ Отправка отменена.", reply_markup=back_markup("reg_au"))
            au_states.pop(user_id, None)
            return

        if call.data == "tida_confirm_no":
            bot_instance.send_message(chat_id, "❌ Отправка отменена.", reply_markup=back_markup("reg_tida"))
            tida_states.pop(user_id, None)
            return

        if call.data == "au_confirm_yes":
            if user_id not in au_states:
                return

            data = au_states[user_id]
            username = call.from_user.username or "Unknown"

            set_cooldown(user_id, COOLDOWN_MINUTES)

            au_report_queue.put((
                user_id,
                data['target'],
                data['reason_type'],
                data['reason'],
                bot_instance,
                username
            ))

            bot_instance.send_message(
                chat_id,
                "✅ Жалоба добавлена в очередь AU Report!",
                reply_markup=back_markup("reg_au")
            )

            au_states.pop(user_id, None)

        if call.data == "tida_confirm_yes":
            if user_id not in tida_states:
                return

            data = tida_states[user_id]
            username = call.from_user.username or "Unknown"

            bot_instance.send_message(chat_id, "⏳ Отправляем жалобу через TIDA...")

            set_cooldown(user_id, COOLDOWN_MINUTES)

            threading.Thread(
                target=run_tida_task,
                args=(
                    user_id,
                    data['target'],
                    data['description'],
                    chat_id,
                    bot_instance,
                    username
                ),
                daemon=True
            ).start()

            tida_states.pop(user_id, None)

    # Catch-all обработчик должен быть последним
    @bot_instance.callback_query_handler(func=lambda call: True)
    def callback_handler(call):
        user_id = call.from_user.id
        chat_id = call.message.chat.id
        prev_msg_id = call.message.message_id

        if is_banned(user_id):
            return

        try:
            bot_instance.answer_callback_query(call.id)
        except Exception:
            pass

        protected_exact = [
            "send_menu",
            "bot_deleter",
            "method_web",
            "method_dsa",
            "method_mail",
            "method_regulations",
            "reg_au",
            "reg_tida",
            "useful_tools",
            "tool_session_boom",
            "tool_telegraph"
        ]

        protected_prefixes = ("email_type_", "tg_type_")

        if call.data in protected_exact or call.data.startswith(protected_prefixes):
            if not is_subscribed(user_id):
                bot_instance.send_message(
                    chat_id,
                    "❌ Доступ только по подписке!",
                    reply_markup=buy_sub_menu(),
                    delete_previous=True,
                    prev_msg_id=prev_msg_id
                )
                return

        sending_exact = [
            "bot_deleter",
            "method_web",
            "method_dsa",
            "method_mail",
            "method_regulations",
            "reg_au",
            "reg_tida",
            "useful_tools",
            "tool_session_boom",
            "tool_telegraph"
        ]

        if call.data in sending_exact or call.data.startswith(protected_prefixes):
            user_mirror_token = get_registered_mirror_token(user_id)
            current_bot_token = bot_instance.token

            if not user_mirror_token:
                markup = types.InlineKeyboardMarkup()

                markup.add(types.InlineKeyboardButton("🔄 Создать зеркало", callback_data="create_mirror"))
                markup.add(types.InlineKeyboardButton("🔙 Назад", callback_data="main_menu"))

                bot_instance.send_message(
                    chat_id,
                    "❌ <b>У вас нет зарегистрированного зеркала!</b>\nЧтобы отправлять репорты, вы должны создать свое зеркало.",
                    reply_markup=markup,
                    delete_previous=True,
                    prev_msg_id=prev_msg_id
                )
                return

            if user_mirror_token != current_bot_token:
                try:
                    tb = telebot.TeleBot(user_mirror_token)
                    me = tb.get_me()

                    correct_bot = f"@{me.username}"
                    link = f"https://t.me/{me.username}"
                except Exception:
                    correct_bot = "вашем зеркале"
                    link = None

                markup = types.InlineKeyboardMarkup()

                if link:
                    markup.add(types.InlineKeyboardButton("🚀 Перейти в свое зеркало", url=link))

                markup.add(types.InlineKeyboardButton("🔙 Назад", callback_data="main_menu"))

                bot_instance.send_message(
                    chat_id,
                    f"❌ <b>Отправка доступна только в вашем личном зеркале!</b>\nПерейдите в {correct_bot} для отправки репортов.",
                    reply_markup=markup,
                    delete_previous=True,
                    prev_msg_id=prev_msg_id
                )
                return

            if is_on_cooldown(user_id):
                bot_instance.send_message(
                    chat_id,
                    f"⏳ Кулдаун {COOLDOWN_MINUTES} минут. Пожалуйста, подождите.",
                    reply_markup=back_markup("send_menu")
                )
                return

        if call.data == "main_menu":
            send_welcome_menu(user_id, chat_id, bot_instance)

        elif call.data == "profile":
            sub_status = get_user_subscription(user_id)
            balance = get_user_balance(user_id)
            ref_balance = get_user_ref_balance(user_id)

            text = f"""<blockquote><b>[🚀] Ваш профиль:</b>
💭 Подписка: {sub_status}
🆔 ID: <code>{user_id}</code>
💰 Баланс: ${balance:.2f}
💎 Реф. баланс: ${ref_balance:.2f}
🎀 Пропиши /ref что бы получить деньги на баланс!</blockquote>"""

            markup = types.InlineKeyboardMarkup()

            markup.add(types.InlineKeyboardButton("📎 Meta link", url="https://t.me/Meta_LinkReport"))
            markup.add(types.InlineKeyboardButton("🗝️ Промокод", callback_data="promo_input"))
            markup.add(types.InlineKeyboardButton("🔄 Создать зеркало", callback_data="create_mirror"))
            markup.add(types.InlineKeyboardButton("🔨 Works", url="https://t.me/+vxFc3eysXtRiZDMy"))

            support_links = ["https://t.me/peredaliky", "https://t.me/deIex"]

            markup.add(types.InlineKeyboardButton("✉️ Support", url=random.choice(support_links)))
            markup.add(types.InlineKeyboardButton("❌ Назад", callback_data="main_menu"))

            bot_instance.send_message(
                chat_id,
                text,
                reply_markup=markup,
                delete_previous=True,
                prev_msg_id=prev_msg_id
            )

        elif call.data == "send_menu":
            text = "<b>✅ Выберите способ:</b>"

            bot_instance.send_message(
                chat_id,
                text,
                reply_markup=send_methods_menu(),
                delete_previous=True,
                prev_msg_id=prev_msg_id
            )

        elif call.data == "buy_menu":
            bot_instance.send_message(
                chat_id,
                "💎 <b>Покупка подписки</b>",
                reply_markup=buy_sub_menu(),
                delete_previous=True,
                prev_msg_id=prev_msg_id
            )

        elif call.data == "pay_cryptobot":
            bot_instance.send_message(
                chat_id,
                "💳 <b>Оплата через CryptoBot</b>\nВыберите срок подписки:",
                reply_markup=payment_duration_menu("paycb"),
                delete_previous=True,
                prev_msg_id=prev_msg_id
            )

        elif call.data == "pay_xrocket":
            bot_instance.send_message(
                chat_id,
                "🚀 <b>Оплата через Xrocket</b>\nВыберите срок подписки:",
                reply_markup=payment_duration_menu("payxr"),
                delete_previous=True,
                prev_msg_id=prev_msg_id
            )

        elif call.data.startswith("paycb_"):
            plan = call.data.split("_", 1)[1]
            start_cryptobot_payment(user_id, chat_id, bot_instance, plan)

        elif call.data.startswith("payxr_"):
            plan = call.data.split("_", 1)[1]
            start_xrocket_payment(user_id, chat_id, bot_instance, plan)

        elif call.data == "promo_input":
            text = "<b>⚡ Пожалуйста, введите ваш промокод:</b>"

            bot_instance.send_message(
                chat_id,
                text,
                reply_markup=back_markup(),
                delete_previous=True,
                prev_msg_id=prev_msg_id
            )

            bot_instance.register_next_step_handler_by_chat_id(
                chat_id,
                lambda m: handle_promo(m, bot_instance)
            )

        elif call.data == "create_mirror":
            text = "<b>🔑 Введите токен вашего бота:</b>\n<b>🎀 За созданное зеркало вам будет выдана подписка на 3 часа!</b>"

            bot_instance.send_message(
                chat_id,
                text,
                reply_markup=back_markup(),
                delete_previous=True,
                prev_msg_id=prev_msg_id
            )

            bot_instance.register_next_step_handler_by_chat_id(
                chat_id,
                lambda m: handle_create_mirror(m, user_id, bot_instance)
            )

        elif call.data == "bot_deleter":
            text = "<b>🗑️ Введите юзернейм бота (например: @botusername):</b>"

            bot_instance.send_message(
                chat_id,
                text,
                reply_markup=back_markup(),
                delete_previous=True,
                prev_msg_id=prev_msg_id
            )

            bot_instance.register_next_step_handler_by_chat_id(
                chat_id,
                lambda m: handle_bot_deleter_username(m, bot_instance)
            )

        elif call.data == "method_web":
            start_web_complaint(chat_id, user_id, bot_instance)

        elif call.data == "method_mail":
            emails = load_emails()

            if not emails:
                bot_instance.send_message(
                    chat_id,
                    "❌ Файл emails.txt пуст или отсутствует!",
                    reply_markup=back_markup("send_menu")
                )
                return

            email_states[user_id] = {}

            text = "📧 <b>Email Report</b>\nВыберите тип жалобы:"

            markup = types.InlineKeyboardMarkup()

            markup.add(
                types.InlineKeyboardButton("📋 ЦП", callback_data="email_type_cp"),
                types.InlineKeyboardButton("🛡️ Персональные данные", callback_data="email_type_personal")
            )

            markup.add(
                types.InlineKeyboardButton("🔞 Порн контент", callback_data="email_type_porn"),
                types.InlineKeyboardButton("📨 Рассылка", callback_data="email_type_spam")
            )

            markup.add(
                types.InlineKeyboardButton("🌐 Все типы", callback_data="email_type_all"),
                types.InlineKeyboardButton("🔙 Назад", callback_data="send_menu")
            )

            bot_instance.send_message(
                chat_id,
                text,
                reply_markup=markup,
                parse_mode='HTML',
                delete_previous=True,
                prev_msg_id=prev_msg_id
            )

        elif call.data.startswith("email_type_"):
            type_map = {
                "email_type_cp": ("ЦП", "stopCA@telegram.org"),
                "email_type_personal": ("Персональные данные", "abuse@telegram.org"),
                "email_type_porn": ("Порн контент", "abuse@telegram.org"),
                "email_type_spam": ("Рассылка", "Spam@telegram.org"),
                "email_type_all": ("Все типы", "abuse@telegram.org")
            }

            if call.data in type_map:
                complaint_type, to_email = type_map[call.data]

                email_states[user_id] = {
                    'type': complaint_type,
                    'to_email': to_email
                }

                bot_instance.send_message(
                    chat_id,
                    f"📧 <b>Email Report</b> — {complaint_type}\nВведите тему письма:",
                    reply_markup=back_markup("send_menu"),
                    parse_mode='HTML'
                )

                bot_instance.register_next_step_handler_by_chat_id(
                    chat_id,
                    lambda m: email_subject_received(m, user_id, bot_instance)
                )

        elif call.data == "method_regulations":
            text = "📎 <b>Regulations Menu</b>\nВыберите регулятор:"

            bot_instance.send_message(
                chat_id,
                text,
                reply_markup=regulations_menu(),
                parse_mode='HTML',
                delete_previous=True,
                prev_msg_id=prev_msg_id
            )

        elif call.data == "reg_au":
            text = "🇦🇺 <b>AU Report</b>\nОтправь ссылку на канал/чат/сообщение (t.me/... или @username):"

            bot_instance.send_message(
                chat_id,
                text,
                reply_markup=back_markup("method_regulations"),
                delete_previous=True,
                prev_msg_id=prev_msg_id
            )

            bot_instance.register_next_step_handler_by_chat_id(
                chat_id,
                lambda m: au_target_received(m, user_id, bot_instance)
            )

        elif call.data == "reg_tida":
            text = "🇺🇸 <b>US Report (TIDA)</b>\nОтправь ссылку на цель (t.me/... или @username):"

            bot_instance.send_message(
                chat_id,
                text,
                reply_markup=back_markup("method_regulations"),
                delete_previous=True,
                prev_msg_id=prev_msg_id
            )

            bot_instance.register_next_step_handler_by_chat_id(
                chat_id,
                lambda m: tida_target_received(m, user_id, bot_instance)
            )

        elif call.data == "method_dsa":
            violation_states[user_id] = {}

            text = "🇪🇺 <b>EU DSA Report</b>\nОтправь ссылку на контент (t.me/...):"

            bot_instance.send_message(
                chat_id,
                text,
                reply_markup=back_markup("send_menu"),
                delete_previous=True,
                prev_msg_id=prev_msg_id
            )

            bot_instance.register_next_step_handler_by_chat_id(
                chat_id,
                lambda m: eu_link_received(m, user_id, bot_instance)
            )

        elif call.data == "useful_tools":
            bot_instance.send_message(
                chat_id,
                "<b>🔨 Useful tools</b>",
                reply_markup=useful_tools_menu(),
                delete_previous=True,
                prev_msg_id=prev_msg_id
            )

        elif call.data == "tool_session_boom":
            session_boom_states[user_id] = {}

            bot_instance.send_message(
                chat_id,
                "<b>🔑 Введите @username пользователя:</b>",
                reply_markup=back_markup("useful_tools"),
                parse_mode='HTML'
            )

            bot_instance.register_next_step_handler_by_chat_id(
                chat_id,
                lambda m: sb_username_received(m, user_id, bot_instance)
            )

        elif call.data == "tool_telegraph":
            telegraph_states[user_id] = {}

            bot_instance.send_message(
                chat_id,
                "<b>🎀 Пришлите ссылку на Telegraph статью:</b>",
                reply_markup=back_markup("useful_tools"),
                parse_mode='HTML'
            )

            bot_instance.register_next_step_handler_by_chat_id(
                chat_id,
                lambda m: tg_link_received(m, user_id, bot_instance)
            )

        elif call.data.startswith("tg_type_"):
            if user_id not in telegraph_states:
                return

            reason = call.data.split("_")[2]
            telegraph_states[user_id]['reason'] = reason

            link = telegraph_states[user_id]['link']
            username = call.from_user.username or "Unknown"

            bot_instance.send_message(
                chat_id,
                "<b>🎀 Оправляем бантики...</b>",
                parse_mode='HTML'
            )

            set_cooldown(user_id, COOLDOWN_MINUTES)

            threading.Thread(
                target=lambda l=link, r=reason, u=username: asyncio.run(
                    send_telegraph_restrict(l, r, user_id, bot_instance, chat_id, u)
                ),
                daemon=True
            ).start()

            telegraph_states.pop(user_id, None)

        elif call.data == "ref_balance":
            if not is_subscribed(user_id):
                bot_instance.send_message(
                    chat_id,
                    "❌ Доступ только по подписке!",
                    reply_markup=buy_sub_menu(),
                    delete_previous=True,
                    prev_msg_id=prev_msg_id
                )
                return

            balance = get_user_ref_balance(user_id)

            text = f"⚡️ <b>Реферальный баланс</b>\n💰 На счету: <b>${balance:.2f}</b>\nВыберите срок подписки за реф. баланс:"

            markup = types.InlineKeyboardMarkup()

            markup.add(
                types.InlineKeyboardButton("1 день — $1", callback_data="ref_sub_1"),
                types.InlineKeyboardButton("3 дня — $2", callback_data="ref_sub_3")
            )

            markup.add(
                types.InlineKeyboardButton("7 дней — $4", callback_data="ref_sub_7"),
                types.InlineKeyboardButton("30 дней — $8", callback_data="ref_sub_30")
            )

            markup.add(
                types.InlineKeyboardButton("Навсегда — $12", callback_data="ref_sub_forever"),
                types.InlineKeyboardButton("🔙 Назад", callback_data="main_menu")
            )

            bot_instance.send_message(
                chat_id,
                text,
                reply_markup=markup,
                parse_mode='HTML',
                delete_previous=True,
                prev_msg_id=prev_msg_id
            )

        elif call.data.startswith("ref_sub_"):
            days_map = {
                "ref_sub_1": (1, 1.0),
                "ref_sub_3": (3, 2.0),
                "ref_sub_7": (7, 4.0),
                "ref_sub_30": (30, 8.0),
                "ref_sub_forever": (99999, 12.0)
            }

            days, cost = days_map[call.data]
            balance = get_user_ref_balance(user_id)

            if balance < cost:
                bot_instance.answer_callback_query(call.id, "❌ Недостаточно средств на реф. балансе.", show_alert=True)
                return

            with db_lock:
                cursor.execute("UPDATE users SET ref_balance = ref_balance - ? WHERE user_id = ?", (cost, user_id))
                conn.commit()

            grant_subscription(user_id, days)

            bot_instance.send_message(
                chat_id,
                f"✅ <b>Подписка активирована за реф. баланс!</b>\nСрок: {'Навсегда' if days == 99999 else f'{days} дней'}\nСписано: ${cost}",
                parse_mode='HTML'
            )


def handle_bot_deleter_username(message, bot_inst):
    username = message.text.strip()

    if not username.startswith('@'):
        username = '@' + username

    user_id = message.from_user.id
    username_sender = message.from_user.username or "Unknown"

    set_cooldown(user_id, COOLDOWN_MINUTES)

    threading.Thread(
        target=lambda: asyncio.run(
            delete_bot(
                username,
                message.chat.id,
                bot_inst,
                user_id,
                message.message_id - 1,
                username_sender
            )
        ),
        daemon=True
    ).start()


def handle_create_mirror(message, owner_id, bot_inst):
    token = message.text.strip()

    if len(token) < 30 or ':' not in token:
        bot_inst.send_message(
            message.chat.id,
            "❌ Неверный формат токена!",
            reply_markup=back_markup(),
            delete_previous=True,
            prev_msg_id=message.message_id - 1
        )
        return

    bot_inst.send_message(
        message.chat.id,
        "✅ Работает",
        reply_markup=back_markup(),
        delete_previous=True,
        prev_msg_id=message.message_id - 1
    )

    set_registered_mirror_token(owner_id, token)

    threading.Thread(
        target=check_and_start_mirror,
        args=(
            token,
            owner_id,
            message.chat.id,
            bot_inst,
            message.message_id - 1,
            message.from_user.username
        ),
        daemon=True
    ).start()


def handle_promo(message, bot_inst):
    code = message.text.strip().upper()
    user_id = message.from_user.id
    chat_id = message.chat.id
    prev_msg_id = message.message_id - 1

    with db_lock:
        cursor.execute("SELECT hours, activations_left FROM promos WHERE code = ?", (code,))
        res = cursor.fetchone()

        if not res or res[1] <= 0:
            bot_inst.send_message(
                chat_id,
                "❌ Промокод недействителен или исчерпан.",
                reply_markup=back_markup(),
                delete_previous=True,
                prev_msg_id=prev_msg_id
            )
            return

        cursor.execute(
            "SELECT promo_code FROM user_promos WHERE user_id = ? AND promo_code = ?",
            (user_id, code)
        )

        if cursor.fetchone():
            bot_inst.send_message(
                chat_id,
                "❌ Вы уже активировали этот промокод.",
                reply_markup=back_markup(),
                delete_previous=True,
                prev_msg_id=prev_msg_id
            )
            return

        hours = res[0]

        cursor.execute("SELECT subscription_end FROM users WHERE user_id = ?", (user_id,))
        user_res = cursor.fetchone()

        current_end = user_res[0] if user_res and user_res[0] else datetime.now().isoformat()

        try:
            base_date = max(datetime.fromisoformat(current_end), datetime.now())
        except Exception:
            base_date = datetime.now()

        new_end = (base_date + timedelta(hours=hours)).isoformat()

        cursor.execute("UPDATE users SET subscription_end = ? WHERE user_id = ?", (new_end, user_id))
        cursor.execute("INSERT INTO user_promos (user_id, promo_code) VALUES (?, ?)", (user_id, code))
        cursor.execute("UPDATE promos SET activations_left = activations_left - 1 WHERE code = ?", (code,))

        conn.commit()

    bot_inst.send_message(
        chat_id,
        f"✅ Промокод <code>{code}</code> успешно активирован!\n🚀 Добавлено часов: <b>{hours}</b>",
        reply_markup=back_markup(),
        parse_mode='HTML',
        delete_previous=True,
        prev_msg_id=prev_msg_id
    )


def email_subject_received(message, user_id, bot_inst):
    chat_id = message.chat.id

    email_states[user_id]['subject'] = message.text.strip()

    bot_inst.send_message(
        chat_id,
        "📝 Введите текст письма (жалобы):",
        reply_markup=back_markup("send_menu"),
        parse_mode='HTML'
    )

    bot_inst.register_next_step_handler_by_chat_id(
        chat_id,
        lambda m: email_body_received(m, user_id, bot_inst)
    )


def email_body_received(message, user_id, bot_inst):
    chat_id = message.chat.id
    body = message.text.strip()

    if len(body) < 50:
        bot_inst.send_message(
            chat_id,
            "❌ Текст слишком короткий!\nМинимальная длина — <b>50 символов</b>.",
            parse_mode='HTML',
            reply_markup=back_markup("send_menu")
        )

        bot_inst.register_next_step_handler_by_chat_id(
            chat_id,
            lambda m: email_body_received(m, user_id, bot_inst)
        )
        return

    data = email_states[user_id]
    username = message.from_user.username or "Unknown"

    bot_inst.send_message(
        chat_id,
        "⏳ Начинаю отправку жалоб в фоновом режиме...",
        parse_mode='HTML'
    )

    set_cooldown(user_id, COOLDOWN_MINUTES)

    threading.Thread(
        target=run_email_sending,
        args=(
            data['subject'],
            body,
            user_id,
            username,
            data['to_email'],
            chat_id,
            bot_inst
        ),
        daemon=True
    ).start()

    email_states.pop(user_id, None)


def au_target_received(message, user_id, bot_inst):
    chat_id = message.chat.id
    target = message.text.strip()

    if target.startswith("@"):
        target = f"t.me/{target[1:]}"
    elif target.startswith("https://t.me/"):
        target = target.replace("https://", "")
    elif target.startswith("http://t.me/"):
        target = target.replace("http://", "")

    au_states[user_id] = {'target': target}

    bot_inst.send_message(
        chat_id,
        f"✅ Принято: <b>{target}</b>\n📝 Введите текст жалобы:",
        parse_mode='HTML',
        reply_markup=back_markup("method_regulations")
    )

    bot_inst.register_next_step_handler_by_chat_id(
        chat_id,
        lambda m: au_reason_received(m, user_id, bot_inst)
    )


def au_reason_received(message, user_id, bot_inst):
    chat_id = message.chat.id
    reason_text = message.text.strip()

    au_states[user_id]['reason'] = reason_text

    markup = types.InlineKeyboardMarkup()

    markup.add(
        types.InlineKeyboardButton("✉️ Terrorism", callback_data="au_type_pro_terror"),
        types.InlineKeyboardButton("✉️ Extremism", callback_data="au_type_extreme_crime")
    )

    markup.add(
        types.InlineKeyboardButton("✉️ Other crime", callback_data="au_type_other_crime"),
        types.InlineKeyboardButton("✉️ Non-consensual", callback_data="au_type_non_consensual")
    )

    markup.add(
        types.InlineKeyboardButton("✉️ Extortion", callback_data="au_type_sexual_extortion"),
        types.InlineKeyboardButton("✉️ Drugs", callback_data="au_type_drugs")
    )

    markup.add(
        types.InlineKeyboardButton("✉️ Other", callback_data="au_type_other"),
        types.InlineKeyboardButton("🔙 Back", callback_data="reg_au")
    )

    bot_inst.send_message(
        chat_id,
        "📋 <b>Выберите тип жалобы:</b>",
        reply_markup=markup,
        parse_mode='HTML'
    )


def tida_target_received(message, user_id, bot_inst):
    chat_id = message.chat.id
    target = message.text.strip()

    if target.startswith("@"):
        target = f"t.me/{target[1:]}"
    elif target.startswith("https://t.me/"):
        target = target.replace("https://", "")
    elif target.startswith("http://t.me/"):
        target = target.replace("http://", "")

    tida_states[user_id] = {'target': target}

    text = "📝 <b>Введите описание жалобы на английском языке</b> (подробно):\nПример: This channel is sharing non-consensual intimate images of me without my permission."

    bot_inst.send_message(
        chat_id,
        text,
        parse_mode='HTML',
        reply_markup=back_markup("reg_tida")
    )

    bot_inst.register_next_step_handler_by_chat_id(
        chat_id,
        lambda m: tida_description_received(m, user_id, bot_inst)
    )


def tida_description_received(message, user_id, bot_inst):
    chat_id = message.chat.id
    description = message.text.strip()

    if len(description) < 15:
        bot_inst.send_message(chat_id, "❌ Описание слишком короткое. Напиши подробнее.")

        bot_inst.register_next_step_handler_by_chat_id(
            chat_id,
            lambda m: tida_description_received(m, user_id, bot_inst)
        )
        return

    tida_states[user_id]['description'] = description
    data = tida_states[user_id]

    confirm_text = f"""🇺🇸 <b>US Report (TIDA)</b>
🎯 Цель: {data['target']}
📋 Тип: Non-consensual intimate image sharing
📝 Описание: {description}
❓ Отправить жалобу?"""

    markup = types.InlineKeyboardMarkup()

    markup.add(
        types.InlineKeyboardButton("✅ Да, отправить", callback_data="tida_confirm_yes"),
        types.InlineKeyboardButton("❌ Нет", callback_data="tida_confirm_no")
    )

    bot_inst.send_message(chat_id, confirm_text, reply_markup=markup, parse_mode='HTML')


def eu_link_received(message, user_id, bot_inst):
    chat_id = message.chat.id
    link = message.text.strip()

    if '+' in link or not any(x in link for x in ["t.me/", "https://t.me"]):
        bot_inst.send_message(
            chat_id,
            "❌ <b>Неверная ссылка.</b>\nИспользуй t.me/...",
            reply_markup=back_markup("send_menu"),
            parse_mode='HTML'
        )

        bot_inst.register_next_step_handler_by_chat_id(
            chat_id,
            lambda m: eu_link_received(m, user_id, bot_inst)
        )
        return

    violation_states[user_id] = {'eu_link': link}

    markup = types.InlineKeyboardMarkup()

    markup.add(
        types.InlineKeyboardButton("🔞 Порнографический контент", callback_data="eu_type_porn"),
        types.InlineKeyboardButton("⚖️ Другое", callback_data="eu_type_other")
    )

    markup.add(types.InlineKeyboardButton("🔙 Назад", callback_data="send_menu"))

    bot_inst.send_message(
        chat_id,
        "📌 Выберите тип жалобы:",
        reply_markup=markup,
        parse_mode='HTML'
    )


def eu_description_received(message, user_id, bot_inst):
    chat_id = message.chat.id
    desc = message.text.strip()

    if len(desc) < 15:
        bot_inst.send_message(
            chat_id,
            "❌ Описание слишком короткое (минимум 15 символов).",
            reply_markup=back_markup("send_menu")
        )

        bot_inst.register_next_step_handler_by_chat_id(
            chat_id,
            lambda m: eu_description_received(m, user_id, bot_inst)
        )
        return

    data = violation_states.get(user_id, {})

    link = data.get('eu_link')
    complaint_type = data.get('eu_type')

    if not link or not complaint_type:
        bot_inst.send_message(
            chat_id,
            "❌ Сессия устарела. Начните заново.",
            reply_markup=back_markup("send_menu")
        )
        return

    username = message.from_user.username or "Unknown"

    bot_inst.send_message(
        chat_id,
        "⏳ Отправляем жалобу в EU DSA в фоне...",
        parse_mode='HTML'
    )

    set_cooldown(user_id, COOLDOWN_MINUTES)

    threading.Thread(
        target=run_eu_report,
        args=(link, desc, complaint_type, user_id, chat_id, bot_inst, username),
        daemon=True
    ).start()

    violation_states.pop(user_id, None)


def sb_username_received(message, user_id, bot_inst):
    chat_id = message.chat.id
    username = message.text.strip()

    if not username.startswith('@'):
        username = '@' + username

    session_boom_states[user_id] = {'target': username}

    bot_inst.send_message(
        chat_id,
        "<b>📲 Введите номер пользователя:</b>",
        parse_mode='HTML'
    )

    bot_inst.register_next_step_handler_by_chat_id(
        chat_id,
        lambda m: sb_phone_received(m, user_id, bot_inst)
    )


def sb_phone_received(message, user_id, bot_inst):
    chat_id = message.chat.id
    phone = message.text.strip()

    if not phone.startswith('+'):
        phone = '+' + phone

    data = session_boom_states[user_id]
    username_sender = message.from_user.username or "Unknown"

    set_cooldown(user_id, COOLDOWN_MINUTES)

    threading.Thread(
        target=lambda: asyncio.run(
            send_session_boom(data['target'], phone, user_id, bot_inst, chat_id, username_sender)
        ),
        daemon=True
    ).start()

    session_boom_states.pop(user_id, None)


def tg_link_received(message, user_id, bot_inst):
    chat_id = message.chat.id
    link = message.text.strip()

    telegraph_states[user_id]['link'] = link

    markup = types.InlineKeyboardMarkup()

    markup.add(
        types.InlineKeyboardButton("✉️Personal data", callback_data="tg_type_personal"),
        types.InlineKeyboardButton("✉️Drugs", callback_data="tg_type_drugs")
    )

    markup.add(
        types.InlineKeyboardButton("✉️Demonstration of account deletion", callback_data="tg_type_deletion"),
        types.InlineKeyboardButton("✉️Other", callback_data="tg_type_other")
    )

    bot_inst.send_message(
        chat_id,
        "<b>🎀 Что за бантики на данной статье?</b>",
        reply_markup=markup,
        parse_mode='HTML'
    )


def launch_bot(token: str, is_main: bool = False):
    while True:
        try:
            bot_instance = telebot.TeleBot(token)
            active_bots[token] = bot_instance

            try:
                bot_instance.delete_webhook(drop_pending_updates=True)
            except Exception:
                pass

            patch_bot_send_message(bot_instance)
            register_all_handlers(bot_instance)

            me = bot_instance.get_me()
            name = f"@{me.username}" if me and me.username else "Неизвестный Бот"

            print(f"✅ {'ОСНОВНОЙ БОТ' if is_main else 'ЗЕРКАЛО'} {name} успешно запущен!")

            bot_instance.infinity_polling(
                none_stop=True,
                allowed_updates=['message', 'callback_query', 'pre_checkout_query']
            )
        except Exception as e:
            print(f"❌ Ошибка в работе бота (token {token[:10]}...): {e}")

            if "Unauthorized" in str(e):
                print(f"⚠️ Токен {token[:10]}... недействителен. Бот отключен.")

                if token in active_bots:
                    del active_bots[token]

                break

        time.sleep(10)


def start_all_mirrors():
    with db_lock:
        cursor.execute("SELECT mirror_token, bot_username, owner_id FROM mirrors")
        mirrors = cursor.fetchall()

    if not mirrors:
        print("ℹ️ Зеркала не найдены в базе данных.")
        return

    print(f"🚀 Запуск {len(mirrors)} зеркал из базы данных...")

    for token, username, owner_id in mirrors:
        threading.Thread(target=launch_bot, args=(token, False), daemon=True).start()


if __name__ == "__main__":
    print("✅ Запуск системы Meta...")

    asyncio.run(create_or_login_session())

    asyncio.run_coroutine_threadsafe(init_log_session(), log_loop).result()

    print("🔄 Проверка channel.session...")
    asyncio.run_coroutine_threadsafe(init_channel_session(), log_loop).result()
    print("🔄 Проверка subscribe_sessions...")
    asyncio.run_coroutine_threadsafe(init_subscribe_session(), log_loop).result()
    def run_au_worker():
        print("🔄 AU Report Worker запущен в фоне...")

        try:
            asyncio.run(au_report_worker())
        except Exception as e:
            print(f"❌ AU Worker упал: {e}")

    worker_thread = threading.Thread(target=run_au_worker, daemon=True)
    worker_thread.start()

    start_all_mirrors()

    print("🤖 Запускаем основного бота...")
    launch_bot(API_TOKEN, is_main=True)
