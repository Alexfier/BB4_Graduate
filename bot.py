import logging
import telebot
from telebot import types
from dotenv import load_dotenv
import os
import schedule
import time
from parser import parser
from parser import search_problems_by_tag  # Импорт функции для поиска по тегу

# Настройка логирования
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')
logger = logging.getLogger()

load_dotenv(encoding="utf-8")

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
API_KEY = os.getenv("apiKey")
SECRET = os.getenv("secret")

# Создание бота
bot = telebot.TeleBot(TELEGRAM_TOKEN)

tags = None
difficulty = None


@bot.message_handler(commands=['start'])
def start(message):
    global tags, difficulty
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    item1 = types.KeyboardButton("Начать парсинг задач")
    item2 = types.KeyboardButton("Поиск в базе по тегу")
    markup.add(item1, item2)
    bot.send_message(message.chat.id,
                     'Привет! Я бот для парсинга задач с Codeforces.\n'
                     'Выберите меню:',
                     reply_markup=markup)
    bot.register_next_step_handler(message, handle_option)


def handle_option(message):
    if message.text == "Начать парсинг задач":
        bot.send_message(message.chat.id,
                         'Введи тему для парсинга, например "math" или "graphs":')
        bot.register_next_step_handler(message, tags_handler)
    elif message.text == "Поиск в базе по тегу":
        bot.send_message(message.chat.id,
                         'Введите тему для поиска, например "math" или "graphs":')
        bot.register_next_step_handler(message, search_by_tag)


def tags_handler(message):
    global tags
    tags = message.text
    bot.send_message(message.chat.id,
                     'Введите сложность задач (целое число) например: 800, 1000, 1500:')
    bot.register_next_step_handler(message, difficulty_handler)


def difficulty_handler(message):
    global difficulty
    try:
        difficulty = int(message.text)
        bot.send_message(message.chat.id,
                         f'Начинаю парсинг задач с тегами: {tags} и сложностью: {difficulty}. \n Пожалуйста дождитесь '
                         f'окончания парсинга!'
                         )

        # Запуск парсера
        try:
            problems = parser(API_KEY, SECRET, tags, difficulty)  # Получаем результаты парсинга
            num_problems = len(problems)
            if problems:
                count = 0
                for problem in problems:
                    if count >= 10:
                        break
                    response = (f"Name: {problem['name']}\n"
                                f"Rating: {problem['rating']}\n"
                                f"Tags: {problem['tags']}\n"
                                f"Link: {problem['link']}\n")
                    bot.send_message(message.chat.id, response)
                    time.sleep(5)
                    count += 1
            else:
                bot.send_message(message.chat.id, 'По указанным параметрам задачи не найдены.')

            bot.send_message(message.chat.id, 'Парсинг завершен. Найдено задач: ' + str(num_problems))
        except Exception as e:
            bot.send_message(message.chat.id, f'Произошла ошибка при парсинге: {e}')

    except ValueError:
        bot.send_message(message.chat.id, 'Пожалуйста, введите корректное число для сложности.')


def search_by_tag(message):
    tag = message.text
    problems = search_problems_by_tag(tag)  # Вызов функции из orm_query.py
    if not problems:
        bot.send_message(message.chat.id, 'Задачи с данным тегом не найдены.')
    else:
        for problem in problems:
            response = (f"Name: {problem.name}\n"
                        f"Rating: {problem.rating}\n"
                        f"Tags: {problem.tags}\n"
                        f"Link: {problem.link}\n")
            bot.send_message(message.chat.id, response)
            time.sleep(5)


if __name__ == '__main__':
    while True:
        bot.polling(none_stop=True)
