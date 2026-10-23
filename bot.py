import asyncio
import logging
import os
import base64
from aiohttp import web
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.webhook.aiohttp_server import SimpleRequestHandler, setup_application
from openai import OpenAI

# --- КЛЮЧИ (ВШИТЫ В КОД) ---
TELEGRAM_TOKEN = "8995002159:AAF-iRKtDZRSTG784suzY9vBI3GrmE2I57g"
PROXYAPI_KEY = "sk-6dKDlOMPUA8uwPgSUFaRKJLE1DR4IO27"
RENDER_EXTERNAL_URL = "https://nagisa-bot-1.onrender.com"

# --- НАСТРОЙКА КЛИЕНТА ---
# Важно: для доступа ко всем моделям (включая Euryale) используем этот адрес
client = OpenAI(
    base_url="https://api.proxyapi.ru/v1",
    api_key=PROXYAPI_KEY,
    timeout=30.0
)

# --- БИБЛИЯ НАГИСЫ ---
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
user_message_counts = {}

# --- ЛОГИКА БОТА ---
@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    user_id = message.from_user.id
    user_message_counts[user_id] = 0
    await message.answer("Кто это? 😒 Откуда у тебя мой номер?")

@dp.message(F.text)
async def handle_message(message: types.Message):
    user_id = message.from_user.id
    user_message_counts[user_id] = user_message_counts.get(user_id, 0) + 1
    user_text = message.text

    try:
        response = client.chat.completions.create(
            model="sao10k/l3.1-euryale-70b", # Наша любимая Euryale
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_text}
            ],
            temperature=0.85,
            max_tokens=400
        )
        reply_text = response.choices[0].message.content
        
        # Проверка на генерацию фото
        if "[IMAGE]" in reply_text and user_message_counts[user_id] >= 25:
            parts = reply_text.split("[IMAGE]")
            text_part = parts[0].strip()
            image_prompt = parts[1].strip() if len(parts) > 1 else "blonde anime girl, lingerie"
            if text_part:
                await message.answer(text_part)
            # Бесплатная генерация картинки
            await message.answer_photo(photo=f"https://image.pollinations.ai/prompt/{image_prompt.replace(' ', '%20')}?width=800&height=1000&nologo=true")
            user_message_counts[user_id] = 0
        else:
            clean_text = reply_text.replace("[IMAGE]", "").strip()
            await message.answer(clean_text)

    except Exception as e:
        logging.error(f"Ошибка: {e}")
        await message.answer(f"Ошибка: {e}")

# --- WEBHOOK ДЛЯ RENDER ---
async def on_startup(bot: Bot):
    await bot.set_webhook(f"{RENDER_EXTERNAL_URL}/{TELEGRAM_TOKEN}")
    logging.info("Webhook установлен")

async def main():
    logging.basicConfig(level=logging.INFO)
    dp.startup.register(on_startup)
    
    app = web.Application()
    webhook_requests_handler = SimpleRequestHandler(dispatcher=dp, bot=bot)
    webhook_requests_handler.register(app, path=f"/{TELEGRAM_TOKEN}")
    setup_application(app, dp, bot=bot)
    
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))
    await site.start()
    
    logging.info("Бот запущен и слушает порт")
    await asyncio.Event().wait() # Бесконечное ожидание

if __name__ == "__main__":
    asyncio.run(main())
