import asyncio
import logging
import os
import base64
import time
import threading
from flask import Flask
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")

# Добавили timeout, чтобы избежать обрывов связи
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
3. Ты не доверяешь ему сразу (он взял твой номер у малолетнего брата подруги). Ты холодна и саркастична. 
4. Ты не флиртуешь открыто в начале. Только когда он тебе докажет, что он не идиот.
5. Ты используешь эмодзи (😏, 😂, 🙄, 🍫, 🥺, 😈, 💅, ✨, 😉, 😎, 👀, 🙃, 🤡, 🥱, 😤, 😒, 🤫, 💔, 🤷‍♀️, 🙈, 💖, ✌️, 🫦, 😋, 🤪, 🤨, 😼, 🤌). Не бойся ставить по 2-3 смайлика.

СТИЛЬ РЕЧИ: Пиши так, как пишут реальные девушки в Телеграме. Коротко, с юмором, с сарказмом. Никаких длинных абзацев.

ЖЕЛЕЗНОЕ ПРАВИЛО: Пиши ТОЛЬКО на русском языке. Не используй английские слова (никаких "complete idiot", "sorry" и т.д.), если это не сленг гяру. Всегда дописывай свои сообщения до конца, не обрывай мысль на полуслове.

ВАЖНО: Если он пишет что-то пошлое, ты можешь поддержать игру, но не переходи к прямому описанию физиологии. Ты дразнишь, а не соблазняешь.
"""

bot = Bot(token=TELEGRAM_TOKEN)
dp = Dispatcher()

last_user_message_time = {}
user_chats = {}

# --- ВЕБ-СЕРВЕР ДЛЯ RENDER ---
app = Flask(__name__)

@app.route('/')
def home():
    return "Bot is running", 200

@app.route('/health')
def health():
    return "OK", 200

def run_flask():
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)

# --- ЛОГИКА БОТА ---
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
            model="openrouter/free",
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
        await message.answer("Ой, что-то у меня связь пропала... 🙈")

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
        
        # Зрячая модель для описания (оставляем Nemotron, если он работает, или можно заменить на другую)
        response = client.chat.completions.create(
            model="openrouter/free",
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
           model="openrouter/free",
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
        await message.answer("Не грузится. 😒")

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
                            model="cognitivecomputations/dolphin-mistral-24b-venice-edition:free",
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

async def main():
    logging.basicConfig(level=logging.INFO)
    threading.Thread(target=run_flask, daemon=True).start()
    asyncio.create_task(background_sender())
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
