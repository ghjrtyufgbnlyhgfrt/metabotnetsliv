from flask import Flask, render_template_string, request, jsonify
from telethon import TelegramClient, events
import asyncio
import time
from datetime import datetime
import threading

app = Flask(__name__)

# Ваши данные API
API_ID = 25874957
API_HASH = "c89ef6fd9ba5c8a479abb1f4d2de248d"

# Глобальные переменные
checking_active = False
bot_username = ""
start_time = None          # timestamp в миллисекундах
bot_deleted_time = None
deletion_elapsed = None    # Новое: точное время жизни бота
check_task = None

HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Telegram Bot Monitor</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <style>
        .timer-container {
            min-height: 420px;
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
        }
        @keyframes pulse {
            0% { transform: scale(1); }
            50% { transform: scale(1.05); }
            100% { transform: scale(1); }
        }
        .pulsing { animation: pulse 2s infinite; }
        .status-active { color: #10b981; }
        .status-deleted { color: #ef4444; }
    </style>
</head>
<body class="bg-gradient-to-br from-gray-900 via-gray-800 to-gray-900 min-h-screen flex items-center justify-center p-4">
    <div class="max-w-2xl w-full bg-gray-800/50 backdrop-blur-lg rounded-2xl shadow-2xl border border-gray-700 p-8">
        <h1 class="text-4xl font-bold text-center text-white mb-8 tracking-tight">
            🤖 <span class="bg-gradient-to-r from-blue-400 to-purple-400 bg-clip-text text-transparent">Bot Monitor</span>
        </h1>
       
        <!-- Ввод юзернейма -->
        <div class="mb-8">
            <div class="flex gap-3">
                <input
                    type="text"
                    id="username-input"
                    placeholder="Введите @username бота"
                    class="flex-1 px-4 py-3 bg-gray-700/50 border border-gray-600 rounded-xl text-white placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent transition-all"
                    value="{{ bot_username }}"
                    {% if checking_active %}disabled{% endif %}
                >
                <button
                    id="start-btn"
                    onclick="startMonitoring()"
                    class="px-6 py-3 bg-gradient-to-r from-blue-500 to-purple-500 text-white font-semibold rounded-xl hover:from-blue-600 hover:to-purple-600 transition-all transform hover:scale-105 disabled:opacity-50 disabled:cursor-not-allowed"
                    {% if checking_active %}disabled{% endif %}
                >
                    Начать
                </button>
                <button
                    id="reset-btn"
                    onclick="resetMonitoring()"
                    class="px-6 py-3 bg-gradient-to-r from-red-500 to-pink-500 text-white font-semibold rounded-xl hover:from-red-600 hover:to-pink-600 transition-all transform hover:scale-105 disabled:opacity-50 disabled:cursor-not-allowed"
                    {% if not checking_active and not bot_deleted_time %}disabled{% endif %}
                >
                    Сброс
                </button>
            </div>
            <div id="error-message" class="text-red-400 text-sm mt-2 hidden"></div>
        </div>

        <!-- Статус и таймер -->
        <div class="timer-container bg-gray-700/30 rounded-xl border border-gray-600 p-6">
            <div class="text-center">
                <div class="text-gray-400 text-sm uppercase tracking-wider mb-2">Статус мониторинга</div>
                <div id="status-text" class="text-2xl font-bold mb-6">
                    {% if checking_active %}
                        <span class="status-active">🔍 Мониторинг активен</span>
                    {% elif bot_deleted_time %}
                        <span class="status-deleted">❌ Бот удалён</span>
                    {% else %}
                        <span class="text-gray-400">⏸ Ожидание запуска</span>
                    {% endif %}
                </div>

                <div class="grid grid-cols-2 gap-6 mb-6">
                    <div>
                        <div class="text-gray-400 text-sm">Бот</div>
                        <div id="bot-display" class="text-white font-mono text-lg">{{ bot_username if bot_username else '—' }}</div>
                    </div>
                    <div>
                        <div class="text-gray-400 text-sm">Время жизни</div>
                        <div id="timer-display" class="text-white font-mono text-3xl font-bold">
                            {{ elapsed_time if elapsed_time else '00:00:00' }}
                        </div>
                    </div>
                </div>

                {% if bot_deleted_time %}
                <div class="bg-red-500/20 border border-red-500/30 rounded-xl p-5 mt-4">
                    <div class="text-red-400 font-semibold text-lg">⏱ Бот был удалён через <span class="text-2xl">{{ deletion_elapsed or elapsed_time }}</span></div>
                    <div class="text-gray-400 text-sm mt-2">Время удаления: {{ bot_deleted_time }}</div>
                </div>
                {% endif %}

                <div id="live-timer" class="text-gray-500 text-sm mt-6">
                    {% if checking_active %}
                        <span class="animate-pulse">● Мониторинг запущен... Проверка каждые 5 сек</span>
                    {% elif bot_deleted_time %}
                        <span>● Мониторинг завершён</span>
                    {% else %}
                        <span>● Введите юзернейм и нажмите "Начать"</span>
                    {% endif %}
                </div>
            </div>
        </div>
    </div>

    <script>
        let updateInterval = null;
        let startTime = {{ start_time if start_time else 'null' }};
        let isActive = {{ 'true' if checking_active else 'false' }};

        function formatTime(ms) {
            const elapsed = Math.floor(ms / 1000);
            const hours = String(Math.floor(elapsed / 3600)).padStart(2, '0');
            const minutes = String(Math.floor((elapsed % 3600) / 60)).padStart(2, '0');
            const seconds = String(elapsed % 60).padStart(2, '0');
            return `${hours}:${minutes}:${seconds}`;
        }

        async function updateStatus() {
            try {
                const response = await fetch('/status');
                const data = await response.json();

                document.getElementById('bot-display').textContent = data.bot_username || '—';
                document.getElementById('status-text').innerHTML = data.status_html;

                const timerEl = document.getElementById('timer-display');
                if (data.deleted) {
                    timerEl.textContent = data.deletion_elapsed || '—';
                } else if (data.start_time) {
                    timerEl.textContent = formatTime(Date.now() - data.start_time);
                }

                // Обновляем кнопку сброса
                document.getElementById('reset-btn').disabled = !(data.checking_active || data.deleted);
            } catch (e) {
                console.error("Ошибка обновления статуса", e);
            }
        }

        async function startMonitoring() {
            const username = document.getElementById('username-input').value.trim();
            if (!username || !username.startsWith('@')) {
                showError('Введите корректный @username бота');
                return;
            }

            const btn = document.getElementById('start-btn');
            btn.disabled = true;
            btn.textContent = 'Запуск...';

            try {
                const response = await fetch('/start', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({username: username})
                });
                const data = await response.json();

                if (data.success) {
                    location.reload();
                } else {
                    showError(data.error || 'Ошибка запуска');
                    btn.disabled = false;
                    btn.textContent = 'Начать';
                }
            } catch (error) {
                showError('Ошибка соединения');
                btn.disabled = false;
                btn.textContent = 'Начать';
            }
        }

        async function resetMonitoring() {
            if (!confirm('Сбросить мониторинг?')) return;
            await fetch('/reset', {method: 'POST'});
            location.reload();
        }

        function showError(message) {
            const errorEl = document.getElementById('error-message');
            errorEl.textContent = message;
            errorEl.classList.remove('hidden');
        }

        // Автообновление каждые 2 секунды
        updateInterval = setInterval(updateStatus, 2000);
        updateStatus(); // первый запуск
    </script>
</body>
</html>
"""

# Telethon клиент
client = None

async def check_bot_status(username):
    global client
    if not client:
        client = TelegramClient('session', API_ID, API_HASH)
        await client.start()

    try:
        entity = await client.get_entity(username)
        if hasattr(entity, 'bot') and not entity.bot:
            return False, "Перестал быть ботом"
        if not entity.username or entity.username.lower() != username.lower().replace('@', ''):
            return False, "Юзернейм стал невалидным"
        return True, None
    except Exception as e:
        error_msg = str(e).lower()
        if any(x in error_msg for x in ['username', 'not found', 'entity']):
            return False, "Бот был удалён"
        return True, None

async def monitoring_loop(username):
    global checking_active, bot_username, start_time, bot_deleted_time, deletion_elapsed

    checking_active = True
    bot_username = username
    start_time = int(time.time() * 1000)
    bot_deleted_time = None
    deletion_elapsed = None

    print(f"🚀 Начат мониторинг бота {username}")

    try:
        while checking_active:
            is_valid, message = await check_bot_status(username)

            if not is_valid:
                bot_deleted_time = datetime.now().strftime("%H:%M:%S %d.%m.%Y")
                # Фиксируем точное время жизни
                deletion_elapsed = format_time(int(time.time() * 1000) - start_time)
                checking_active = False
                print(f"❌ Бот {username} удалён через {deletion_elapsed}")
                break

            await asyncio.sleep(5)
    except Exception as e:
        print(f"Ошибка мониторинга: {e}")
        checking_active = False

def format_time(ms):
    elapsed = ms // 1000
    h = elapsed // 3600
    m = (elapsed % 3600) // 60
    s = elapsed % 60
    return f"{h:02d}:{m:02d}:{s:02d}"

@app.route('/')
def index():
    elapsed_time = ""
    if start_time and not bot_deleted_time:
        elapsed_time = format_time(int(time.time() * 1000) - start_time)

    return render_template_string(
        HTML_TEMPLATE,
        checking_active=checking_active,
        bot_username=bot_username,
        start_time=start_time,
        bot_deleted_time=bot_deleted_time,
        elapsed_time=elapsed_time,
        deletion_elapsed=deletion_elapsed
    )

@app.route('/status')
def get_status():
    if checking_active and start_time:
        elapsed = format_time(int(time.time() * 1000) - start_time)
        status_html = '<span class="status-active">🔍 Мониторинг активен</span>'
    elif bot_deleted_time:
        elapsed = deletion_elapsed or "—"
        status_html = '<span class="status-deleted">❌ Бот удалён</span>'
    else:
        elapsed = "00:00:00"
        status_html = '<span class="text-gray-400">⏸ Ожидание запуска</span>'

    return jsonify({
        "checking_active": checking_active,
        "bot_username": bot_username,
        "start_time": start_time,
        "deleted": bool(bot_deleted_time),
        "deletion_elapsed": deletion_elapsed,
        "elapsed": elapsed,
        "status_html": status_html
    })

@app.route('/start', methods=['POST'])
def start_monitoring():
    global checking_active, check_task

    if checking_active:
        return jsonify({'success': False, 'error': 'Мониторинг уже запущен'})

    data = request.json
    username = data.get('username', '').strip()

    if not username.startswith('@'):
        return jsonify({'success': False, 'error': 'Юзернейм должен начинаться с @'})

    # Сброс предыдущих данных
    global bot_deleted_time, deletion_elapsed, start_time
    bot_deleted_time = None
    deletion_elapsed = None
    start_time = None

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    def run_monitoring():
        loop.run_until_complete(monitoring_loop(username))

    thread = threading.Thread(target=run_monitoring, daemon=True)
    thread.start()

    time.sleep(0.5)
    return jsonify({'success': True})

@app.route('/reset', methods=['POST'])
def reset_monitoring():
    global checking_active, bot_username, start_time, bot_deleted_time, deletion_elapsed
    checking_active = False
    bot_username = ""
    start_time = None
    bot_deleted_time = None
    deletion_elapsed = None
    return jsonify({'success': True})

if __name__ == '__main__':
    print("🚀 Bot Monitor запущен")
    print("🌐 Откройте: http://127.0.0.1:8080")
    app.run(debug=True, host='127.0.0.1', port=8080)