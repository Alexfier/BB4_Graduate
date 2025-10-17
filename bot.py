import asyncio
import logging
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.utils.keyboard import InlineKeyboardBuilder
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
from sqlalchemy.orm import joinedload

from config import BOT_TOKEN, UPDATE_INTERVAL_HOURS
from database import DatabaseManager
from codeforces_api import CodeforcesAPI
from models import Problem

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Инициализация бота и диспетчера
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()
db = DatabaseManager()
cf_api = CodeforcesAPI()

# Состояния FSM
class ProblemSearch(StatesGroup):
    choosing_rating = State()
    choosing_tags = State()
    searching = State()

# Основные клавиатуры
def get_main_menu_keyboard():
    keyboard = InlineKeyboardBuilder()
    keyboard.button(text="🎯 Подбор задач", callback_data="problems_menu")
    keyboard.button(text="🔍 Поиск задач", callback_data="search_menu")
    keyboard.button(text="🎲 Случайная задача", callback_data="random_problem")
    keyboard.button(text="🆘 Помощь", callback_data="help")
    keyboard.adjust(2, 2)
    return keyboard.as_markup()

def get_back_keyboard(back_to: str = "main_menu"):
    keyboard = InlineKeyboardBuilder()
    keyboard.button(text="🔙 Назад", callback_data=back_to)
    return keyboard.as_markup()

def get_navigation_keyboard(back_to: str = "main_menu", show_main: bool = True):
    keyboard = InlineKeyboardBuilder()
    keyboard.button(text="🔙 Назад", callback_data=back_to)
    if show_main:
        keyboard.button(text="🏠 Главная", callback_data="main_menu")
    keyboard.adjust(2)
    return keyboard.as_markup()

def get_problems_navigation_keyboard():
    keyboard = InlineKeyboardBuilder()
    keyboard.button(text="🔄 Новый поиск", callback_data="problems_menu")
    keyboard.button(text="🎲 Случайная", callback_data="random_problem")
    keyboard.button(text="🏠 Главная", callback_data="main_menu")
    keyboard.adjust(2, 1)
    return keyboard.as_markup()

def get_search_navigation_keyboard():
    keyboard = InlineKeyboardBuilder()
    keyboard.button(text="🔍 Новый поиск", callback_data="search_menu")
    keyboard.button(text="🎯 Подбор задач", callback_data="problems_menu")
    keyboard.button(text="🏠 Главная", callback_data="main_menu")
    keyboard.adjust(2, 1)
    return keyboard.as_markup()

# Клавиатуры для фильтров
def get_ratings_keyboard(back_to: str = "main_menu"):
    ratings = db.get_available_ratings()
    keyboard = InlineKeyboardBuilder()
    
    # Группируем рейтинги по 5 в строке
    for i in range(0, len(ratings), 5):
        row_ratings = ratings[i:i+5]
        for rating in row_ratings:
            keyboard.button(text=str(rating), callback_data=f"rating_{rating}")
        keyboard.adjust(5)
    
    keyboard.button(text="❌ Без фильтра", callback_data="rating_none")
    keyboard.button(text="🔙 Назад", callback_data=back_to)
    keyboard.button(text="🏠 Главная", callback_data="main_menu")
    keyboard.adjust(1)
    return keyboard.as_markup()

def get_tags_keyboard(selected_tags=None, back_to: str = "problems_menu"):
    if selected_tags is None:
        selected_tags = []
        
    tags = db.get_available_tags()
    keyboard = InlineKeyboardBuilder()
    
    # Показываем первые 20 тегов для удобства
    for tag in tags[:20]:
        emoji = "✅" if tag in selected_tags else "⚪"
        keyboard.button(text=f"{emoji} {tag}", callback_data=f"tag_{tag}")
    
    keyboard.button(text="✅ Готово", callback_data="tags_done")
    keyboard.button(text="❌ Очистить", callback_data="tags_clear")
    keyboard.button(text="🔙 Назад", callback_data=back_to)
    keyboard.button(text="🏠 Главная", callback_data="main_menu")
    keyboard.adjust(2, 2)
    return keyboard.as_markup()

def format_problem_info_api(problem_data: dict) -> str:
    """Форматирование информации о задаче из API"""
    name = problem_data.get('name', 'Неизвестно')
    contest_id = problem_data.get('contestId', '?')
    index = problem_data.get('index', '?')
    rating = problem_data.get('rating', 'Не указана')
    solved_count = problem_data.get('solvedCount', 0)
    tags = ", ".join(problem_data.get('tags', []))
    
    info = f"""
📝 <b>{name}</b>

🔢 <b>Код:</b> {contest_id}{index}
⭐ <b>Сложность:</b> {rating}
✅ <b>Решений:</b> {solved_count}
🏷️ <b>Теги:</b> {tags if tags else 'Нет тегов'}

🔗 <a href="https://codeforces.com/problemset/problem/{contest_id}/{index}">Открыть на Codeforces</a>
    """.strip()
    
    return info

def format_problem_info(problem: Problem) -> str:
    """Форматирование информации о задаче из базы"""
    tags_list = [tag.name for tag in problem.tags]
    tags = ", ".join(tags_list)
    
    info = f"""
📝 <b>{problem.name}</b>

🔢 <b>Код:</b> {problem.full_code}
⭐ <b>Сложность:</b> {problem.rating if problem.rating else 'Не указана'}
✅ <b>Решений:</b> {problem.solved_count}
🏷️ <b>Теги:</b> {tags if tags else 'Нет тегов'}

🔗 <a href="{problem.url}">Открыть на Codeforces</a>
    """.strip()
    
    return info

# Команды бота
@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    welcome_text = """
🤖 <b>Добро пожаловать в Codeforces Bot!</b>

Я помогу вам найти интересные задачи для решения с Codeforces.

<b>Доступные команды:</b>
🎯 /problems - Подбор задач по сложности и темам
🔍 /search - Поиск задач по названию или номеру
🎲 /random - Случайная задача
🆘 /help - Помощь

Выберите действие ниже:
    """.strip()
    
    await message.answer(welcome_text, reply_markup=get_main_menu_keyboard(), parse_mode='HTML')

@dp.message(Command("help"))
async def cmd_help(message: types.Message):
    await show_help(message)

async def show_help(message: types.Message = None, callback: types.CallbackQuery = None):
    help_text = """
🆘 <b>Помощь по использованию бота</b>

<b>Основные функции:</b>

🎯 <b>Подбор задач</b> - Выбор задач по сложности и тематике. 
    • Выберите рейтинг сложности (800, 900, 1000 и т.д.)
    • Выберите одну или несколько тем
    • Получите подборку из 10 задач из разных контестов

🔍 <b>Поиск задач</b> - Поиск по названию задачи или её номеру через API Codeforces
    • Например: "1A", "231A", "Watermelon"

🎲 <b>Случайная задача</b> - Получить случайную задачу

<b>Навигация:</b>
• 🔙 Назад - вернуться на предыдущий шаг
• 🏠 Главная - вернуться в главное меню
• 🔄 Новый поиск - начать новый поиск
    """.strip()
    
    if message:
        await message.answer(help_text, parse_mode='HTML', reply_markup=get_navigation_keyboard())
    elif callback:
        await callback.message.edit_text(help_text, parse_mode='HTML', reply_markup=get_navigation_keyboard())

@dp.message(Command("problems"))
async def cmd_problems(message: types.Message, state: FSMContext):
    await show_problems_menu(message, state)

async def show_problems_menu(message: types.Message = None, state: FSMContext = None, callback: types.CallbackQuery = None):
    if state:
        await state.set_state(ProblemSearch.choosing_rating)
    
    text = "🎯 <b>Подбор задач</b>\n\nВыберите сложность задач (рейтинг):"
    
    if message:
        await message.answer(text, reply_markup=get_ratings_keyboard("main_menu"), parse_mode='HTML')
    elif callback:
        await callback.message.edit_text(text, reply_markup=get_ratings_keyboard("main_menu"), parse_mode='HTML')

@dp.message(Command("search"))
async def cmd_search(message: types.Message, state: FSMContext):
    await show_search_menu(message, state)

async def show_search_menu(message: types.Message = None, state: FSMContext = None, callback: types.CallbackQuery = None):
    if state:
        await state.set_state(ProblemSearch.searching)
    
    text = (
        "🔍 <b>Поиск задач через API Codeforces</b>\n\n"
        "Введите название задачи или её номер:\n"
        "• Например: <code>1A</code>\n"
        "• Или: <code>Watermelon</code>\n"
        "• Или: <code>231A</code>\n\n"
        "<i>Поиск выполняется через официальное API Codeforces</i>"
    )
    
    if message:
        await message.answer(text, parse_mode='HTML', reply_markup=get_navigation_keyboard("main_menu"))
    elif callback:
        await callback.message.edit_text(text, parse_mode='HTML', reply_markup=get_navigation_keyboard("main_menu"))

@dp.message(Command("random"))
async def cmd_random(message: types.Message):
    await show_random_problem(message)

async def show_random_problem(message: types.Message = None, callback: types.CallbackQuery = None):
    session = db.Session()
    try:
        problem = db.get_random_problem()
        if problem:
            refreshed_problem = session.query(Problem).options(joinedload(Problem.tags)).filter(
                Problem.id == problem.id
            ).first()
            
            text = format_problem_info(refreshed_problem)
            if message:
                await message.answer(text, parse_mode='HTML', disable_web_page_preview=False, 
                                   reply_markup=get_problems_navigation_keyboard())
            elif callback:
                await callback.message.edit_text(text, parse_mode='HTML', disable_web_page_preview=False,
                                               reply_markup=get_problems_navigation_keyboard())
        else:
            text = "❌ Не удалось найти случайную задачу"
            if message:
                await message.answer(text, reply_markup=get_navigation_keyboard())
            elif callback:
                await callback.message.edit_text(text, reply_markup=get_navigation_keyboard())
    finally:
        session.close()

# Обработчики callback-запросов
@dp.callback_query(F.data == "main_menu")
async def main_menu_callback(callback: types.CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.edit_text(
        "🤖 <b>Главное меню Codeforces Bot</b>\n\nВыберите действие:",
        reply_markup=get_main_menu_keyboard(),
        parse_mode='HTML'
    )
    await callback.answer()

@dp.callback_query(F.data == "problems_menu")
async def problems_menu_callback(callback: types.CallbackQuery, state: FSMContext):
    await show_problems_menu(state=state, callback=callback)

@dp.callback_query(F.data.startswith("rating_"))
async def rating_chosen_callback(callback: types.CallbackQuery, state: FSMContext):
    rating_data = callback.data.split("_")[1]
    
    if rating_data == "none":
        rating = None
    else:
        rating = int(rating_data)
    
    await state.update_data(rating=rating)
    await state.set_state(ProblemSearch.choosing_tags)
    
    rating_text = "любой" if rating is None else str(rating)
    await callback.message.edit_text(
        f"🎯 <b>Подбор задач</b>\n\n"
        f"⭐ Сложность: <b>{rating_text}</b>\n\n"
        f"Теперь выберите теги (можно несколько):",
        reply_markup=get_tags_keyboard(back_to="problems_menu"),
        parse_mode='HTML'
    )
    await callback.answer()

@dp.callback_query(F.data.startswith("tag_"))
async def tag_toggle_callback(callback: types.CallbackQuery, state: FSMContext):
    tag_name = callback.data[4:]
    
    state_data = await state.get_data()
    selected_tags = state_data.get('selected_tags', [])
    
    if tag_name in selected_tags:
        selected_tags.remove(tag_name)
    else:
        selected_tags.append(tag_name)
    
    await state.update_data(selected_tags=selected_tags)
    
    rating = state_data.get('rating')
    rating_text = "любой" if rating is None else str(rating)
    
    await callback.message.edit_text(
        f"🎯 <b>Подбор задач</b>\n\n"
        f"⭐ Сложность: <b>{rating_text}</b>\n"
        f"🏷️ Выбрано тегов: <b>{len(selected_tags)}</b>\n\n"
        f"Выберите теги (можно несколько):",
        reply_markup=get_tags_keyboard(selected_tags, back_to="problems_menu"),
        parse_mode='HTML'
    )
    await callback.answer()

@dp.callback_query(F.data == "tags_clear")
async def tags_clear_callback(callback: types.CallbackQuery, state: FSMContext):
    await state.update_data(selected_tags=[])
    
    state_data = await state.get_data()
    rating = state_data.get('rating')
    rating_text = "любой" if rating is None else str(rating)
    
    await callback.message.edit_text(
        f"🎯 <b>Подбор задач</b>\n\n"
        f"⭐ Сложность: <b>{rating_text}</b>\n"
        f"🏷️ Выбрано тегов: <b>0</b>\n\n"
        f"Теги очищены. Выберите теги:",
        reply_markup=get_tags_keyboard(back_to="problems_menu"),
        parse_mode='HTML'
    )
    await callback.answer()

@dp.callback_query(F.data == "tags_done")
async def tags_done_callback(callback: types.CallbackQuery, state: FSMContext):
    state_data = await state.get_data()
    rating = state_data.get('rating')
    selected_tags = state_data.get('selected_tags', [])
    
    # Показываем сообщение о загрузке
    await callback.message.edit_text(
        "⏳ <b>Ищем подходящие задачи...</b>",
        parse_mode='HTML'
    )
    
    # Получаем задачи по фильтрам
    problems = db.get_problems_by_filters(rating, selected_tags if selected_tags else None)
    
    if not problems:
        await callback.message.edit_text(
            "❌ <b>Задачи не найдены</b>\n\n"
            "Попробуйте изменить фильтры: выбрать другую сложность или другие теги.",
            reply_markup=InlineKeyboardBuilder()
                .button(text="🔄 Новый поиск", callback_data="problems_menu")
                .button(text="🎲 Случайная", callback_data="random_problem")
                .button(text="🏠 Главная", callback_data="main_menu")
                .adjust(2, 1)
                .as_markup(),
            parse_mode='HTML'
        )
    else:
        response_text = f"🎯 <b>Найдено задач: {len(problems)}</b>\n\n"
        
        for i, problem in enumerate(problems, 1):
            tags_list = [tag.name for tag in problem.tags]
            tags = ", ".join(tags_list[:3])
            
            response_text += (
                f"{i}. <b>{problem.full_code}</b> - {problem.name}\n"
                f"   ⭐ {problem.rating if problem.rating else '?'} | "
                f"✅ {problem.solved_count} | "
                f"🏷️ {tags}\n"
                f"   🔗 <a href='{problem.url}'>Открыть</a>\n\n"
            )
        
        # Добавляем информацию о фильтрах
        rating_text = "любой" if rating is None else str(rating)
        tags_text = ", ".join(selected_tags) if selected_tags else "все"
        
        response_text += f"<i>Фильтры: сложность {rating_text}, теги: {tags_text}</i>"
        
        await callback.message.edit_text(
            response_text,
            parse_mode='HTML',
            disable_web_page_preview=True,
            reply_markup=get_problems_navigation_keyboard()
        )
    
    await state.clear()
    await callback.answer()

@dp.callback_query(F.data == "search_menu")
async def search_menu_callback(callback: types.CallbackQuery, state: FSMContext):
    await show_search_menu(state=state, callback=callback)

@dp.callback_query(F.data == "random_problem")
async def random_problem_callback(callback: types.CallbackQuery):
    await show_random_problem(callback=callback)

@dp.callback_query(F.data == "help")
async def help_callback(callback: types.CallbackQuery):
    await show_help(callback=callback)

# Обработчик поисковых запросов через API
@dp.message(ProblemSearch.searching)
async def process_search(message: types.Message, state: FSMContext):
    search_query = message.text.strip()
    
    if len(search_query) < 2:
        await message.answer(
            "❌ Слишком короткий запрос. Введите хотя бы 2 символа.",
            reply_markup=get_navigation_keyboard("search_menu")
        )
        return
    
    # Показываем сообщение о загрузке
    loading_msg = await message.answer("⏳ <b>Ищем задачи через API Codeforces...</b>", parse_mode='HTML')
    
    # Ищем задачи через API
    async with CodeforcesAPI() as api:
        problems = await api.search_problems(search_query)
    
    if not problems:
        await loading_msg.edit_text(
            f"❌ По запросу '<code>{search_query}</code>' ничего не найдено.",
            parse_mode='HTML',
            reply_markup=get_search_navigation_keyboard()
        )
    else:
        response_text = f"🔍 <b>Результаты поиска по '{search_query}'</b>\n\n"
        
        for i, problem in enumerate(problems, 1):
            tags = ", ".join(problem.get('tags', [])[:2])
            contest_id = problem.get('contestId', '?')
            index = problem.get('index', '?')
            
            response_text += (
                f"{i}. <b>{contest_id}{index}</b> - {problem.get('name', 'Неизвестно')}\n"
                f"   ⭐ {problem.get('rating', '?')} | "
                f"✅ {problem.get('solvedCount', 0)} | "
                f"🏷️ {tags}\n"
                f"   🔗 <a href='https://codeforces.com/problemset/problem/{contest_id}/{index}'>Открыть</a>\n\n"
            )
        
        if len(problems) == 10:
            response_text += "<i>Показаны первые 10 результатов</i>"
        
        await loading_msg.edit_text(
            response_text,
            parse_mode='HTML',
            disable_web_page_preview=True,
            reply_markup=get_search_navigation_keyboard()
        )
    
    await state.clear()

# Обработчик любых сообщений (fallback)
@dp.message()
async def handle_other_messages(message: types.Message):
    await message.answer(
        "🤖 <b>Codeforces Bot</b>\n\n"
        "Используйте меню ниже для навигации:",
        reply_markup=get_main_menu_keyboard(),
        parse_mode='HTML'
    )

# Планировщик для обновления данных
async def scheduled_update():
    logger.info("Starting scheduled database update...")
    await db.update_problems()
    logger.info("Scheduled update completed")

async def main():
    # Инициализация базы данных
    db.init_db()
    logger.info("Database initialized")
    
    # Первоначальное обновление данных
    await db.update_problems()
    
    # Настройка планировщика
    scheduler = AsyncIOScheduler()
    scheduler.add_job(
        scheduled_update,
        trigger=IntervalTrigger(hours=UPDATE_INTERVAL_HOURS),
        id='update_problems'
    )
    scheduler.start()
    
    logger.info("Bot started successfully")
    
    # Запуск бота
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())