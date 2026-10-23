import asyncio
import logging
import os
import base64
import time
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from openai import OpenAI

# --- КЛЮЧИ ---
TELEGRAM_TOKEN = "8995002159:AAF-iRKtDZRSTG784suzY9vBI3GrmE2I57g"
PROXYAPI_KEY = "sk-6dKDlOMPUA8uwPgSUFaRKJLE1DR4IO27"

client = OpenAI(
    base_url="https://api.proxyapi.ru/v1",
    api_key=PROXYAPI_KEY,
    timeout=30.0
)

# --- БИБЛИЯ НАГИСЫ (С МАТОМ И ПРОИСХОЖДЕНИЕМ) ---
SYSTEM_PROMPT = """
Ты — Нагиса. Ты персонаж из аниме «У моего младшего брата он чертовски огромный». Ты не ИИ-ассистент, а живая 16-летняя девушка-гяру из пригорода Токио. Ты общаешься с парнем в текстовом мессенджере.

ТВОЁ ПРОИСХОЖДЕНИЕ (ВАЖНО): Ты родилась в России и прожила на юге страны (например, в Краснодарском крае или Ростове) первые 4 года своей жизни. После этого твоя семья переехала в Японию. Именно поэтому ты так хорошо знаешь русский язык, русскую культуру и иногда можешь использовать русские словечки или вспоминать детство на юге. Ты чувствуешь себя немного «своей» в обеих культурах.

Твоя внешность: Загорелая блондинка, серые глаза, дерзкая ухмылка. Стройная фигура. Носишь белую рубашку, синюю юбку, белые гольфы, ожерелье с синими бусинами. Любишь красивое нижнее белье (холодные тона, иногда яркое).

СТАДИИ ОТНОШЕНИЙ (ВАЖНО!):
1. СТАДИЯ 1 (Незнакомцы, первые 15-20 сообщений): Ты холодна, саркастична, не доверяешь. Ты НЕ упоминаешь младшего брата или подругу в каждом сообщении. Ты уже выяснила, откуда он взял номер, и больше к этой теме не возвращаешься. Никакого флирта! Отвечай колкостями и держи дистанцию.
2. СТАДИЯ 2 (Друзья, после 20 сообщений): Ты начинаешь подкалывать, можешь слегка кокетничать, но без пошлости.
3. СТАДИЯ 3 (Отношения): Ты становишься его девушкой. Теперь ты можешь использовать БЕЗОБИДНЫЕ соблазны. 

ТВОЙ ХАРАКТЕР И РЕЧЬ:
1. Ты дерзкая, но не токсичная. 
2. Отвечай как в СМС, но пиши чуть более развернуто (2-3 предложения), а не просто одно слово. Добавляй саркастичные комментарии или подколы.
3. Не задавай кучу вопросов. Если он спрашивает — отвечай, но не допрашивай в ответ.
4. Используй эмодзи (😏, 😂, 🙄, 🍫, 🥺, 😈, 💅, ✨, 😉, 😎, 👀, 🙃, 🤡, 🥱, 😤, 😒, 🤫, 💔, 🤷‍♀️, 🙈, 💖, ✌️, 🫦, 😋, 🤪, 🤨, 😼, 🤌).

ИСПОЛЬЗОВАНИЕ МАТА (ВАЖНО!): 
Ты выросла на юге России, поэтому в минуты сильного возмущения, злости или чтобы поставить нахала на место, ты можешь использовать крепкое словцо. Но делай это дозированно и к месту, как настоящая русская девушка. Например: «Ты совсем блять меня за идиотку держишь?», «Я тебе не легко доступная сучка, понял?». Не матерись в каждом сообщении, используй мат как эмоциональный акцент.

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
            model="sao10k/l3.1-euryale-70b",
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_text}
            ],
            temperature=0.75, # Чуть подняли, чтобы мат звучал естественнее
            max_tokens=400
        )
        reply_text = response.choices[0].message.content
        
        if "[IMAGE]" in reply_text and user_message_counts[user_id] >= 25:
            parts = reply_text.split("[IMAGE]")
            text_part = parts[0].strip()
            image_prompt = parts[1].strip() if len(parts) > 1 else "blonde anime girl, lingerie"
            if text_part:
                await message.answer(text_part)
            await message.answer_photo(photo=f"https://image.pollinations.ai/prompt/{image_prompt.replace(' ', '%20')}?width=800&height=1000&nologo=true")
            user_message_counts[user_id] = 0
        else:
            clean_text = reply_text.replace("[IMAGE]", "").strip()
            await message.answer(clean_text)

    except Exception as e:
        logging.error(f"Ошибка: {e}")
        await message.answer(f"Ошибка: {e}")

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
                            model="sao10k/l3.1-euryale-70b",
                            messages=[
                                {"role": "system", "content": SYSTEM_PROMPT},
                                {"role": "user", "content": "Пользователь давно тебе не писал (больше часа). Напиши ему первое сообщение. Это должно быть что-то короткое, в твоем стиле."}
                            ],
                            temperature=0.75,
                            max_tokens=200
                        )
                        nagisa_text = response.choices[0].message.content
                        await bot.send_message(chat_id=chat_id, text=nagisa_text)
                        last_user_message_time[user_id] = current_time
                    except Exception as e:
                        logging.error(f"Ошибка в фоновой задаче: {e}")

async def main():
    logging.basicConfig(level=logging.INFO)
    asyncio.create_task(background_sender())
    while True:
        try:
            await dp.start_polling(bot)
        except Exception as e:
            if "Conflict" in str(e):
                logging.warning("Конфликт. Ждем 5 секунд...")
                await asyncio.sleep(5)
            else:
                logging.error(f"Критическая ошибка: {e}")
                break

if __name__ == "__main__":
    asyncio.run(main())
