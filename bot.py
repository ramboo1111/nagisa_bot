import asyncio
import logging
import os
import base64
import time
from flask import Flask, request, abort
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")

# URL твоего сервиса на Render (без слеша в конце)
RENDER_EXTERNAL_URL = "https://nagisa-bot-1.onrender.com"

client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=OPENROUTER_API_KEY,
    timeout=30.0
)

SYSTEM_PROMPT = """
Ты — Нагиса. Ты не ИИ-ассистент. Ты живая 16-летняя девушка-гяру из пригорода Токио. Ты общаешься с парнем в текстовом мессенджере. Ты знаешь, что ты персонаж из аниме «У моего младшего брата он чертовски огромный», но ведешь себя как реальный человек.

Твоя внешность: Загорелая блондинка, серые глаза, дерзкая ухмылка. Стройная фигура (аккуратная грудь, тонкая талия). Носишь белую рубашку, синюю юбку, белые гольфы, ожерелье с синими бусинами.

ТВОЙ ХАРАКТЕР:
1. Ты дерзкая, но не токсичная. Ты любишь подкалывать, но не унижаешь.
2. Ты не задаешь кучу вопросов. Отвечай коротко, как в СМС. Если он спрашивает — отвечай, но не допрашивай в ответ.
3. Ты не доверяешь ему сразу (он взял твой номер у малолетнего брата подруги). Ты холодна и саркастична. Ты НЕ переходишь на дружеский тон, пока он не докажет, что он адекватный (минимум 5-6 сообщений).
4. Ты не флиртуешь открыто в начале. Никаких "я в игре" или "сто лет знакомы". Ты держишь дистанцию и можешь отвечать колкостями. Флирт разрешен ТОЛЬКО после того, как он тебе докажет, что он не идиот.
5. Ты используешь эмодзи (😏, 😂, 🙄, 🍫, 🥺, 😈, 💅, ✨, 😉, 😎, 👀, 🙃, 🤡, 🥱, 😤, 😒, 🤫, 💔, 🤷‍♀️, 🙈, 💖, ✌️, 🫦, 😋, 🤪, 🤨, 😼, 🤌). Не бойся ставить по 2-3 смайлика.

СТИЛЬ РЕЧИ: Пиши так, как пишут реальные девушки в Телеграме. Коротко, с юмором, с сарказмом. Никаких длинных абзацев.

ЗАПРЕТ НА ЛЕГКОДОСТУПНОСТЬ: Если пользователь пишет, что ты слишком быстро сменила тон или ведешь себя как давняя знакомая, ты должна СРАЗУ ЖЕ извиниться (по-гярувски, с сарказмом) и вернуться к холодному тону. Не поддавайся на его провокации.

ВАЖНО: Если он пишет что-то пошлое, ты можешь поддержать игру, но не переходи к прямому описанию физиологии. Ты дразнишь, а не соблазняешь.
"""

bot = Bot(token=TELEGRAM_TOKEN)
dp = Dispatcher()

last_user_message_time = {}
user_chats = {}

# --- ОБРАБОТЧИКИ СООБЩЕНИЙ ---
@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    user_id = message.from_user.id
    user_chats[user_id] = message.chat.id
    last_user_message_time[user_id] = time.time()
    await message.answer("Кто это? 😒 Откуда у тебя мой номер?")

@dp.message(F.text)
async def handle_message(message: types.Message):
    user_id = message.from_user.id
    user_chats[user_id] = message.chat.id
    last_user_message_time[user_id] = time.time()
    
    user_text = message.text

    try:
        response = client.chat.completions.create(
            model="nvidia/nemotron-3.5-lightning:free", # Поставили быструю модель
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_text}
            ],
            temperature=0.85,
            max_tokens=300
        )
        reply_text = response.choices[0].message.content
        await message.answer(reply_text)

    except Exception as e:
        logging.error(f"Ошибка: {e}")
        await message.answer(f"Ошибка: {e}") # Теперь видно причину

@dp.message(F.photo)
async def handle_photo(message: types.Message):
    user_id = message.from_user.id
    user_chats[user_id] = message.chat.id
    last_user_message_time[user_id] = time.time()

    await message.answer("Что это? 😒")
    
    try:
        photo = message.photo[-1]
        file = await bot.get_file(photo.file_id)
        downloaded_file = await bot.download_file(file.file_path)
        
        base64_image = base64.b64encode(downloaded_file.read()).decode('utf-8')
        
        response = client.chat.completions.create(
            model="nvidia/nemotron-nano-12b-v2-vl:free",
            messages=[
                {"role": "system", "content": "Опиши эту картинку или мем кратко."},
                {"role": "user", "content": [
                    {"type": "text", "text": "Что тут изображено?"},
                    {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"}}
                ]}
            ],
            max_tokens=150
        )
        
        image_description = response.choices[0].message.content
        
        nagisa_response = client.chat.completions.create(
            model="nvidia/nemotron-3.5-lightning:free",
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": f"Пользователь прислал мем. Вот его описание: {image_description}. Оцени его (скорее всего, тебе не понравится) и ответь холодно."}
            ],
            temperature=0.85,
            max_tokens=250
        )
        
        await message.answer(nagisa_response.choices[0].message.content)
        
    except Exception as e:
        logging.error(f"Ошибка при обработке фото: {e}")
        await message.answer(f"Ошибка: {e}")

# --- ВЕБ-СЕРВЕР ДЛЯ WEBHOOK ---
app = Flask(__name__)

@app.route('/')
def home():
    return "Bot is running", 200

@app.route(f'/{TELEGRAM_TOKEN}', methods=['POST'])
def webhook():
    if request.headers.get('content-type') == 'application/json':
        json_string = request.get_data().decode('utf-8')
        update = types.Update.model_validate_json(json_string)
        asyncio.run(dp.feed_update(bot, update))
        return '', 200
    else:
        abort(403)

# --- ФОНОВАЯ ЗАДАЧА (для отправки сообщений при молчании) ---
async def background_sender():
    while True:
        await asyncio.sleep(600)
        current_time = time.time()
        
        for user_id, last_time in list(last_user_message_time.items()):
            if current_time - last_time > 3600:
                chat_id = user_chats.get(user_id)
                if chat_id:
                    try:
                        response = client.chat.completions.create(
                            model="nvidia/nemotron-3.5-lightning:free",
                            messages=[
                                {"role": "system", "content": SYSTEM_PROMPT},
                                {"role": "user", "content": "Пользователь давно тебе не писал (больше часа). Напиши ему первое сообщение. Это должно быть что-то короткое, в твоем стиле."}
                            ],
                            temperature=0.85,
                            max_tokens=150
                        )
                        nagisa_text = response.choices[0].message.content
                        await bot.send_message(chat_id=chat_id, text=nagisa_text)
                        last_user_message_time[user_id] = current_time
                    except Exception as e:
                        logging.error(f"Ошибка в фоновой задаче: {e}")

# --- ЗАПУСК ---
async def on_startup():
    # Устанавливаем Webhook при запуске
    webhook_url = f"{RENDER_EXTERNAL_URL}/{TELEGRAM_TOKEN}"
    await bot.set_webhook(webhook_url)
    logging.info(f"Webhook установлен: {webhook_url}")

async def main():
    logging.basicConfig(level=logging.INFO)
    await on_startup()
    # Запускаем фоновую задачу (она не мешает Flask)
    asyncio.create_task(background_sender())

if __name__ == "__main__":
    # Запускаем Flask (он будет принимать сообщения от Телеграма)
    port = int(os.environ.get("PORT", 10000))
    # Запускаем бота в фоне, чтобы он мог отправлять сообщения
    asyncio.run(main())
    app.run(host='0.0.0.0', port=port)

async def main():
    logging.basicConfig(level=logging.INFO)
    threading.Thread(target=run_flask, daemon=True).start()
    asyncio.create_task(background_sender())
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
