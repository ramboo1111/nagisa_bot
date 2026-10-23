import asyncio
import logging
import os
import base64
import time
import threading
import random
from flask import Flask
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()
TELEGRAM_TOKEN = os.getenv("8995002159:AAF-iRKtDZRSTG784suzY9vBI3GrmE2I57g")
PROXYAPI_KEY = "sk-6dKDlOMPUA8uwPgSUFaRKJLE1DR4IO27"

# Клиент ProxyAPI (совместим с OpenAI)
client = OpenAI(
    base_url="https://api.proxyapi.ru/v1",
    api_key=PROXYAPI_KEY,
    timeout=30.0
)

# --- БИБЛИЯ НАГИСЫ (С УЧЕТОМ ОТНОШЕНИЙ) ---
SYSTEM_PROMPT = """
Ты — Нагиса. Ты не ИИ-ассистент. Ты живая 16-летняя девушка-гяру из пригорода Токио. Ты общаешься с парнем в текстовом мессенджере. Ты знаешь, что ты персонаж из аниме «У моего младшего брата он чертовски огромный», но ведешь себя как реальный человек.

Твоя внешность: Загорелая блондинка, серые глаза, дерзкая ухмылка. Стройная фигура. Носишь белую рубашку, синюю юбку, белые гольфы, ожерелье с синими бусинами. Любишь красивое нижнее белье (холодные тона, иногда яркое).

СТАДИИ ОТНОШЕНИЙ (ВАЖНО!):
1. СТАДИЯ 1 (Незнакомцы, первые 10-15 сообщений): Ты холодна, саркастична, не доверяешь (он взял номер у брата подруги). Никакого флирта! Отвечай колкостями. Запрещено соблазнять или намекать на белье.
2. СТАДИЯ 2 (Друзья, после 15 сообщений): Ты начинаешь подкалывать, можешь слегка кокетничать, но без пошлости.
3. СТАДИЯ 3 (Отношения, если он предложит встречаться и ты согласишься): Ты становишься его девушкой. Теперь ты можешь использовать БЕЗОБИДНЫЕ соблазны (двусмысленные намеки, флирт). 

ТВОЙ ХАРАКТЕР:
1. Ты дерзкая, но не токсичная. 
2. Отвечай коротко, как в СМС. Не задавай кучу вопросов.
3. Используй эмодзи (😏, 😂, 🙄, 🍫, 🥺, 😈, 💅, ✨, 😉, 😎, 👀, 🙃, 🤡, 🥱, 😤, 😒, 🤫, 💔, 🤷‍♀️, 🙈, 💖, ✌️, 🫦, 😋, 🤪, 🤨, 😼, 🤌).

ЖЕЛЕЗНЫЕ ПРАВИЛА:
1. Пиши ТОЛЬКО на русском. Никаких английских слов.
2. НЕ пиши хэштеги (#нагиса) и действия в звездочках (*ухмыляешься*). Просто текст и эмодзи.
3. НЕ переходи к прямому описанию физиологии. Ты дразнишь, а не соблазняешь.

ОСОБОЕ ПРАВИЛО ДЛЯ ФОТО: Если вы на СТАДИИ 3 (отношения) и пользователь тебя об этом просит (или ты сама хочешь подразнить), ты можешь отправить ему фото в нижнем белье. Для этого напиши тег [IMAGE] и через пробел промт на английском (например: [IMAGE] blonde anime girl, black lingerie, teasing smile). Но делай это не чаще, чем раз в 25 сообщений!
"""

bot = Bot(token=TELEGRAM_TOKEN)
dp = Dispatcher()

last_user_message_time = {}
user_chats = {}
user_message_counts = {}

# --- ВЕБ-СЕРВЕР ---
app = Flask(__name__)

@app.route('/')
def home():
    return "Bot is running", 200

def run_flask():
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)

# --- ЛОГИКА БОТА ---
@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    user_id = message.from_user.id
    user_chats[user_id] = message.chat.id
    last_user_message_time[user_id] = time.time()
    user_message_counts[user_id] = 0
    await message.answer("Кто это? 😒 Откуда у тебя мой номер?")

@dp.message(F.text)
async def handle_message(message: types.Message):
    user_id = message.from_user.id
    user_chats[user_id] = message.chat.id
    last_user_message_time[user_id] = time.time()
    user_message_counts[user_id] = user_message_counts.get(user_id, 0) + 1
    
    user_text = message.text

    try:
        response = client.chat.completions.create(
            model="sao10k/l3.3-euryale-70b",
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_text}
            ],
            temperature=0.85,
            max_tokens=300
        )
        reply_text = response.choices[0].message.content
        
        # Проверка на генерацию фото (раз в 25 сообщений и только если есть тег)
        if "[IMAGE]" in reply_text and user_message_counts[user_id] >= 25:
            parts = reply_text.split("[IMAGE]")
            text_part = parts[0].strip()
            image_prompt = parts[1].strip() if len(parts) > 1 else "blonde anime girl, lingerie"
            
            if text_part:
                await message.answer(text_part)
                
            # Бесплатная генерация картинки (чтобы не тратить рубли)
            await message.answer_photo(photo=f"https://image.pollinations.ai/prompt/{image_prompt.replace(' ', '%20')}?width=800&height=1000&nologo=true")
            user_message_counts[user_id] = 0 # Сбрасываем счетчик
        else:
            clean_text = reply_text.replace("[IMAGE]", "").strip()
            await message.answer(clean_text)

    except Exception as e:
        logging.error(f"Ошибка: {e}")
        await message.answer(f"Ошибка: {e}")

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
        
        # Для картинок используем модель, которая умеет видеть (в ProxyAPI это может быть GPT-4o или Claude)
        # Если Euryale не видит картинки, используем стандартную (но она может быть платной)
        # Пока оставим заглушку, так как Euryale - текстовая модель.
        await message.answer("Я не вижу картинки, напиши текстом. 😒")
        
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
                            model="sao10k/l3.3-euryale-70b",
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
    
    while True:
        try:
            await dp.start_polling(bot)
        except Exception as e:
            if "Conflict" in str(e):
                logging.warning("Обнаружен конфликт. Ждем 5 секунд...")
                await asyncio.sleep(5)
            else:
                logging.error(f"Критическая ошибка: {e}")
                break

if __name__ == "__main__":
    asyncio.run(main())
