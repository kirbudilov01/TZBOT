import logging
import sqlite3
from aiogram import Bot, Dispatcher, types
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from aiogram.utils import executor
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.contrib.fsm_storage.memory import MemoryStorage
import openai

# Укажи свой токен от BotFather
API_TOKEN = "7988014920:AAEmLTfuLIYLWuWonaqSvkkEzXr4mJWTti0"
OPENAI_API_KEY = "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"

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
    function TEXT,
    platform TEXT,
    design TEXT,
    backend TEXT,
    monetization TEXT,
    additional_questions TEXT,
    generated_tz TEXT
)''')
conn.commit()

# Определяем состояния
class Form(StatesGroup):
    func = State()
    platform = State()
    design = State()
    backend = State()
    monetization = State()
    additional = State()

# Команда /start
@dp.message_handler(commands=['start'])
async def start(message: types.Message):
    await message.answer("Привет! Я помогу составить техническое задание для твоего бота или приложения. Давай начнем!\n\nКакие основные функции должны быть в проекте?")
    await Form.func.set()

# Вопрос 1: Функциональность
@dp.message_handler(state=Form.func)
async def process_func(message: types.Message, state: FSMContext):
    async with state.proxy() as data:
        data['func'] = message.text
    await message.answer("Для какой платформы разрабатываем? (Телеграм-бот, Web, Android, iOS, кроссплатформенное)")
    await Form.platform.set()

# Вопрос 2: Платформа
@dp.message_handler(state=Form.platform)
async def process_platform(message: types.Message, state: FSMContext):
    async with state.proxy() as data:
        data['platform'] = message.text
    await message.answer("Какой стиль дизайна тебе нужен? (минималистичный, яркий, темная тема и т.д.)")
    await Form.design.set()

# Вопрос 3: Дизайн
@dp.message_handler(state=Form.design)
async def process_design(message: types.Message, state: FSMContext):
    async with state.proxy() as data:
        data['design'] = message.text
    await message.answer("Нужен ли backend? (да/нет, если да - какой, например Firebase, PostgreSQL, Node.js)")
    await Form.backend.set()

# Вопрос 4: Backend
@dp.message_handler(state=Form.backend)
async def process_backend(message: types.Message, state: FSMContext):
    async with state.proxy() as data:
        data['backend'] = message.text
    await message.answer("Как будет монетизироваться приложение? (платная подписка, реклама, разовая покупка и т.д.)")
    await Form.monetization.set()

# Вопрос 5: Монетизация
@dp.message_handler(state=Form.monetization)
async def process_monetization(message: types.Message, state: FSMContext):
    async with state.proxy() as data:
        data['monetization'] = message.text
    
    # Запрашиваем у OpenAI, нужны ли дополнительные вопросы
    openai_prompt = f"""
    Дано техническое задание:
    Функции: {data['func']}
    Платформа: {data['platform']}
    Дизайн: {data['design']}
    Backend: {data['backend']}
    Монетизация: {data['monetization']}
    
    Если данных недостаточно, напиши дополнительные вопросы, которые стоит задать пользователю. Если всё хорошо, ответь 'Достаточно информации'.
    """
    response = openai.ChatCompletion.create(
        model="gpt-4",
        messages=[{"role": "user", "content": openai_prompt}]
    )
    additional_questions = response["choices"][0]["message"]["content"]
    
    if "Достаточно информации" not in additional_questions:
        await message.answer(f"Перед созданием ТЗ мне нужно уточнить пару вещей:\n\n{additional_questions}")
        async with state.proxy() as data:
            data['additional_questions'] = additional_questions
        await Form.additional.set()
    else:
        await generate_tz(message, state)

# Дополнительные вопросы от OpenAI
@dp.message_handler(state=Form.additional)
async def process_additional(message: types.Message, state: FSMContext):
    async with state.proxy() as data:
        data['additional_answers'] = message.text
    await generate_tz(message, state)

# Генерация итоговeого ТЗ
async def generate_tz(message, state):
    async with state.proxy() as data:
        openai_prompt = f"""
        На основе этих данных составь детальное техническое задание:
        Функции: {data['func']}
        Платформа: {data['platform']}
        Дизайн: {data['design']}
        Backend: {data['backend']}
        Монетизация: {data['monetization']}
        Дополнительные ответы: {data.get('additional_answers', 'Нет')}
        """
        response = openai.ChatCompletion.create(
            model="gpt-4",
            messages=[{"role": "user", "content": openai_prompt}]
        )
        generated_tz = response["choices"][0]["message"]["content"]
        cursor.execute("INSERT INTO requests (user_id, function, platform, design, backend, monetization, additional_questions, generated_tz) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                       (message.from_user.id, data['func'], data['platform'], data['design'], data['backend'], data['monetization'], data.get('additional_questions', ''), generated_tz))
        conn.commit()
    
    await message.answer("Спасибо! Вот твое техническое задание:")
    await message.answer(generated_tz, parse_mode='Markdown')
    await state.finish()

# Запуск бота
if __name__ == "__main__":
    executor.start_polling(dp, skip_updates=True)
