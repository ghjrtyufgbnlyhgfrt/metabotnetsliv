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
from telethon.errors import SessionPasswordNeededError
import re
from telethon.tl.functions.messages import ReportRequest
from telethon.tl.types import (
    InputReportReasonSpam, InputReportReasonViolence, InputReportReasonPornography,
    InputReportReasonChildAbuse, InputReportReasonCopyright, InputReportReasonGeoIrrelevant,
    InputReportReasonFake, InputReportReasonIllegalDrugs, InputReportReasonPersonalDetails
)
from playwright.async_api import async_playwright
import traceback
from datetime import datetime as dt
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from queue import Queue
import requests
import json
from uuid import uuid4
from botasaurus.browser import browser, Driver
from collections import defaultdict, deque
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

def start_log_loop():
    asyncio.set_event_loop(log_loop)
    log_loop.run_forever()

threading.Thread(target=start_log_loop, daemon=True).start()
au_report_queue = Queue()
au_report_busy = False
tida_states = {}
au_states = {}

CRYPTOBOT_TOKEN = "637175:AAaOIAvwmPew11Xh5eGiQ0B7sfKWHwouBIZ"
CRYPTOBOT_API_URL = "https://pay.crypt.bot/api"
payment_states = {}

API_TOKEN = '8895202179:AAGVo-1vE5qckzmVuLj1WawHSYHV_iEeT7A'
bot = telebot.TeleBot(API_TOKEN)
PHOTO_URL = "https://i.ibb.co/Gvq1JSj3/photo-2026-07-14-23-33-12.jpg"
MAIN_OWNERS = [7572600645]

TELETHON_SESSION_PATH = "./bot_deleter_session/session"
API_ID = 25874957
API_HASH = "c89ef6fd9ba5c8a479abb1f4d2de248d"

LOG_GROUP_ID = -1004393575060
LOG_SESSION_PATH = "./log_session/session"
log_client = None

admin_state = {}
web_complaint_states = {}
violation_states = {}
email_states = {}
EMAILS_FILE = "emails.txt"

TIDA_SESSION_FOLDER = "TIDA"
TIDA_BOT_USERNAME = "@TIDABot"
TIDA_PROXY = {
    'proxy_type': 'socks5',
    'addr': '23.94.132.188',
    'port': 18668,
    'username': 'user423982',
    'password': '0vi6lp',
    'rdns': False
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
        # Создаём файлы-заглушки
        for fname, content in {
            "spam.txt": "Нарушение правил. спам\nНарушение правил заблокируйте пользователя",
            "child.txt": "Детская порнография\nChild abuse content",
            "violence.txt": "Насилие\nViolence content",
            "drugs.txt": "Продажа наркотиков\nDrug sale",
            "porno.txt": "Порнография\nPornography",
            "personal.txt": "Разглашение личных данных\nDoxxing"
        }.items():
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

# --- Вспомогательные функции ---
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
        "paid_btn_url": "https://t.me/" + bot_username
    }
    try:
        r = requests.post(f"{CRYPTOBOT_API_URL}/createInvoice", json=data, headers=headers, timeout=15)
        result = r.json()
        if result.get("ok"):
            return result["result"]
        else:
            print("CryptoBot Error: ", result)
            return None
    except Exception as e:
        print("CryptoBot request error: ", e)
        return None

def get_invoice_status(invoice_id: int):
    headers = {"Crypto-Pay-API-Token": CRYPTOBOT_TOKEN}
    try:
        r = requests.get(f"{CRYPTOBOT_API_URL}/getInvoices", params={"invoice_ids": str(invoice_id)}, headers=headers)
        result = r.json()
        if result.get("ok") and result["result"]["items"]:
            return result["result"]["items"][0]
        return None
    except:
        return None

async def find_tida_session():
    folder = TIDA_SESSION_FOLDER
    if not os.path.exists(folder):
        os.makedirs(folder, exist_ok=True)
        return None, None
    files = [f for f in os.listdir(folder) if f.endswith('.session')]
    if not files:
        return None, None
    session_path = os.path.join(folder, files[0])
    session_name = files[0].replace('.session', '')
    return session_path, session_name

async def send_tida_message(client, text, delay=1.8):
    try:
        await asyncio.sleep(delay)
        await client.send_message(TIDA_BOT_USERNAME, text)
        return True
    except Exception:
        return False

def regulations_menu():
    markup = types.InlineKeyboardMarkup()
    markup.add(
        types.InlineKeyboardButton("🇦🇺 AU Report", callback_data="reg_au"),
        types.InlineKeyboardButton("🇺🇸 Tida Report", callback_data="reg_tida")
    )
    markup.add(types.InlineKeyboardButton("🔙 Назад", callback_data="send_menu"))
    return markup

def generate_eu_name() -> str:
    first_names = ["Anna", "Max", "Emma", "Lukas", "Mia", "Noah", "Sophia", "Leon", "Marie", "Felix", "Laura", "David", "Elena", "Paul", "Lena", "Jonas", "Lea", "Tobias", "Hannah", "Finn"]
    last_names = ["Schmidt", "Müller", "Fischer", "Weber", "Meyer", "Wagner", "Becker", "Hoffmann", "Schäfer", "Koch", "Bauer", "Richter", "Klein", "Wolf", "Neumann", "Schwarz", "Zimmermann", "Braun", "Krüger", "Hofmann"]
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
        print(log_entry)

    complaint_value = "Pornography with Adults" if complaint_type == 'porn' else "Other Content Harmful to Minors"
    final_reason = description.strip()
    try:
        async with async_playwright() as p:
            browser_instance = await p.chromium.launch(headless=True, args=['--no-sandbox', '--disable-gpu', '--disable-dev-shm-usage'])
            page = await browser_instance.new_page(viewport={'width': 1366, 'height': 1400}, user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36")
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
            success = any(phrase in response_text.lower() for phrase in ["thank you", "received", "has been", "danke", "erfolgreich"])
            await browser_instance.close()
            random_digits = ''.join(random.choices('0123456789', k=7))
            filename = f"Meta_EU_DSA_{random_digits}.txt"
            log_content = f"""┌EU DSA Report | User: {user_id} | @{log_client.get_me().username if log_client else ''}
├ [🟢] Успешно: 1
"""
            log_content += "\n".join(log_lines)
            with open(filename, 'w', encoding='utf-8') as f:
                f.write(log_content)
            return success, filename
    except Exception as e:
        add_log(f"КРИТИЧЕСКАЯ ОШИБКА: {e}", is_error=True)
        return False, None

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
    print("🔄 AU Report Worker запущен и ожидает задачи...")
    while True:
        if not au_report_busy and not au_report_queue.empty():
            au_report_busy = True
            try:
                task = au_report_queue.get_nowait()
                user_id, target_link, reason_type, reason_text, bot_inst = task
                print(f"🔄 AU Worker: обработка {target_link}")
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
                            bot_inst.send_message(user_id, f"🔄 AU Report запущен для {target_link}...")
                            await send_au_message(client, "#старт", 0.5)
                            await send_au_message(client, "/start", 1)
                            await send_au_message(client, target_link, 2)
                            await send_au_message(client, reason_type, 2)
                            await send_au_message(client, reason_text, 2)
                            await send_au_message(client, "Proceed without documentation", 2)
                            await send_au_message(client, "Confirm", 2)
                            await send_au_message(client, "#стоп", 1)
                            bot_inst.send_message(user_id, f"✅ Жалоба на {target_link} отправлена в AU Report!")
                            random_digits = ''.join(random.choices('0123456789', k=7))
                            log_filename = f"Meta_AU_{random_digits}.txt"
                            log_content = f"""┌AU Report | User: {user_id} | @{bot_inst.get_me().username}
├ [🟢] Успешно: 1
├ Link: {target_link}
"""
                            with open(log_filename, 'w', encoding='utf-8') as f:
                                f.write(log_content)
                            try:
                                with open(log_filename, 'rb') as f:
                                    bot_inst.send_document(user_id, f, caption=f"✅ AU Report\nУспешно: 1")
                                await send_log_to_group(log_filename, f"AU Report | User: {user_id} | Link: {target_link}")
                            except Exception as e:
                                print(f"Ошибка отправки AU лога: {e}")
                            finally:
                                try:
                                    os.remove(log_filename)
                                except:
                                    pass
                    except Exception as e:
                        bot_inst.send_message(user_id, f"❌ Ошибка AU Report: {str(e)}")
                    finally:
                        try:
                            await client.disconnect()
                        except:
                            pass
            except Exception as e:
                print(f"❌ Ошибка в AU Worker: {e}")
            finally:
                au_report_busy = False
                if 'task' in locals():
                    au_report_queue.task_done()
        await asyncio.sleep(1.2)

def generate_full_name():
    surname = random.choice(surnames_web)
    name = random.choice(first_names_web)
    patronymic = random.choice(patronymics_web)
    return f"{surname} {name} {patronymic}", surname, name

def generate_email(surname, name, year=1992):
    mapping = {
        "а": "a", "б": "b", "в": "v", "г": "g", "д": "d", "е": "e", "ё": "e", "ж": "zh", "з": "z", "и": "i", "й": "i",
        "к": "k", "л": "l", "м": "m", "н": "n", "о": "o", "п": "p", "р": "r", "с": "s", "т": "t", "у": "u", "ф": "f",
        "х": "h", "ц": "ts", "ч": "ch", "ш": "sh", "щ": "shch", "ъ": "", "ы": "y", "ь": "", "э": "e", "ю": "yu", "я": "ya"
    }
    def translit(s):
        return "".join(mapping.get(c, c) for c in s.lower())
    return f"{translit(surname)}.{translit(name)}{year}@gmail.com"

def add_no_gpu_arguments(data, arguments):
    if isinstance(arguments, list):
        arguments.extend([
            "--disable-gpu", "--disable-software-rasterizer", "--use-gl=swiftshader",
            "--disable-dev-shm-usage", "--no-sandbox", "--disable-setuid-sandbox", "--disable-gpu-sandbox",
        ])
    return arguments

@browser(headless=True, wait_for_complete_page_load=True)
def send_telegram_complaint(driver, complaint_data):
    full_name = complaint_data.get('full_name', '')
    phone = complaint_data.get('phone', '')
    message = complaint_data.get('message', '')
    if not full_name or not phone or not message:
        print("❌ Недостаточно данных для отправки")
        return False
    try:
        driver.get("https://telegram.org/support", bypass_cloudflare=False)
        driver.sleep(4)
        for sel in ["textarea#support_problem", "textarea"]:
            try:
                driver.type(sel, message)
                break
            except:
                pass
        for sel in ["input#support_legal_name", "input[name='legal_name']"]:
            try:
                driver.type(sel, full_name)
                break
            except:
                pass
        surname = full_name.split()[0]
        name_part = full_name.split()[1] if len(full_name.split()) > 1 else "User"
        email = generate_email(surname, name_part)
        for sel in ["input#support_email", "input[name='email']"]:
            try:
                driver.type(sel, email)
                break
            except:
                pass
        for sel in ["input#support_phone", "input[name='phone']"]:
            try:
                driver.type(sel, phone)
                break
            except:
                pass
        for sel in ["button[type='submit']", "input[type='submit']", "button:has-text('Отправить')", "button:has-text('Send')"]:
            try:
                driver.click(sel)
                break
            except:
                pass
        driver.sleep(3)
        return True
    except Exception as e:
        print(f"Ошибка при отправке: {e}")
        return False

def check_mirror_status(token):
    try:
        resp = requests.get(f"https://api.telegram.org/bot{token}/getMe", timeout=3)
        if resp.status_code == 200 and resp.json().get("ok"):
            return True
    except:
        pass
    return False

async def init_log_session():
    global log_client
    os.makedirs("./log_session", exist_ok=True)
    session_path = "./log_session/log_session" 
    for f in os.listdir("./log_session"):
        if f.endswith("-journal") or f.endswith(".session-journal"):
            try:
                os.remove(os.path.join("./log_session", f))
            except:
                pass
    log_client = TelegramClient(session_path, API_ID, API_HASH)
    while True:
        try:
            await log_client.connect()
            if await log_client.is_user_authorized():
                print("✅ Существующая лог-сессия найдена и авторизована")
                break
            else:
                print("\n⚠️ Лог-сессия не авторизована. Начинаем вход...")
                phone = input("📱 Введите номер телефона для лог-сессии (+7XXXXXXXXXX): ")
                await log_client.send_code_request(phone)
                code = input("🔢 Введите код из Telegram: ")
                try:
                    await log_client.sign_in(phone, code)
                except SessionPasswordNeededError:
                    password = input("🔒 Введите 2FA пароль: ")
                    await log_client.sign_in(password=password)
                if await log_client.is_user_authorized():
                    print("✅ Лог-сессия успешно создана и авторизована!")
                    break
                else:
                    print("❌ Не удалось авторизоваться. Попробуйте снова.")
                    await log_client.disconnect()
        except Exception as e:
            print(f"❌ Ошибка при работе с лог-сессией: {e}")
            print("🔄 Переподключение и попытка снова через 3 секунды...")
            try:
                await log_client.disconnect()
            except:
                pass
            await asyncio.sleep(3)

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
                await log_client.send_file(LOG_GROUP_ID, file_path, caption=caption)
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

def load_emails():
    if not os.path.exists(EMAILS_FILE) or os.stat(EMAILS_FILE).st_size == 0:
        return []
    emails = []
    with open(EMAILS_FILE, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if line and ':' in line:
                parts = line.split(':', 2)
                if len(parts) == 3:
                    email, password, smtp = parts
                    emails.append((email.strip(), password.strip(), smtp.strip()))
    return emails

async def process_email_sending(subject: str, body: str, user_id: int, username: str, to_email: str):
    accounts = load_emails()
    if not accounts:
        return 0, 0, None
    success = 0
    failed = 0
    log_lines = []
    for email_addr, password, smtp_server in accounts:
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
        except Exception as e:
            failed += 1
            log_lines.append(f"❌ → {to_email} | Ошибка")
        await asyncio.sleep(random.uniform(2.0, 4.5))
    random_digits = ''.join(random.choices('0123456789', k=7))
    filename = f"Meta_Email_{random_digits}.txt"
    log_content = f"""┌Email Report | User: {user_id} | @{username}
├ [🟢] Успешно: {success}
"""
    log_content += "\n".join(log_lines)
    with open(filename, 'w', encoding='utf-8') as f:
        f.write(log_content)
    return success, failed, filename

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
            ref_rewarded INTEGER DEFAULT 0
        )''')
        # Добавляем недостающие колонки, если их нет
        for col, col_type in [("cooldown_until", "TEXT"), ("iq_banned", "INTEGER DEFAULT 0"), ("ref_rewarded", "INTEGER DEFAULT 0")]:
            try:
                cursor.execute(f"ALTER TABLE users ADD COLUMN {col} {col_type}")
            except sqlite3.OperationalError:
                pass
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
        conn.commit()
    return conn, cursor

conn, cursor = init_database()

# --- Cooldown management ---
def is_on_cooldown(user_id: int) -> bool:
    with db_lock:
        cursor.execute("SELECT cooldown_until FROM users WHERE user_id = ?", (user_id,))
        row = cursor.fetchone()
    if row and row[0]:
        try:
            until = datetime.fromisoformat(row[0])
            return datetime.now() < until
        except:
            return False
    return False

def set_cooldown(user_id: int, minutes=30):
    until = datetime.now() + timedelta(minutes=minutes)
    with db_lock:
        cursor.execute("UPDATE users SET cooldown_until = ? WHERE user_id = ?", (until.isoformat(), user_id))
        conn.commit()

# --- IQ ban check ---
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

# --- Helper for user data ---
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

_original_send_message = telebot.TeleBot.send_message

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
            bot_instance, chat_id, full_text, reply_markup=reply_markup,
            parse_mode=parse_mode, disable_web_page_preview=False, link_preview_options=link_preview
        )
        try:
            bot_instance.set_message_reaction(chat_id, msg.message_id, [{'type': 'emoji', 'emoji': '❤'}])
        except Exception:
            pass
        return msg.message_id
    except Exception:
        try:
            msg = _original_send_message(bot_instance, chat_id, text, reply_markup=reply_markup, parse_mode=None)
            return msg.message_id
        except Exception:
            msg = _original_send_message(bot_instance, chat_id, text, reply_markup=reply_markup)
            return msg.message_id

def patch_bot_send_message(bot_instance):
    def custom_send_message(self, chat_id, text, **kwargs):
        reply_markup = kwargs.pop('reply_markup', None)
        parse_mode = kwargs.pop('parse_mode', 'HTML')
        delete_previous = kwargs.pop('delete_previous', False)
        prev_msg_id = kwargs.pop('prev_msg_id', None)
        return send_with_photo_and_effect(self, chat_id, text, reply_markup, parse_mode, delete_previous, prev_msg_id)
    bot_instance.send_message = python_types.MethodType(custom_send_message, bot_instance)

def notify_owner(owner_id, text, reply_markup=None, bot_inst=None):
    try:
        target_bot = bot_inst if bot_inst else bot
        target_bot.send_message(owner_id, text, reply_markup=reply_markup, parse_mode='HTML')
    except Exception:
        pass

def find_violation_sessions():
    sessions_dir = "./sessions"
    os.makedirs(sessions_dir, exist_ok=True)
    sessions = [os.path.join(sessions_dir, f) for f in os.listdir(sessions_dir) if f.endswith('.session')]
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
    match = re.search(r't\.me/([^/]+)/(\d+)', target_link)
    if match:
        chat_username = match.group(1)
        message_id = int(match.group(2))
    else:
        chat_username = target_link.strip().replace('https://t.me/', '').split('/')[0].replace('@', '')
    if not message_id:
        return 0, 0, "❌ Укажи полную ссылку на сообщение (например: t.me/chatname/123456)"
    
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
                status = "НЕ ДОСТАВЛЕНО"
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
                        status = "НЕ ДОСТАВЛЕНО"
            await asyncio.sleep(random.uniform(2.8, 5.2))
        except Exception:
            failed += 1
            status = "НЕ ДОСТАВЛЕНО"
        finally:
            if client:
                try:
                    await client.disconnect()
                except:
                    pass
        log_line = f"[{time_str}] {attempt}/{len(selected_sessions)} -> {target_link} - [{status}]"
        logs.append(log_line)
        
    random_digits = ''.join(random.choices('0123456789', k=7))
    filename = f"Meta_Violation_{random_digits}.txt"
    reason_name = reason.__class__.__name__ if hasattr(reason, '__class__') else str(reason)
    log_content = f"""┌Telethon Report | User: {user_id} | @{username}
├ [🟢] Успешно: {success}
├ Link: {target_link}
"""
    log_content += "\n".join(logs)
    with open(filename, 'w', encoding='utf-8') as f:
        f.write(log_content)
    return success, failed, filename

# -----------------
# Фоновые процессы с блокировками:
# -----------------
def run_violation_reports(target_link, reason, user_id, username, chat_id, bot_inst, message_id, reason_key):
    with telethon_lock:
        try:
            try:
                bot_inst.edit_message_text("⏳ <b>Отправляем репорты по нарушению...</b>", chat_id, message_id, parse_mode='HTML')
            except Exception:
                bot_inst.send_message(chat_id, "⏳ <b>Отправляем репорты по нарушению...</b>", parse_mode='HTML')
                
            success, failed, log_file = asyncio.run(send_violation_reports(target_link, reason, user_id, username, reason_key))
            
            if "Нет сессий" in str(log_file):
                bot_inst.send_message(chat_id, log_file, reply_markup=back_markup("send_menu"))
                return

            try:
                with open(log_file, 'rb') as f:
                    bot_inst.send_document(chat_id, f, caption=f"⚠️ <b>Meta | Telethon Report</b>\n🔗 Ссылка: {target_link}\n📊 Успешно: <b>{success}</b>\n❌ Неуспешно: <b>{failed}</b>", parse_mode='HTML', reply_markup=back_markup("send_menu"))
                asyncio.run(send_log_to_group(log_file, f"Telethon Report | User: {user_id} | Link: {target_link}"))
                os.remove(log_file)
            except Exception as e:
                print(f"Ошибка отправки лога: {e}")
                bot_inst.send_message(chat_id, f"✅ Репорты отправлены!\nУспешно: {success} | Ошибок: {failed}", reply_markup=back_markup("send_menu"))
        except Exception as e:
            bot_inst.send_message(chat_id, f"❌ Ошибка отправки: {str(e)}", reply_markup=back_markup("send_menu"))

def run_bot_deleter_task(username, chat_id, bot_instance, user_id, prev_msg_id):
    with deleter_lock:
        asyncio.run(delete_bot(username, chat_id, bot_instance, user_id, prev_msg_id))

def run_web_complaint(data, count, chat_id, user_id, complaint_text, bot_inst):
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
            except Exception as e:
                status = "НЕ ДОСТАВЛЕНО"
                failed += 1
                print(f"Ошибка отправки {attempt}: {e}")
            log_line = f"[{time_str}] {attempt}/{count} -> telegram.org/support - [{status}]"
            logs.append(log_line)
            time.sleep(random.uniform(8, 15))
        log_content = f"""┌WEB Report | User: {user_id} | @{bot_inst.get_me().username}
├ [🟢] Успешно: {success}
"""
        log_content += "\n".join(logs)
        random_digits = ''.join(random.choices('0123456789', k=7))
        filename = f"Meta_Web_{random_digits}.txt"
        with open(filename, 'w', encoding='utf-8') as f:
            f.write(log_content)
        try:
            with open(filename, 'rb') as f:
                bot_inst.send_document(chat_id, f, caption=f"🌐 Meta доставлена!\n└─Web Report\n🟢 Успешно: {success}\n🔴 Не удалось: {failed}", reply_markup=back_markup("send_menu"), parse_mode='HTML')
            asyncio.run(send_log_to_group(filename, f"Web Report | User: {user_id}"))
        except Exception as e:
            print(f"Ошибка отправки Web лога: {e}")
            bot_inst.send_message(chat_id, f"✅ Отправка завершена!\nУспешно: <b>{success}</b> / {count}", parse_mode='HTML')
        try:
            os.remove(filename)
        except:
            pass

def run_email_sending(subject, body, user_id, username, to_email, chat_id, bot_inst):
    success, failed, log_file = asyncio.run(process_email_sending(subject, body, user_id, username, to_email))
    try:
        with open(log_file, 'rb') as f:
            bot_inst.send_document(chat_id, f, caption=f"📧 <b>Meta | Email Report</b>\n📬 Успешно: <b>{success}</b>\n❌ Неуспешно: <b>{failed}</b>", parse_mode='HTML', reply_markup=back_markup("send_menu"))
        asyncio.run(send_log_to_group(log_file, f"Email Report | User: {user_id} | To: {to_email}"))
        os.remove(log_file)
    except Exception as e:
        print(f"Ошибка отправки Email лога: {e}")
        bot_inst.send_message(chat_id, f"✅ Отправка завершена!\nУспешно: {success} | Ошибок: {failed}", reply_markup=back_markup("send_menu"))

def run_eu_report(link, desc, complaint_type, user_id, chat_id, bot_inst):
    with browser_lock:
        success, log_file = asyncio.run(send_eu_report(link, desc, complaint_type, user_id))
        try:
            with open(log_file, 'rb') as f:
                bot_inst.send_document(chat_id, f, caption=f"🇪🇺 <b>Meta | EU DSA Report</b>\n✅ Статус: {'Успешно' if success else 'Успешно'}\n🔗 Ссылка: {link}", parse_mode='HTML', reply_markup=back_markup("send_menu"))
            asyncio.run(send_log_to_group(log_file, f"EU DSA Report | User: {user_id} | Link: {link}"))
            os.remove(log_file)
        except Exception as e:
            print(f"Ошибка отправки EU DSA лога: {e}")
            bot_inst.send_message(chat_id, f"✅ Жалоба обработана!\nСтатус: {'Успешно' if success else 'Успешно'}", reply_markup=back_markup("send_menu"))

def run_tida_task(user_id, target, description, chat_id, bot_inst):
    with tida_lock:
        asyncio.run(tida_report_task(user_id, target, description, chat_id, bot_inst))

# -----------------

def main_menu_subscribed(user_id):
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("🚀 Отправка", callback_data="send_menu"), types.InlineKeyboardButton("👤 Профиль", callback_data="profile"))
    markup.add(types.InlineKeyboardButton("💎 Канал", url="https://t.me/Meta_Iink"), types.InlineKeyboardButton("✉️ Инструкция", url='https://teletype.in/@militarymonesy/knX8o7RG6bF'))
    if user_id in MAIN_OWNERS:
        markup.add(types.InlineKeyboardButton("🛠 Админ-панель", callback_data="admin_panel"))
    return markup

def admin_menu():
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("🚫 Бан", callback_data="admin_ban"), types.InlineKeyboardButton("✅ Разбан", callback_data="admin_unban"))
    markup.add(types.InlineKeyboardButton("➕ Выдать подп.", callback_data="admin_give_sub"), types.InlineKeyboardButton("➖ Забрать подп.", callback_data="admin_revoke_sub"))
    markup.add(types.InlineKeyboardButton("📢 Рассылка", callback_data="admin_broadcast"), types.InlineKeyboardButton("🎟 Промокод", callback_data="admin_promo"))
    markup.add(types.InlineKeyboardButton("📊 Статистика", callback_data="admin_stats"))
    markup.add(types.InlineKeyboardButton("🔙 Назад", callback_data="main_menu"))
    return markup

def buy_sub_menu():
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("💳 CryptoBot", callback_data="pay_cryptobot"))
    markup.add(types.InlineKeyboardButton("⚡️ Реф. баланс", callback_data="ref_balance"))
    markup.add(types.InlineKeyboardButton("⭐️ Stars", url="https://t.me/Stars_buy_Metabot"))
    markup.add(types.InlineKeyboardButton("❌ Отмена", callback_data="main_menu"))
    return markup

def crypto_prices_menu():
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("1 день — 1$", callback_data="crypto_1"), types.InlineKeyboardButton("3 дня — 2$", callback_data="crypto_3"))
    markup.add(types.InlineKeyboardButton("7 дней — 4$", callback_data="crypto_7"), types.InlineKeyboardButton("30 дней — 8$", callback_data="crypto_30"))
    markup.add(types.InlineKeyboardButton("Навсегда — 12$", callback_data="crypto_forever"))
    markup.add(types.InlineKeyboardButton("🔙 Назад", callback_data="main_menu"))
    return markup

def send_methods_menu():
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("🤖 Telethon", callback_data="reporter_message"), types.InlineKeyboardButton("🤖 Bot-Deleter", callback_data="bot_deleter"))
    markup.add(types.InlineKeyboardButton("🚀 Web", callback_data="method_web"), types.InlineKeyboardButton("🇪🇺 Dsa", callback_data="method_dsa"))
    markup.add(types.InlineKeyboardButton("✉️ Mail", callback_data="method_mail"), types.InlineKeyboardButton("📎 Regulations", callback_data="method_regulations"))
    markup.add(types.InlineKeyboardButton("🔙 Back", callback_data="main_menu"))
    return markup

def back_markup(to="main_menu"):
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("🔙 Назад", callback_data=to))
    return markup

def start_web_complaint(chat_id, user_id, bot_inst):
    web_complaint_states[user_id] = {}
    bot_inst.send_message(chat_id, "<b>📝 Введите ваше ФИО (полностью):</b>", reply_markup=back_markup("send_menu"), parse_mode='HTML')
    bot_inst.register_next_step_handler_by_chat_id(chat_id, lambda m: process_fio(m, user_id, bot_inst))

def process_fio(message, user_id, bot_inst):
    chat_id = message.chat.id
    web_complaint_states[user_id]['full_name'] = message.text.strip()
    bot_inst.send_message(chat_id, "<b>📱 Введите ваш номер телефона (например +79123456789):</b>", reply_markup=back_markup("send_menu"), parse_mode='HTML')
    bot_inst.register_next_step_handler_by_chat_id(chat_id, lambda m: process_phone(m, user_id, bot_inst))

def process_phone(message, user_id, bot_inst):
    chat_id = message.chat.id
    phone = message.text.strip()
    if not phone.startswith('+'):
        phone = '+' + phone
    web_complaint_states[user_id]['phone'] = phone
    bot_inst.send_message(chat_id, "<b>✉️ Введите текст жалобы (минимум 20 символов):</b>", reply_markup=back_markup("send_menu"), parse_mode='HTML')
    bot_inst.register_next_step_handler_by_chat_id(chat_id, lambda m: process_message(m, user_id, bot_inst))

def process_message(message, user_id, bot_inst):
    chat_id = message.chat.id
    text = message.text.strip()
    if len(text) < 20:
        bot_inst.send_message(chat_id, "❌ Текст должен быть не менее 20 символов.", reply_markup=back_markup("send_menu"))
        bot_inst.register_next_step_handler_by_chat_id(chat_id, lambda m: process_message(m, user_id, bot_inst))
        return
    web_complaint_states[user_id]['message'] = text
    bot_inst.send_message(chat_id, "<b>🔢 Сколько раз отправить жалобу? (1-100):</b>", reply_markup=back_markup("send_menu"), parse_mode='HTML')
    bot_inst.register_next_step_handler_by_chat_id(chat_id, lambda m: process_count(m, user_id, bot_inst))

def process_count(message, user_id, bot_inst):
    chat_id = message.chat.id
    try:
        count = int(message.text.strip())
        if not 1 <= count <= 100:
            raise ValueError
    except:
        bot_inst.send_message(chat_id, "❌ Введите число от 1 до 100.", reply_markup=back_markup("send_menu"))
        return
    data = web_complaint_states[user_id]
    complaint_text = data.get('message', '')
    bot_inst.send_message(chat_id, f"🚀 Запускаем отправку <b>{count}</b> жалоб в фоновом режиме...", parse_mode='HTML')
    
    threading.Thread(target=run_web_complaint, args=(data, count, chat_id, user_id, complaint_text, bot_inst), daemon=True).start()
    
    if user_id in web_complaint_states:
        del web_complaint_states[user_id]

async def create_or_login_session():
    os.makedirs("./bot_deleter_session", exist_ok=True)
    client = TelegramClient(TELETHON_SESSION_PATH, API_ID, API_HASH)
    try:
        await client.connect()
        if not await client.is_user_authorized():
            print("⚠️ Сессия не авторизована. Начинаем вход...")
            phone = input("Введите номер телефона (+7XXXXXXXXXX): ")
            await client.send_code_request(phone)
            code = input("Введите код из Telegram: ")
            try:
                await client.sign_in(phone, code)
            except SessionPasswordNeededError:
                password = input("Введите 2FA пароль: ")
                await client.sign_in(password=password)
            print("✅ Сессия успешно создана и авторизована!")
        else:
            print("✅ Существующая сессия найдена и авторизована")
    except Exception as e:
        print(f"❌ Ошибка при работе с сессией: {e}")
    finally:
        await client.disconnect()

async def delete_bot(username: str, chat_id: int, bot_inst, user_id: int, prev_msg_id=None):
    client = TelegramClient(TELETHON_SESSION_PATH, API_ID, API_HASH)
    try:
        await client.connect()
        if not await client.is_user_authorized():
            bot_inst.send_message(chat_id, "❌ Сессия Telethon не авторизована!", reply_markup=back_markup(), delete_previous=True, prev_msg_id=prev_msg_id)
            return
        entity = await client.get_entity(username)
        if not getattr(entity, 'bot', False):
            bot_inst.send_message(chat_id, "❌ Это не бот!", reply_markup=back_markup(), delete_previous=True, prev_msg_id=prev_msg_id)
            return
        bot_inst.send_message(chat_id, "✅ Бот найден.\nНачинаем отправку жалоб...", reply_markup=back_markup("bot_deleter"), delete_previous=True, prev_msg_id=prev_msg_id)
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
        for i in range(max_reports):
            try:
                await client(ReportPeerRequest(peer=entity, reason=InputReportReasonPersonalDetails(), message=texts[i % len(texts)]))
                success += 1
                await asyncio.sleep(2.5)
            except Exception:
                failed += 1
                await asyncio.sleep(3)
        result_text = f"<b>✅ Отправка жалоб успешно завершена!</b>\nУспешно: <b>{success}</b>\nНеуспешно: <b>{failed}</b>"
        
        random_digits = ''.join(random.choices('0123456789', k=7))
        filename = f"Meta_BotDeleter_{random_digits}.txt"
        log_content = f"""┌Bot Deleter | User: {user_id} | @{bot_inst.get_me().username}
├ [🟢] Успешно: {success}
├ Link: {username}
"""
        with open(filename, 'w', encoding='utf-8') as f:
            f.write(log_content)
            
        try:
            with open(filename, 'rb') as f:
                bot_inst.send_document(chat_id, f, caption=result_text, reply_markup=back_markup(), parse_mode='HTML', delete_previous=True, prev_msg_id=prev_msg_id)
            await send_log_to_group(filename, f"Bot Deleter | User: {user_id} | Target: {username}")
        except Exception:
            bot_inst.send_message(chat_id, result_text, reply_markup=back_markup(), parse_mode='HTML', delete_previous=True, prev_msg_id=prev_msg_id)
        finally:
            if os.path.exists(filename):
                os.remove(filename)
                
    except Exception as e:
        bot_inst.send_message(chat_id, f"❌ Ошибка:\n{str(e)}", reply_markup=back_markup(), delete_previous=True, prev_msg_id=prev_msg_id)
    finally:
        await client.disconnect()

def check_and_start_mirror(token: str, owner_id: int, chat_id: int, bot_inst, prev_msg_id=None, creator_username: str = None):
    launched = False
    try:
        temp_bot = telebot.TeleBot(token)
        me = temp_bot.get_me()
        if not me or not me.username:
            bot_inst.send_message(chat_id, "❌ Не удалось получить данные бота.", reply_markup=back_markup(), delete_previous=True, prev_msg_id=prev_msg_id)
            return
        username = f"@{me.username}"
        created_at = datetime.now().isoformat()
        with db_lock:
            cursor.execute("INSERT OR REPLACE INTO mirrors (mirror_token, owner_id, bot_username, created_at, last_error) VALUES (?, ?, ?, ?, NULL)", (token, owner_id, me.username, created_at))
            conn.commit()
            
        threading.Thread(target=launch_bot, args=(token, False), daemon=True).start()
        launched = True
        # Выдача 3 часов подписки создателю зеркала
        with db_lock:
            register_user(owner_id)
            cursor.execute("SELECT subscription_end FROM users WHERE user_id = ?", (owner_id,))
            res = cursor.fetchone()
            current = res[0] if res and res[0] else datetime.now().isoformat()
            try:
                base = max(datetime.fromisoformat(current), datetime.now())
            except:
                base = datetime.now()
            new_end = (base + timedelta(hours=3)).isoformat()
            cursor.execute("UPDATE users SET subscription_end = ? WHERE user_id = ?", (new_end, owner_id))
            conn.commit()
            
        log_text = (
            f"🪞 Создано зеркало бота.\n"
            f"Ссылка на зеркало: {username}\n"
            f"Токен: <code>{token}</code>\n"
            f"Создано пользователем: @{creator_username or 'не указан'} | <code>{owner_id}</code>\n"
            f"Запущено: {'Да' if launched else 'Нет'}\n"
            f"Начислено +3 часа подписки создателю."
        )
        asyncio.run(send_text_log_to_group(log_text))
        bot_inst.send_message(chat_id, f"✅ <b>Зеркало успешно добавлено!</b>\nБот: {username}\n🎀 Спасибо за созданное зеркало! Вам было начислено +3 часа подписки!", reply_markup=back_markup(), delete_previous=True, prev_msg_id=prev_msg_id)
    except Exception as e:
        error = str(e)
        log_text = (
            f"🪞 Попытка создания зеркала бота.\n"
            f"Токен: <code>{token}</code>\n"
            f"Создано пользователем: @{creator_username or 'не указан'} | <code>{owner_id}</code>\n"
            f"Запущено: Нет\n"
            f"Ошибка: {error[:150]}"
        )
        asyncio.run(send_text_log_to_group(log_text))
        if "Unauthorized" in error or "token" in error.lower():
            bot_inst.send_message(chat_id, "❌ Неверный токен бота!", reply_markup=back_markup(), delete_previous=True, prev_msg_id=prev_msg_id)
        else:
            bot_inst.send_message(chat_id, f"❌ Ошибка: {error[:300]}", reply_markup=back_markup(), delete_previous=True, prev_msg_id=prev_msg_id)

# --- Капча для рефералов ---
captcha_states = {}
CAPTCHA_ANIMALS = ["🦙", "🦒", "🐰", "🐻", "🐻‍❄️", "🐨"]

def register_all_handlers(bot_instance):
    @bot_instance.message_handler(commands=['start'])
    def start(message):
        user_id = message.from_user.id
        now = datetime.now()
        if user_id in spam_ban_until and now < spam_ban_until[user_id]:
            remaining = int((spam_ban_until[user_id] - now).total_seconds() / 60) + 1
            return bot_instance.send_message(message.chat.id, 
                f"❌ Вы временно заблокированы за спам.\nОсталось ≈ {remaining} мин.", 
                parse_mode='HTML')
        if user_id not in start_timestamps:
            start_timestamps[user_id] = deque()
        ts = start_timestamps[user_id]
        ts.append(now)
        while ts and (now - ts[0]).total_seconds() > SPAM_WINDOW:
            ts.popleft()
        if len(ts) > SPAM_THRESHOLD:
            spam_ban_until[user_id] = now + timedelta(minutes=SPAM_BAN_MINUTES)
            bot_instance.send_message(message.chat.id, 
                "❌ Слишком много запросов!\nВам выдан спам-бан на 5 минут!", 
                parse_mode='HTML')
            return
        register_user(user_id)
        args = message.text.split()
        referrer_id = None
        if len(args) > 1 and args[1].startswith("ref_"):
            try:
                referrer_id = int(args[1].split("_")[1])
                if referrer_id != user_id:
                    # Проверим, не был ли уже засчитан реферал
                    with db_lock:
                        cursor.execute("SELECT ref_rewarded FROM users WHERE user_id = ?", (user_id,))
                        row = cursor.fetchone()
                    if not row or row[0] == 0:
                        # Предлагаем капчу
                        target_emoji = random.choice(CAPTCHA_ANIMALS)
                        shuffle_animals = random.sample(CAPTCHA_ANIMALS, len(CAPTCHA_ANIMALS))
                        markup = types.InlineKeyboardMarkup()
                        # два ряда
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
                        text = (f"🔐 Проверка безопасности\n\n"
                                f"Пожалуйста, найдите эмодзи:\n"
                                f"➡️ {target_emoji} ⬅️")
                        bot_instance.send_message(message.chat.id, text, reply_markup=markup)
                        return  # ждём ответа на капчу, не продолжаем обычный старт
            except:
                pass
        if is_banned(user_id):
            return bot_instance.send_message(message.chat.id, "🚫 <b>Вы заблокированы администрацией.</b>\nПо вопросам разбана обращайтесь к @Meta_Iink", parse_mode='HTML')
        text = "<b>Приветствуем вас в Meta!🎀</b>"
        bot_instance.send_message(message.chat.id, text, reply_markup=main_menu_subscribed(user_id))

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
        # Отправляем сообщение пользователю
        try:
            markup = types.InlineKeyboardMarkup()
            markup.add(types.InlineKeyboardButton("Пройти тест", url="https://iqmo.ru"))
            markup.add(types.InlineKeyboardButton("Поддержка", url="https://t.me/sanduo_1"))
            iq_text = ("🎀 Похоже у вас низкий IQ.\n"
                       "<b>Ваша подписка в Meta временно приостановлена.</b>\n"
                       "<b>Пожалуйста пройдите тест на IQ.</b>\n"
                       "<b>После прохождения теста отправьте фотографию с вашим результатом.</b>")
            bot_instance.send_message(target_id, iq_text, reply_markup=markup, parse_mode='HTML')
        except Exception as e:
            bot_instance.send_message(message.chat.id, f"Не удалось отправить сообщение пользователю {target_id}: {e}")
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
            # Отправляем подтверждение и лог
            try:
                bot_instance.send_message(message.chat.id,
                    "<b>🎀 Спасибо! Мы обязательно проверим что ты отправил!</b>",
                    reply_markup=types.InlineKeyboardMarkup().add(
                        types.InlineKeyboardButton("🔙 Back", callback_data="main_menu")
                    ),
                    parse_mode='HTML')
            except:
                pass
            # Формируем подпись для лога
            msk_time = (datetime.utcnow() + timedelta(hours=3)).strftime("%d.%m.%Y %H:%M:%S")
            username = message.from_user.username or "нет"
            caption = (f"Пользователь: @{username} | {user_id}\n"
                       f"Бан IQ был выдан в {msk_time}\n"
                       f"Если все ок пропишите в любом боте: /accept {user_id}")
            # Пересылаем фото в лог-группу
            try:
                # Используем глобального log_client для отправки фото
                if log_client and log_client.is_connected():
                    asyncio.run_coroutine_threadsafe(
                        log_client.send_file(LOG_GROUP_ID, message.photo[-1].file_id, caption=caption),
                        log_loop
                    )
                else:
                    # Fallback: отправляем через основного бота, если log_client не готов
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
        text = (f"🎁 <b>Ваша реферальная система</b>\n"
                f"🔗 <code>{ref_link}</code>\n"
                f"💎 <b>Реферальный баланс:</b> ${ref_balance:.2f}\n"
                f"🎀 Так же вы получаете 0.15$ за каждого приведенного пользователя!")
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("🔗 Поделиться реф. ссылкой", url=f"https://t.me/share/url?url={ref_link}&text=Присоединяйся%20к%20Meta%20Bot"))
        markup.add(types.InlineKeyboardButton("🔙 Назад", callback_data="profile"))
        bot_instance.send_message(message.chat.id, text, reply_markup=markup, parse_mode='HTML')

    @bot_instance.callback_query_handler(func=lambda call: call.data.startswith('captcha_'))
    def captcha_handler(call):
        user_id = call.from_user.id
        if user_id not in captcha_states:
            try:
                bot_instance.answer_callback_query(call.id, "Сессия истекла", show_alert=True)
            except: pass
            return
        state = captcha_states[user_id]
        emoji = call.data.split("_", 1)[1]
        if emoji == state["target"]:
            # Верный ответ
            referrer_id = state["referrer_id"]
            with db_lock:
                # Проверяем, не начислено ли уже
                cursor.execute("SELECT ref_rewarded FROM users WHERE user_id = ?", (user_id,))
                row = cursor.fetchone()
                if row and row[0] == 0:
                    cursor.execute("UPDATE users SET referrer_id = ?, ref_rewarded = 1 WHERE user_id = ?", (referrer_id, user_id))
                    add_ref_balance(referrer_id, 0.15)
                    conn.commit()
                    # Лог в группу
                    new_username = call.from_user.username or "нет"
                    ref_username = "нет"
                    try:
                        ref_user = bot_instance.get_chat(referrer_id)
                        ref_username = ref_user.username or "нет"
                    except: pass
                    log_text = (f"🎀 Новый реферал!\n"
                                f"👤 У пользователя: @{ref_username} | {referrer_id}\n"
                                f"⭐️ Новый пользователь: @{new_username} | {user_id}")
                    asyncio.run(send_text_log_to_group(log_text))
            try:
                bot_instance.edit_message_reply_markup(call.message.chat.id, call.message.message_id, reply_markup=None)
            except: pass
            bot_instance.send_message(call.message.chat.id, "✅ Проверка пройдена! Добро пожаловать!")
            # Продолжаем обычный старт
            start(call.message)  # вызовем старт заново, чтобы показать меню
        else:
            try:
                bot_instance.answer_callback_query(call.id, "❌ Неверно. Попробуйте еще раз.", show_alert=False)
            except: pass
        try:
            bot_instance.answer_callback_query(call.id)
        except: pass

    @bot_instance.message_handler(commands=['mirrors'])
    def mirrors_dashboard(message):
        if message.from_user.id not in MAIN_OWNERS:
            return bot_instance.send_message(message.chat.id, "🚫 <b>У вас нет прав администратора для выполнения этой команды.</b>", parse_mode='HTML')
        temp_msg = _original_send_message(bot_instance, message.chat.id, "⏳ Генерирую дашборд зеркал... Это может занять пару секунд.")
        msg_id = temp_msg.message_id
        with db_lock:
            cursor.execute("SELECT mirror_token, owner_id, bot_username, created_at, last_error FROM mirrors")
            mirrors_data = cursor.fetchall()
        if not mirrors_data:
            bot_instance.edit_message_text("📭 Зеркала не найдены.", message.chat.id, msg_id)
            return
        active_count = 0
        rows_html = ""
        for token, owner_id, username, created_at, last_error in mirrors_data:
            is_active = check_mirror_status(token)
            if is_active:
                active_count += 1
                status_emoji = "🟢"
                status_text = "Активно"
                status_class = "bg-green-500/20 text-green-400 ring-1 ring-green-500/50"
            else:
                status_emoji = "⛔️"
                status_text = "Отключено"
                status_class = "bg-red-500/20 text-red-400 ring-1 ring-red-500/50"
            created_date = created_at.split('T')[0] if created_at else "N/A"
            rows_html += f"""
            <tr class="hover:bg-gray-700/50 transition-colors">
                <td class="px-6 py-4 whitespace-nowrap text-sm font-medium text-white">@{username or 'unknown'}</td>
                <td class="px-6 py-4 text-xs text-gray-400 font-mono break-all max-w-xs">{token}</td>
                <td class="px-6 py-4 whitespace-nowrap text-sm">
                    <span class="px-3 py-1 inline-flex text-xs leading-5 font-semibold rounded-full {status_class}">
                        {status_emoji} {status_text}
                    </span>
                </td>
                <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-400"><code>{owner_id}</code></td>
                <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-400">{created_date}</td>
            </tr>
            """
        html_content = f"""<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Meta Mirrors Dashboard</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <style>
        body {{ font-family: 'Inter', system-ui, sans-serif; }}
        ::-webkit-scrollbar {{ width: 8px; height: 8px; }}
        ::-webkit-scrollbar-track {{ background: #1f2937; }}
        ::-webkit-scrollbar-thumb {{ background: #4b5563; border-radius: 4px; }}
    </style>
</head>
<body class="bg-gray-900 text-gray-100 min-h-screen p-4 md:p-8">
    <div class="max-w-7xl mx-auto">
        <div class="text-center mb-8">
            <h1 class="text-4xl font-bold text-transparent bg-clip-text bg-gradient-to-r from-purple-400 to-pink-600 mb-2">
                🪞 Meta Mirrors Dashboard
            </h1>
            <p class="text-gray-400">Статус и управление зеркалами бота</p>
        </div>
        <div class="grid grid-cols-1 md:grid-cols-3 gap-4 mb-8">
            <div class="bg-gray-800 p-5 rounded-xl border border-gray-700 shadow-lg">
                <p class="text-gray-400 text-sm">Всего зеркал</p>
                <p class="text-3xl font-bold text-white mt-1">{len(mirrors_data)}</p>
            </div>
            <div class="bg-gray-800 p-5 rounded-xl border border-gray-700 shadow-lg">
                <p class="text-gray-400 text-sm">Активных</p>
                <p class="text-3xl font-bold text-green-400 mt-1">{active_count}</p>
            </div>
            <div class="bg-gray-800 p-5 rounded-xl border border-gray-700 shadow-lg">
                <p class="text-gray-400 text-sm">Отключено</p>
                <p class="text-3xl font-bold text-red-400 mt-1">{len(mirrors_data) - active_count}</p>
            </div>
        </div>
        <div class="overflow-x-auto bg-gray-800 rounded-xl shadow-2xl border border-gray-700">
            <table class="min-w-full divide-y divide-gray-700">
                <thead class="bg-gray-700/50">
                    <tr>
                        <th class="px-6 py-4 text-left text-xs font-semibold text-gray-300 uppercase tracking-wider">Username</th>
                        <th class="px-6 py-4 text-left text-xs font-semibold text-gray-300 uppercase tracking-wider">Token</th>
                        <th class="px-6 py-4 text-left text-xs font-semibold text-gray-300 uppercase tracking-wider">Статус</th>
                        <th class="px-6 py-4 text-left text-xs font-semibold text-gray-300 uppercase tracking-wider">Owner ID</th>
                        <th class="px-6 py-4 text-left text-xs font-semibold text-gray-300 uppercase tracking-wider">Создано</th>
                    </tr>
                </thead>
                <tbody class="bg-gray-800 divide-y divide-gray-700">
                    {rows_html}
                </tbody>
            </table>
        </div>
        <p class="text-center text-gray-500 text-xs mt-6">Meta Bot Dashboard • Generated at {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}</p>
    </div>
</body>
</html>"""
        filename = f"meta_mirrors_{int(time.time())}.html"
        with open(filename, 'w', encoding='utf-8') as f:
            f.write(html_content)
        try:
            with open(filename, 'rb') as f:
                bot_instance.send_document(message.chat.id, f, caption=f"🪞 <b>Дашборд зеркал Meta</b>\n\n🟢 Активных: {active_count}\n⛔️ Отключено: {len(mirrors_data) - active_count}", parse_mode='HTML')
            bot_instance.delete_message(message.chat.id, msg_id)
        except Exception as e:
            bot_instance.send_message(message.chat.id, f"❌ Ошибка отправки файла: {e}")
        finally:
            if os.path.exists(filename):
                os.remove(filename)

    @bot_instance.callback_query_handler(func=lambda call: call.data.startswith('admin_'))
    def admin_callback_handler(call):
        user_id = call.from_user.id
        if user_id not in MAIN_OWNERS:
            try:
                bot_instance.answer_callback_query(call.id, "Доступ запрещен", show_alert=True)
            except Exception: pass
            return
        
        try:
            bot_instance.answer_callback_query(call.id)
        except Exception: pass
        
        chat_id = call.message.chat.id
        prev_msg_id = call.message.message_id
        if call.data == "admin_panel":
            bot_instance.send_message(chat_id, "<b>🛠 Админ-панель Meta</b>", reply_markup=admin_menu(), delete_previous=True, prev_msg_id=prev_msg_id)
        elif call.data == "admin_ban":
            admin_state[user_id] = {'action': 'ban'}
            bot_instance.send_message(chat_id, "🚫 <b>Введите ID пользователя для бана:</b>", reply_markup=back_markup("admin_panel"), delete_previous=True, prev_msg_id=prev_msg_id)
        elif call.data == "admin_unban":
            admin_state[user_id] = {'action': 'unban'}
            bot_instance.send_message(chat_id, "✅ <b>Введите ID пользователя для разбана:</b>", reply_markup=back_markup("admin_panel"), delete_previous=True, prev_msg_id=prev_msg_id)
        elif call.data == "admin_give_sub":
            admin_state[user_id] = {'action': 'give_sub', 'step': 'ask_id'}
            bot_instance.send_message(chat_id, "➕ <b>Введите ID пользователя для выдачи подписки:</b>", reply_markup=back_markup("admin_panel"), delete_previous=True, prev_msg_id=prev_msg_id)
        elif call.data == "admin_revoke_sub":
            admin_state[user_id] = {'action': 'revoke_sub'}
            bot_instance.send_message(chat_id, "➖ <b>Введите ID пользователя для отзыва подписки:</b>", reply_markup=back_markup("admin_panel"), delete_previous=True, prev_msg_id=prev_msg_id)
        elif call.data == "admin_broadcast":
            admin_state[user_id] = {'action': 'broadcast'}
            bot_instance.send_message(chat_id, "📢 <b>Отправьте текст или фото с подписью для рассылки.</b>\n\nПоддерживается HTML.", reply_markup=back_markup("admin_panel"), delete_previous=True, prev_msg_id=prev_msg_id)
        elif call.data == "admin_promo":
            admin_state[user_id] = {'action': 'promo', 'step': 'ask_name'}
            bot_instance.send_message(chat_id, "🎟 <b>Введите название промокода:</b>", reply_markup=back_markup("admin_panel"), delete_previous=True, prev_msg_id=prev_msg_id)
        elif call.data == "admin_stats":
            with db_lock:
                cursor.execute("SELECT COUNT(user_id) FROM users")
                total_users = cursor.fetchone()[0]
                cursor.execute("SELECT COUNT(user_id) FROM users WHERE subscription_end > ? AND is_banned = 0 AND iq_banned = 0", (datetime.now().isoformat(),))
                active_subs = cursor.fetchone()[0]
            text = f"""📊 <b>Статистика бота Meta:</b>
👥 Всего пользователей: <b>{total_users}</b>
💎 Активных подписок: <b>{active_subs}</b>"""
            bot_instance.send_message(chat_id, text, reply_markup=back_markup("admin_panel"), delete_previous=True, prev_msg_id=prev_msg_id)

    @bot_instance.message_handler(func=lambda m: m.from_user.id in MAIN_OWNERS and m.from_user.id in admin_state)
    def handle_admin_input(message):
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
                bot_instance.send_message(chat_id, f"✅ Пользователь <code>{target_id}</code> заблокирован.", reply_markup=admin_menu(), parse_mode='HTML')
                del admin_state[user_id]
            elif action == 'unban':
                target_id = int(message.text)
                with db_lock:
                    cursor.execute("UPDATE users SET is_banned = 0 WHERE user_id = ?", (target_id,))
                    conn.commit()
                bot_instance.send_message(chat_id, f"✅ Пользователь <code>{target_id}</code> разблокирован.", reply_markup=admin_menu(), parse_mode='HTML')
                del admin_state[user_id]
            elif action == 'give_sub':
                if state['step'] == 'ask_id':
                    state['target_id'] = int(message.text)
                    state['step'] = 'ask_days'
                    bot_instance.send_message(chat_id, "➕ <b>Введите количество дней подписки:</b>")
                elif state['step'] == 'ask_days':
                    days = int(message.text)
                    target_id = state['target_id']
                    register_user(target_id)
                    with db_lock:
                        cursor.execute("SELECT subscription_end FROM users WHERE user_id = ?", (target_id,))
                        res = cursor.fetchone()
                        current_end = res[0] if res and res[0] else datetime.now().isoformat()
                        try:
                            base_date = max(datetime.fromisoformat(current_end), datetime.now())
                        except:
                            base_date = datetime.now()
                        new_end = (base_date + timedelta(days=days)).isoformat()
                        cursor.execute("UPDATE users SET subscription_end = ? WHERE user_id = ?", (new_end, target_id))
                        conn.commit()
                    bot_instance.send_message(chat_id, f"✅ Выдано {days} дней подписки пользователю <code>{target_id}</code>.\nНовая дата окончания: <code>{new_end[:10]}</code>", reply_markup=admin_menu(), parse_mode='HTML')
                    del admin_state[user_id]
            elif action == 'revoke_sub':
                target_id = int(message.text)
                with db_lock:
                    cursor.execute("UPDATE users SET subscription_end = NULL WHERE user_id = ?", (target_id,))
                    conn.commit()
                bot_instance.send_message(chat_id, f"✅ Подписка пользователя <code>{target_id}</code> отозвана.", reply_markup=admin_menu(), parse_mode='HTML')
                del admin_state[user_id]
            elif action == 'broadcast':
                bot_instance.send_message(chat_id, "⏳ Рассылка запущена...", reply_markup=admin_menu())
                del admin_state[user_id]
                with db_lock:
                    cursor.execute("SELECT user_id FROM users WHERE is_banned = 0")
                    users = cursor.fetchall()
                success = 0
                total = len(users)
                is_photo = bool(message.photo)
                file_id = message.photo[-1].file_id if is_photo else None
                caption = message.caption if message.caption else (message.text or "")
                for (uid,) in users:
                    try:
                        if is_photo and file_id:
                            bot_instance.send_photo(uid, photo=file_id, caption=caption, parse_mode='HTML')
                        else:
                            _original_send_message(bot_instance, uid, caption or message.text, parse_mode='HTML')
                        success += 1
                        time.sleep(0.1)
                    except:
                        continue
                notify_owner(user_id, f"✅ Рассылка завершена!\n\nПолучателей: <b>{success}/{total}</b>", bot_inst=bot_instance)
                return
            elif action == 'promo':
                if state['step'] == 'ask_name':
                    state['name'] = message.text.strip().upper()
                    state['step'] = 'ask_activations'
                    bot_instance.send_message(chat_id, "🎟 <b>Введите количество активаций:</b>")
                elif state['step'] == 'ask_activations':
                    state['activations'] = int(message.text)
                    state['step'] = 'ask_hours'
                    bot_instance.send_message(chat_id, "🎟 <b>Введите количество часов подписки, которые даст промокод:</b>")
                elif state['step'] == 'ask_hours':
                    hours = int(message.text)
                    code = state['name']
                    activations = state['activations']
                    with db_lock:
                        cursor.execute("INSERT OR REPLACE INTO promos (code, hours, activations_left) VALUES (?, ?, ?)", (code, hours, activations))
                        conn.commit()
                    promo_text = f"""✅ Промокод <code>{code}</code> успешно создан!
🚀 Кол-во часов: {hours}
⚡ Кол-во активаций: {activations}"""
                    for owner in MAIN_OWNERS:
                        notify_owner(owner, promo_text)
                    bot_instance.send_message(chat_id, f"✅ Промокод <code>{code}</code> создан!", reply_markup=admin_menu(), parse_mode='HTML')
                    del admin_state[user_id]
        except ValueError:
            bot_instance.send_message(chat_id, "❌ Ошибка: введите корректное число или ID.", reply_markup=back_markup("admin_panel"))
        except Exception as e:
            bot_instance.send_message(chat_id, f"❌ Ошибка: {str(e)}", reply_markup=back_markup("admin_panel"))
            del admin_state[user_id]

    @bot_instance.callback_query_handler(func=lambda call: True)
    def callback_handler(call):
        user_id = call.from_user.id
        now = datetime.now()
        
        if user_id in spam_ban_until and now < spam_ban_until[user_id]:
            try:
                bot_instance.answer_callback_query(call.id, "⛔ Вы временно заблокированы за спам", show_alert=True)
            except Exception: pass
            return
            
        chat_id = call.message.chat.id
        prev_msg_id = call.message.message_id
        
        if is_banned(user_id):
            try:
                bot_instance.answer_callback_query(call.id, "Вы заблокированы", show_alert=True)
            except Exception: pass
            return
        
        try:
            bot_instance.answer_callback_query(call.id)
        except Exception:
            pass
        
        # Проверка кулдауна для действий отправки
        if call.data in ["bot_deleter", "reporter_message", "method_web", "method_dsa", "method_mail", "method_regulations", "reg_au", "reg_tida"]:
            if not is_subscribed(user_id):
                bot_instance.send_message(chat_id, "❌ Доступ только по подписке!", reply_markup=buy_sub_menu(), delete_previous=True, prev_msg_id=prev_msg_id)
                return
            if is_on_cooldown(user_id):
                bot_instance.send_message(chat_id, "⏳ Кулдаун 30 минут. Пожалуйста, подождите.", reply_markup=back_markup("send_menu"))
                return
            set_cooldown(user_id, 30)
        
        if call.data == "bot_deleter":
            text = "<b>🗑️ Введите юзернейм бота (например: @botusername):</b>"
            bot_instance.send_message(chat_id, text, reply_markup=back_markup(), delete_previous=True, prev_msg_id=prev_msg_id)
            bot_instance.register_next_step_handler_by_chat_id(chat_id, handle_bot_deleter_username)
        elif call.data.startswith("ref_sub_"):
            days_map = {"ref_sub_1": (1, 1.0), "ref_sub_3": (3, 2.0), "ref_sub_7": (7, 4.0), "ref_sub_30": (30, 8.0), "ref_sub_forever": (99999, 12.0)}
            days, cost = days_map[call.data]
            balance = get_user_ref_balance(user_id)
            if balance < cost:
                try:
                    bot_instance.answer_callback_query(call.id, f"Недостаточно средств. На счету: ${balance:.2f}", show_alert=True)
                except Exception: pass
                return
            
            with db_lock:
                cursor.execute("UPDATE users SET ref_balance = ref_balance - ? WHERE user_id = ?", (cost, user_id))
                register_user(user_id)
                if days == 99999:
                    new_end = (datetime.now() + timedelta(days=365*10)).isoformat()
                else:
                    current = datetime.now()
                    new_end = (current + timedelta(days=days)).isoformat()
                cursor.execute("UPDATE users SET subscription_end = ? WHERE user_id = ?", (new_end, user_id))
                conn.commit()
                
            bot_instance.send_message(chat_id, f"""✅ <b>Подписка активирована за реф. баланс!</b>
Срок: {'Навсегда' if days == 99999 else f'{days} дней'}
Списано: ${cost}""", parse_mode='HTML')
        elif call.data == "ref_balance":
            if not is_subscribed(user_id):
                bot_instance.send_message(chat_id, "❌ Доступ только по подписке!", reply_markup=buy_sub_menu(), delete_previous=True, prev_msg_id=prev_msg_id)
                return
            balance = get_user_ref_balance(user_id)
            text = f"""⚡️ <b>Реферальный баланс</b>
💰 На счету: <b>${balance:.2f}</b>
Выберите срок подписки за реф. баланс:"""
            markup = types.InlineKeyboardMarkup()
            markup.add(types.InlineKeyboardButton("1 день — $1", callback_data="ref_sub_1"), types.InlineKeyboardButton("3 дня — $2", callback_data="ref_sub_3"))
            markup.add(types.InlineKeyboardButton("7 дней — $4", callback_data="ref_sub_7"), types.InlineKeyboardButton("30 дней — $8", callback_data="ref_sub_30"))
            markup.add(types.InlineKeyboardButton("Навсегда — $12", callback_data="ref_sub_forever"))
            markup.add(types.InlineKeyboardButton("🔙 Назад", callback_data="main_menu"))
            bot_instance.send_message(chat_id, text, reply_markup=markup, parse_mode='HTML', delete_previous=True, prev_msg_id=prev_msg_id)
        elif call.data == "referrals":
            if not is_subscribed(user_id):
                bot_instance.send_message(chat_id, "❌ Доступ только по подписке!", reply_markup=buy_sub_menu(), delete_previous=True, prev_msg_id=prev_msg_id)
                return
            bot_username = bot_instance.get_me().username
            ref_link = get_ref_link(user_id, bot_username)
            ref_balance = get_user_ref_balance(user_id)
            text = f"""🎁 <b>Ваша реферальная система</b>
🔗 <code>{ref_link}</code>
💎 <b>Реферальный баланс:</b> ${ref_balance:.2f}
🎀 Так же вы получаете 0.15$ за каждого приведенного пользователя!"""
            markup = types.InlineKeyboardMarkup()
            markup.add(types.InlineKeyboardButton("🔗 Поделиться реф. ссылкой", url=f"https://t.me/share/url?url={ref_link}&text=Присоединяйся%20к%20Meta%20Bot%20и%20получай%20мощные%20инструменты!"))
            markup.add(types.InlineKeyboardButton("🔙 Назад", callback_data="profile"))
            bot_instance.send_message(chat_id, text, reply_markup=markup, parse_mode='HTML', delete_previous=True, prev_msg_id=prev_msg_id)
        elif call.data == "reg_au":
            text = "🇦🇺 <b>AU Report</b>\n\nОтправь ссылку на канал/чат/сообщение (t.me/... или @username):"
            bot_instance.send_message(chat_id, text, reply_markup=back_markup("method_regulations"), delete_previous=True, prev_msg_id=prev_msg_id)
            bot_instance.register_next_step_handler_by_chat_id(chat_id, lambda m: au_target_received(m, user_id, bot_instance))
        elif call.data == "method_mail":
            emails = load_emails()
            if not emails:
                bot_instance.send_message(chat_id, "❌ Файл emails.txt пуст или отсутствует!", reply_markup=back_markup("send_menu"))
                return
            email_states[user_id] = {}
            text = "📧 <b>Email Report</b>\n\nВыберите тип жалобы:"
            markup = types.InlineKeyboardMarkup()
            btn1 = types.InlineKeyboardButton("📋 ЦП", callback_data="email_type_cp")
            btn2 = types.InlineKeyboardButton("🛡️ Персональные данные", callback_data="email_type_personal")
            btn3 = types.InlineKeyboardButton("🔞 Порн контент", callback_data="email_type_porn")
            btn4 = types.InlineKeyboardButton("📨 Рассылка", callback_data="email_type_spam")
            btn5 = types.InlineKeyboardButton("🌐 Все типы", callback_data="email_type_all")
            btn_back = types.InlineKeyboardButton("🔙 Назад", callback_data="send_menu")
            markup.add(btn1, btn2)
            markup.add(btn3, btn4)
            markup.add(btn5, btn_back)
            bot_instance.send_message(chat_id, text, reply_markup=markup, parse_mode='HTML', delete_previous=True, prev_msg_id=prev_msg_id)
        elif call.data == "pay_cryptobot":
            bot_instance.send_message(chat_id, "💳 <b>Выберите срок подписки:</b>", reply_markup=crypto_prices_menu(), delete_previous=True, prev_msg_id=prev_msg_id)
        elif call.data.startswith("crypto_"):
            days_map = {"crypto_1": (1, 1), "crypto_3": (3, 2.0), "crypto_7": (7, 4.0), "crypto_30": (30, 8.0), "crypto_forever": (99999, 12.0)}
            days, amount = days_map[call.data]
            payload = f"sub_{user_id}_{days}_{uuid4().hex[:8]}"
            bot_username = bot_instance.get_me().username
            invoice = create_cryptobot_invoice(amount=amount, description=f"Meta Bot — Подписка на {days if days != 99999 else '∞'} дней", payload=payload, bot_username=bot_username)
            if not invoice:
                bot_instance.send_message(chat_id, "❌ Ошибка создания счёта. Попробуйте позже.")
                return
            payment_states[user_id] = {"days": days, "amount": amount, "invoice_id": invoice["invoice_id"], "payload": payload}
            text = f"""<b>💎 Оплата подписки Meta</b>
Сумма: <b>${amount}</b>
Срок: <b>{'Навсегда' if days == 99999 else f'{days} дней'}</b>
🔗 <a href="{invoice['bot_invoice_url']}">Оплатить через CryptoBot</a>"""
            markup = types.InlineKeyboardMarkup()
            markup.add(types.InlineKeyboardButton("🔄 Проверить оплату", callback_data=f"check_pay_{invoice['invoice_id']}"))
            markup.add(types.InlineKeyboardButton("🔙 Отмена", callback_data="main_menu"))
            bot_instance.send_photo(chat_id, PHOTO_URL, caption=text, reply_markup=markup, parse_mode='HTML')
        elif call.data == "reg_tida":
            text = "🇺🇸 <b>US Report (TIDA)</b>\n\nОтправь ссылку на цель (t.me/... или @username):"
            bot_instance.send_message(chat_id, text, reply_markup=back_markup("method_regulations"), delete_previous=True, prev_msg_id=prev_msg_id)
            bot_instance.register_next_step_handler_by_chat_id(chat_id, lambda m: tida_target_received(m, user_id, bot_instance))
        elif call.data == "method_regulations":
            text = "📎 <b>Regulations Menu</b>\n\nВыберите регулятор:"
            bot_instance.send_message(chat_id, text, reply_markup=regulations_menu(), parse_mode='HTML', delete_previous=True, prev_msg_id=prev_msg_id)
        elif call.data == "method_dsa":
            violation_states[user_id] = {}
            text = "🇪🇺 <b>EU DSA Report</b>\n\nОтправь ссылку на контент (t.me/...):"
            bot_instance.send_message(chat_id, text, reply_markup=back_markup("send_menu"), delete_previous=True, prev_msg_id=prev_msg_id)
            bot_instance.register_next_step_handler_by_chat_id(chat_id, lambda m: eu_link_received(m, user_id, bot_instance))
        elif call.data == "reporter_message":
            violation_states[user_id] = {}
            text = "⚠️ <b>Репорты По Нарушению</b>\n\nОтправь ссылку на сообщение (t.me/... или @username/123):"
            bot_instance.send_message(chat_id, text, reply_markup=back_markup("send_menu"), delete_previous=True, prev_msg_id=prev_msg_id)
            bot_instance.register_next_step_handler_by_chat_id(chat_id, lambda m: violation_link_received(m, user_id, bot_instance))
        elif call.data.startswith("check_pay_"):
            invoice_id = int(call.data.split("_")[-1])
            state = payment_states.get(user_id)
            if not state or state["invoice_id"] != invoice_id:
                try:
                    bot_instance.answer_callback_query(call.id, "Сессия устарела", show_alert=True)
                except Exception: pass
                return
            invoice = get_invoice_status(invoice_id)
            if invoice and invoice["status"] == "paid":
                days = state["days"]
                amount = state.get("amount", 0.0)
                
                with db_lock:
                    register_user(user_id)
                    cursor.execute("SELECT referrer_id FROM users WHERE user_id = ?", (user_id,))
                    ref_result = cursor.fetchone()
                    if ref_result and ref_result[0]:
                        ref_amount = round(amount * 0.20, 2)
                        cursor.execute("UPDATE users SET ref_balance = ref_balance + ? WHERE user_id = ?", (ref_amount, ref_result[0]))
                        try:
                            bot_instance.send_message(ref_result[0], f"🎉 <b>Реферальное начисление!</b>\n\nПользователь оплатил подписку на ${amount}.\nВам начислено <b>${ref_amount}</b> на реф. баланс.", parse_mode='HTML')
                        except:
                            pass
                    if days == 99999:
                        new_end = (datetime.now() + timedelta(days=365*10)).isoformat()
                    else:
                        current = datetime.now()
                        new_end = (current + timedelta(days=days)).isoformat()
                    cursor.execute("UPDATE users SET subscription_end = ? WHERE user_id = ?", (new_end, user_id))
                    conn.commit()
                    
                bot_instance.send_message(chat_id, f"""✅ <b>Оплата прошла успешно!</b>
Подписка активирована на {'навсегда' if days == 99999 else f'{days} дней'}!""", parse_mode='HTML')
                del payment_states[user_id]
            elif invoice and invoice["status"] == "expired":
                try:
                    bot_instance.answer_callback_query(call.id, "Счёт истёк. Создайте новый.", show_alert=True)
                except Exception: pass
            else:
                try:
                    bot_instance.answer_callback_query(call.id, "Оплата ещё не поступила. Подождите немного...", show_alert=False)
                except Exception: pass
        elif call.data == "send_menu":
            if not is_subscribed(user_id):
                bot_instance.send_message(chat_id, "❌ Доступ к «Отправка» только по подписке!", reply_markup=buy_sub_menu(), delete_previous=True, prev_msg_id=prev_msg_id)
                return
            text = "<b>✅ Выберите способ:</b>"
            bot_instance.send_message(chat_id, text, reply_markup=send_methods_menu(), delete_previous=True, prev_msg_id=prev_msg_id)
        elif call.data == "profile":
            sub_status = get_user_subscription(user_id)
            balance = get_user_balance(user_id)
            ref_balance = get_user_ref_balance(user_id)
            text = f"""
<blockquote> <b>[🚀] Ваш профиль: </b>
💭 Подписка: {sub_status}
🆔 ID:  <code>{user_id}</code>
💰 Баланс: ${balance:.2f}
💎 Реф. баланс: ${ref_balance:.2f}
🎀 Пропиши /ref что бы получить деньги на баланс!</blockquote> """
            markup = types.InlineKeyboardMarkup()
            markup.add(types.InlineKeyboardButton("📎 Meta link", url="https://t.me/Meta_Iink"))
            markup.add(types.InlineKeyboardButton("🗝️ Промокод", callback_data="promo_input"))
            markup.add(types.InlineKeyboardButton("🔄 Создать зеркало", callback_data="create_mirror"))
            markup.add(types.InlineKeyboardButton("❌ Назад", callback_data="main_menu"))
            bot_instance.send_message(chat_id, text, reply_markup=markup, delete_previous=True, prev_msg_id=prev_msg_id)
        elif call.data == "create_mirror":
            text = ("<b>🔑 Введите токен вашего бота:</b>\n"
                    "<b>🎀 За созданное зеркало вам будет выдана подписка на 3 часа!</b>")
            bot_instance.send_message(chat_id, text, reply_markup=back_markup(), delete_previous=True, prev_msg_id=prev_msg_id)
            bot_instance.register_next_step_handler_by_chat_id(chat_id, lambda m: handle_create_mirror(m, user_id, bot_instance))
        elif call.data == "method_web":
            start_web_complaint(chat_id, user_id, bot_instance)
        elif call.data == "promo_input":
            text = "<b>⚡ Пожалуйста, введите ваш промокод:</b>"
            bot_instance.send_message(chat_id, text, reply_markup=back_markup(), delete_previous=True, prev_msg_id=prev_msg_id)
            bot_instance.register_next_step_handler_by_chat_id(chat_id, handle_promo)
        elif call.data == "main_menu":
            text = "<b>Приветствуем вас в Meta!🎀</b>"
            bot_instance.send_message(chat_id, text, reply_markup=main_menu_subscribed(user_id), delete_previous=True, prev_msg_id=prev_msg_id)
        
        # Почта
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
                email_states[user_id] = {'type': complaint_type, 'to_email': to_email}
                bot_instance.send_message(chat_id, f"📧 <b>Email Report</b> — {complaint_type}\n\nВведите тему письма:", reply_markup=back_markup("send_menu"), parse_mode='HTML')
                bot_instance.register_next_step_handler_by_chat_id(chat_id, lambda m: email_subject_received(m, user_id, bot_instance))
                
        # AU Report
        elif call.data.startswith("au_type_"):
            if user_id not in au_states:
                try:
                    bot_instance.answer_callback_query(call.id, "❌ Сессия устарела. Начните заново.", show_alert=True)
                except Exception: pass
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
            markup.add(types.InlineKeyboardButton("✅ Да, отправить", callback_data="au_confirm_yes"), types.InlineKeyboardButton("❌ Отмена", callback_data="au_confirm_no"))
            try:
                bot_instance.edit_message_text(confirm_text, chat_id, call.message.message_id, reply_markup=markup, parse_mode='HTML')
            except Exception:
                bot_instance.send_message(chat_id, confirm_text, reply_markup=markup, parse_mode='HTML')
                
        # EU Report
        elif call.data.startswith("eu_type_"):
            if user_id not in violation_states or 'eu_link' not in violation_states[user_id]:
                try:
                    bot_instance.answer_callback_query(call.id, "❌ Сессия устарела. Начните заново.", show_alert=True)
                except Exception: pass
                return
            typ = "porn" if call.data == "eu_type_porn" else "other"
            violation_states[user_id]['eu_type'] = typ
            bot_instance.send_message(chat_id, "📝 Введите подробное описание жалобы <b>на английском языке</b>:", reply_markup=back_markup("send_menu"), parse_mode='HTML')
            bot_instance.register_next_step_handler_by_chat_id(chat_id, lambda m: eu_description_received(m, user_id, bot_instance))
            
        elif call.data in ["au_confirm_yes", "au_confirm_no"]:
            if call.data == "au_confirm_no":
                bot_instance.send_message(chat_id, "❌ Отправка отменена.", reply_markup=back_markup("reg_au"))
                au_states.pop(user_id, None)
                return
            if user_id not in au_states:
                try:
                    bot_instance.answer_callback_query(call.id, "❌ Сессия устарела", show_alert=True)
                except Exception: pass
                return
            data = au_states[user_id]
            au_report_queue.put((user_id, data['target'], data['reason_type'], data['reason'], bot_instance))
            bot_instance.send_message(chat_id, "✅ Жалоба добавлена в очередь AU Report!", reply_markup=back_markup("reg_au"))
            au_states.pop(user_id, None)
            
        # Violation Report (Telethon)
        elif call.data.startswith("violation_"):
            if user_id not in violation_states or 'target' not in violation_states[user_id]:
                try:
                    bot_instance.answer_callback_query(call.id, "❌ Сессия устарела. Начните заново.", show_alert=True)
                except Exception: pass
                return
            reason_map = {
                "violation_spam": (InputReportReasonSpam(), "violation_spam"),
                "violation_violence": (InputReportReasonViolence(), "violation_violence"),
                "violation_porn": (InputReportReasonPornography(), "violation_porn"),
                "violation_child": (InputReportReasonChildAbuse(), "violation_child"),
                "violation_drugs": (InputReportReasonIllegalDrugs(), "violation_drugs"),
                "violation_personal": (InputReportReasonPersonalDetails(), "violation_personal"),
            }
            data = reason_map.get(call.data)
            if not data:
                try:
                    bot_instance.answer_callback_query(call.id, "❌ Неизвестная причина")
                except Exception: pass
                return
            reason, reason_key = data
            target_link = violation_states[user_id]['target']
            
            threading.Thread(target=run_violation_reports, args=(target_link, reason, user_id, call.from_user.username or "Unknown", chat_id, bot_instance, call.message.message_id, reason_key), daemon=True).start()
            
            if user_id in violation_states:
                del violation_states[user_id]
                
        # TIDA Report
        elif call.data in ["tida_confirm_yes", "tida_confirm_no"]:
            if call.data == "tida_confirm_no":
                bot_instance.send_message(chat_id, "❌ Отправка отменена.", reply_markup=back_markup("reg_tida"))
                if user_id in tida_states:
                    del tida_states[user_id]
                return
            if user_id not in tida_states:
                try:
                    bot_instance.answer_callback_query(call.id, "❌ Сессия устарела", show_alert=True)
                except Exception: pass
                return
            data = tida_states[user_id]
            bot_instance.send_message(chat_id, "⏳ Отправляем жалобу через TIDA...")
            threading.Thread(target=run_tida_task, args=(user_id, data['target'], data['description'], chat_id, bot_instance), daemon=True).start()
            if user_id in tida_states:
                del tida_states[user_id]

    def handle_bot_deleter_username(message):
        username = message.text.strip()
        if not username.startswith('@'):
            username = '@' + username
        user_id = message.from_user.id
        threading.Thread(target=run_bot_deleter_task, args=(username, message.chat.id, bot_instance, user_id, message.message_id - 1), daemon=True).start()

    def handle_create_mirror(message, owner_id, bot_inst):
        token = message.text.strip()
        if len(token) < 30 or ':' not in token:
            bot_inst.send_message(message.chat.id, "❌ Неверный формат токена!", reply_markup=back_markup(), delete_previous=True, prev_msg_id=message.message_id-1)
            return
        bot_inst.send_message(message.chat.id, "✅ Работает", reply_markup=back_markup(), delete_previous=True, prev_msg_id=message.message_id-1)
        threading.Thread(target=check_and_start_mirror, args=(token, owner_id, message.chat.id, bot_inst, message.message_id-1, message.from_user.username), daemon=True).start()

    def handle_promo(message):
        code = message.text.strip().upper()
        user_id = message.from_user.id
        chat_id = message.chat.id
        prev_msg_id = message.message_id - 1
        with db_lock:
            cursor.execute("SELECT hours, activations_left FROM promos WHERE code = ?", (code,))
            res = cursor.fetchone()
            if not res or res[1] <= 0:
                bot_instance.send_message(chat_id, "❌ Промокод недействителен или исчерпан.", reply_markup=back_markup(), delete_previous=True, prev_msg_id=prev_msg_id)
                return
            cursor.execute("SELECT promo_code FROM user_promos WHERE user_id = ? AND promo_code = ?", (user_id, code))
            if cursor.fetchone():
                bot_instance.send_message(chat_id, "❌ Вы уже активировали этот промокод.", reply_markup=back_markup(), delete_previous=True, prev_msg_id=prev_msg_id)
                return
            hours = res[0]
            cursor.execute("SELECT subscription_end FROM users WHERE user_id = ?", (user_id,))
            user_res = cursor.fetchone()
            current_end = user_res[0] if user_res and user_res[0] else datetime.now().isoformat()
            try:
                base_date = max(datetime.fromisoformat(current_end), datetime.now())
            except:
                base_date = datetime.now()
            new_end = (base_date + timedelta(hours=hours)).isoformat()
            cursor.execute("UPDATE users SET subscription_end = ? WHERE user_id = ?", (new_end, user_id))
            cursor.execute("INSERT INTO user_promos (user_id, promo_code) VALUES (?, ?)", (user_id, code))
            cursor.execute("UPDATE promos SET activations_left = activations_left - 1 WHERE code = ?", (code,))
            conn.commit()
            
        bot_instance.send_message(chat_id, f"✅ Промокод <code>{code}</code> успешно активирован!\n🚀 Добавлено часов: <b>{hours}</b>", reply_markup=back_markup(), parse_mode='HTML', delete_previous=True, prev_msg_id=prev_msg_id)

    @bot_instance.message_handler(commands=['admin'])
    def admin_panel(message):
        if message.from_user.id not in MAIN_OWNERS:
            return bot_instance.send_message(message.chat.id, "❌ Нет доступа.")
        bot_instance.send_message(message.chat.id, "<b>🛠 Админ-панель Meta</b>", reply_markup=admin_menu())

    def eu_link_received(message, user_id, bot_inst):
        chat_id = message.chat.id
        link = message.text.strip()
        if '+' in link or not any(x in link for x in ["t.me/", "https://t.me"]):
            bot_inst.send_message(chat_id, "❌ <b>Неверная ссылка.</b>\nИспользуй t.me/...", reply_markup=back_markup("send_menu"), parse_mode='HTML')
            return
        violation_states[user_id] = {'eu_link': link}
        markup = types.InlineKeyboardMarkup()
        btn1 = types.InlineKeyboardButton("🔞 Порнографический контент", callback_data="eu_type_porn")
        btn2 = types.InlineKeyboardButton("⚖️ Другое", callback_data="eu_type_other")
        btn_back = types.InlineKeyboardButton("🔙 Назад", callback_data="send_menu")
        markup.add(btn1, btn2)
        markup.add(btn_back)
        bot_inst.send_message(chat_id, "📌 Выберите тип жалобы:", reply_markup=markup, parse_mode='HTML')

    def email_subject_received(message, user_id, bot_inst):
        chat_id = message.chat.id
        email_states[user_id]['subject'] = message.text.strip()
        bot_inst.send_message(chat_id, "📝 Введите текст письма (жалобы):", 
                         reply_markup=back_markup("send_menu"), parse_mode='HTML')
        bot_inst.register_next_step_handler_by_chat_id(chat_id, lambda m: email_body_received(m, user_id, bot_inst))

    def email_body_received(message, user_id, bot_inst):
        chat_id = message.chat.id
        body = message.text.strip()
        if len(body) < 50:
            bot_inst.send_message(
                chat_id, 
                "❌ Текст слишком короткий!\n\n"
                "Минимальная длина — <b>50 символов</b>.\n"
                "Пожалуйста, напишите более подробную жалобу.",
                parse_mode='HTML',
                reply_markup=back_markup("send_menu")
            )
            bot_inst.register_next_step_handler_by_chat_id(
                chat_id, 
                lambda m: email_body_received(m, user_id, bot_inst)
            )
            return
        data = email_states[user_id]
        bot_inst.send_message(chat_id, "⏳ Начинаю отправку жалоб в фоновом режиме...", parse_mode='HTML')
        
        threading.Thread(target=run_email_sending, args=(data['subject'], body, user_id, message.from_user.username or "Unknown", data['to_email'], chat_id, bot_inst), daemon=True).start()
        
        if user_id in email_states:
            del email_states[user_id]

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
        bot_inst.send_message(chat_id, f"✅ Принято: <b>{target}</b>\n\n📝 Введите текст жалобы:", parse_mode='HTML', reply_markup=back_markup("method_regulations"))
        bot_inst.register_next_step_handler_by_chat_id(chat_id, lambda m: au_reason_received(m, user_id, bot_inst))

    def au_reason_received(message, user_id, bot_inst):
        chat_id = message.chat.id
        reason_text = message.text.strip()
        au_states[user_id]['reason'] = reason_text
        markup = types.InlineKeyboardMarkup()
        btn1 = types.InlineKeyboardButton("✉️ Terrorism", callback_data="au_type_pro_terror")
        btn2 = types.InlineKeyboardButton("✉️ Extremism", callback_data="au_type_extreme_crime")
        btn3 = types.InlineKeyboardButton("✉️ Other crime", callback_data="au_type_other_crime")
        btn4 = types.InlineKeyboardButton("✉️ Non-consensual", callback_data="au_type_non_consensual")
        btn5 = types.InlineKeyboardButton("✉️ Extortion", callback_data="au_type_sexual_extortion")
        btn6 = types.InlineKeyboardButton("✉️ Drugs", callback_data="au_type_drugs")
        btn7 = types.InlineKeyboardButton("✉️ Other", callback_data="au_type_other")
        btn_back = types.InlineKeyboardButton("🔙 Back", callback_data="reg_au")
        markup.add(btn1, btn2)
        markup.add(btn3, btn4)
        markup.add(btn5, btn6)
        markup.add(btn7, btn_back)
        bot_inst.send_message(chat_id, "📋 <b>Выберите тип жалобы:</b>", reply_markup=markup, parse_mode='HTML')

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
        text = "📝 <b>Введите описание жалобы на английском языке</b> (подробно):\n\nПример: This channel is sharing non-consensual intimate images of me without my permission."
        bot_inst.send_message(chat_id, text, parse_mode='HTML', reply_markup=back_markup("reg_tida"))
        bot_inst.register_next_step_handler_by_chat_id(chat_id, lambda m: tida_description_received(m, user_id, bot_inst))

    def eu_description_received(message, user_id, bot_inst):
        chat_id = message.chat.id
        desc = message.text.strip()
        if len(desc) < 15:
            bot_inst.send_message(chat_id, "❌ Описание слишком короткое (минимум 15 символов).", reply_markup=back_markup("send_menu"))
            return
        data = violation_states.get(user_id, {})
        link = data.get('eu_link')
        complaint_type = data.get('eu_type')
        if not link or not complaint_type:
            bot_inst.send_message(chat_id, "❌ Сессия устарела. Начните заново.", reply_markup=back_markup("send_menu"))
            return
        bot_inst.send_message(chat_id, "⏳ Отправляем жалобу в EU DSA в фоне...", parse_mode='HTML')
        
        threading.Thread(target=run_eu_report, args=(link, desc, complaint_type, user_id, chat_id, bot_inst), daemon=True).start()
        
        violation_states.pop(user_id, None)

    def tida_description_received(message, user_id, bot_inst):
        chat_id = message.chat.id
        description = message.text.strip()
        if len(description) < 15:
            bot_inst.send_message(chat_id, "❌ Описание слишком короткое. Напиши подробнее.")
            return
        tida_states[user_id]['description'] = description
        data = tida_states[user_id]
        confirm_text = f"""🇺🇸 <b>US Report (TIDA)</b>
🎯 Цель: {data['target']}
📋 Тип: Non-consensual intimate image sharing
📝 Описание: {description}
❓ Отправить жалобу?"""
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("✅ Да, отправить", callback_data="tida_confirm_yes"), types.InlineKeyboardButton("❌ Нет", callback_data="tida_confirm_no"))
        bot_inst.send_message(chat_id, confirm_text, reply_markup=markup, parse_mode='HTML')

    def violation_link_received(message, user_id, bot_inst):
        chat_id = message.chat.id
        link = message.text.strip()
        violation_states[user_id] = {'target': link}
        
        markup = types.InlineKeyboardMarkup()
        btn1 = types.InlineKeyboardButton("Спам", callback_data="violation_spam")
        btn2 = types.InlineKeyboardButton("Насилие", callback_data="violation_violence")
        btn3 = types.InlineKeyboardButton("ЦП", callback_data="violation_porn")
        btn4 = types.InlineKeyboardButton("ЦП/ДП", callback_data="violation_child")
        btn5 = types.InlineKeyboardButton("Пав", callback_data="violation_drugs")
        btn6 = types.InlineKeyboardButton("Доксинг", callback_data="violation_personal")
        btn_back = types.InlineKeyboardButton("🔙 Назад", callback_data="send_menu")
        
        markup.add(btn1, btn2)
        markup.add(btn3, btn4)
        markup.add(btn5, btn6)
        markup.add(btn_back)
        
        bot_inst.send_message(chat_id, "📋 <b>Выберите причину репорта:</b>", reply_markup=markup, parse_mode='HTML')

async def tida_report_task(user_id: int, target: str, description: str, chat_id: int, bot_inst):
    session_path, session_name = await find_tida_session()
    if not session_path:
        bot_inst.send_message(chat_id, "❌ Не найдена сессия TIDA в папке TIDA/")
        return
    client = TelegramClient(session_path.replace('.session', ''), API_ID, API_HASH, proxy=TIDA_PROXY)
    try:
        await client.connect()
        if not await client.is_user_authorized():
            bot_inst.send_message(chat_id, "❌ Сессия TIDA не авторизована.")
            return
        bot_inst.send_message(chat_id, f"🔄 TIDA Report запущен для {target}...")
        await send_tida_message(client, "/start", 1.5)
        await send_tida_message(client, target, 1.5)
        await send_tida_message(client, "Non-consensual intimate image sharing", 1.5)
        await send_tida_message(client, description, 1.5)
        await send_tida_message(client, "Proceed without documentation", 1.5)
        await send_tida_message(client, "Confirm", 1.5)
        bot_inst.send_message(chat_id, "✅ <b>Жалоба успешно отправлена через TIDA!</b>", parse_mode='HTML')
        random_digits = ''.join(random.choices('0123456789', k=7))
        log_filename = f"Meta_TIDA_{random_digits}.txt"
        log_content = f"""┌TIDA Report | User: {user_id} | @{bot_inst.get_me().username}
├ [🟢] Успешно: 1
├ Link: {target}
"""
        with open(log_filename, 'w', encoding='utf-8') as f:
            f.write(log_content)
        try:
            with open(log_filename, 'rb') as f:
                bot_inst.send_document(chat_id, f, caption="✅ TIDA Report лог")
            await send_log_to_group(log_filename, f"TIDA Report | User: {user_id} | Link: {target}")
        except Exception as e:
            print(f"Ошибка отправки TIDA лога: {e}")
        finally:
            try:
                os.remove(log_filename)
            except:
                pass
    except Exception as e:
        bot_inst.send_message(chat_id, f"❌ Ошибка TIDA: {str(e)}")
    finally:
        try:
            await client.disconnect()
        except:
            pass

# Единая функция для запуска бота (и основного, и зеркал)
def launch_bot(token: str, is_main: bool = False):
    while True:
        try:
            bot_instance = telebot.TeleBot(token)
            
            bot_instance.delete_webhook(drop_pending_updates=True)
            
            patch_bot_send_message(bot_instance)
            register_all_handlers(bot_instance)
            
            me = bot_instance.get_me()
            name = f"@{me.username}" if me and me.username else "Неизвестный Бот"
            
            print(f"✅ {'ОСНОВНОЙ БОТ' if is_main else 'ЗЕРКАЛО'} {name} успешно запущен!")

            bot_instance.infinity_polling(none_stop=True, allowed_updates=['message', 'callback_query'])
            
        except Exception as e:
            print(f"❌ Ошибка в работе бота (token {token[:10]}...): {e}")
            if "Unauthorized" in str(e):
                print(f"⚠️ Токен {token[:10]}... недействителен. Бот отключен.")
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
