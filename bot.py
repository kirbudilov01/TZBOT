import logging
import sqlite3
import os
import asyncio
from aiogram import Bot, Dispatcher, types
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from docx import Document
import openai

# API ключи из переменных окружения
API_TOKEN = os.getenv("API_TOKEN")  
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

if not API_TOKEN:
    raise ValueError("❌ Ошибка: API_TOKEN не найден! Проверь настройки Render.")
# Проверяем, есть ли токен
if not API_TOKEN:
    raise ValueError("❌ Ошибка: API_TOKEN не найден! Проверь настройки Render.")

bot = Bot(token=API_TOKEN)
dp = Dispatcher(bot)
# Логирование
logging.basicConfig(level=logging.INFO)

# Инициализация бота и диспетчера
bot = Bot(token=API_TOKEN)
dp = Dispatcher(bot, storage=MemoryStorage())

# Подключение к базе данных SQLite
conn = sqlite3.connect("tz_database.db")
cursor = conn.cursor()
cursor.execute('''CREATE TABLE IF NOT EXISTS requests (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    business_goal TEXT,
    key_features TEXT,
    integrations TEXT,
    target_audience TEXT,
    monetization TEXT,
    additional_questions TEXT,
    generated_tz TEXT
)''')
conn.commit()

# Определяем состояния
class Form(StatesGroup):
    business_goal = State()
    key_features = State()
    integrations = State()
    target_audience = State()
    monetization = State()
    additional = State()

# Команда /start
@dp.message_handler(commands=['start'])
async def start(message: types.Message):
    await message.answer("Привет! Я помогу составить техническое задание на веб-приложение или бота. Начнем с главного вопроса: Какая основная цель вашего продукта? (Например: автоматизация заказов, поддержка клиентов, маркетинг и т.д.)")
    await Form.business_goal.set()

# Вопрос 1: Цель бизнеса
@dp.message_handler(state=Form.business_goal, content_types=[types.ContentType.TEXT, types.ContentType.VOICE])
async def process_business_goal(message: types.Message, state: FSMContext):
    if message.voice:
        file = await bot.get_file(message.voice.file_id)
        text = "(Аудио-ответ: см. запись)"
    else:
        text = message.text
    async with state.proxy() as data:
        data['business_goal'] = text
    await message.answer("Какие ключевые функции должны быть у вашего веб-приложения или бота? (Например: чат, CRM-система, онлайн-оплата, аналитика)")
    await Form.key_features.set()

# Вопрос 2: Основные функции
@dp.message_handler(state=Form.key_features)
async def process_key_features(message: types.Message, state: FSMContext):
    async with state.proxy() as data:
        data['key_features'] = message.text
    await message.answer("Какие внешние сервисы или API вам нужно интегрировать? (Например: платежные системы, CRM, AI-боты, маркетинговые платформы)")
    await Form.integrations.set()

# Вопрос 3: Интеграции
@dp.message_handler(state=Form.integrations)
async def process_integrations(message: types.Message, state: FSMContext):
    async with state.proxy() as data:
        data['integrations'] = message.text
    await message.answer("Кто ваша основная целевая аудитория? (Например: малый бизнес, корпоративные клиенты, конечные пользователи)")
    await Form.target_audience.set()

# Вопрос 4: Целевая аудитория
@dp.message_handler(state=Form.target_audience)
async def process_target_audience(message: types.Message, state: FSMContext):
    async with state.proxy() as data:
        data['target_audience'] = message.text
    await message.answer("Как вы планируете монетизировать продукт? (Например: подписка, разовая оплата, freemium-модель)")
    await Form.monetization.set()

# Вопрос 5: Монетизация
@dp.message_handler(state=Form.monetization)
async def process_monetization(message: types.Message, state: FSMContext):
    async with state.proxy() as data:
        data['monetization'] = message.text
    await generate_tz(message, state)

# Генерация документа с ТЗ
async def generate_tz(message, state):
    async with state.proxy() as data:
        document = Document()
        document.add_heading("Техническое задание", level=1)
        document.add_paragraph(f"📌 Основная цель: {data['business_goal']}")
        document.add_paragraph(f"🔹 Ключевые функции: {data['key_features']}")
        document.add_paragraph(f"🔗 Интеграции: {data['integrations']}")
        document.add_paragraph(f"🎯 Целевая аудитория: {data['target_audience']}")
        document.add_paragraph(f"💰 Монетизация: {data['monetization']}")
        
        file_path = f"tz_{message.from_user.id}.docx"
        document.save(file_path)
        
        with open(file_path, "rb") as file:
            await message.answer("Спасибо! Вот ваше техническое задание:")
            await bot.send_document(message.chat.id, file)
        
        os.remove(file_path)
    await state.finish()

# Запуск бота
async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
