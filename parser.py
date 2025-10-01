import os
import requests
import time
import hashlib
import random
import urllib.parse
import logging
from dotenv import load_dotenv

from database.config import Session, Base, engine
from database.models import LastFetched, Problem

# Настройка логирования
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger()

load_dotenv(encoding="utf-8")

apiKey = os.getenv("apiKey")
secret = os.getenv("secret")

# Создание базы данных и таблиц
Base.metadata.create_all(engine)


# Получить текущее Unix время
def get_current_time():
    return int(time.time())


# Генерация SHA-512 хэша
def generate_sha512_hash(data):
    return hashlib.sha512(data.encode('utf-8')).hexdigest()


# Получить подпись API
def get_api_signature(apiKey, secret, methodName, params):
    rand = ''.join(random.choices('abcdefghijklmnopqrstuvwxyz0123456789', k=6))
    params['apiKey'] = apiKey
    params['time'] = get_current_time()

    sorted_params = sorted(params.items())
    param_str = '&'.join([f"{k}={v}" for k, v in sorted_params])
    hash_input = f"{rand}/{methodName}?{param_str}#{secret}"
    hash_output = generate_sha512_hash(hash_input)

    return f"{rand}{hash_output}"


# Выполнить запрос к API
def make_api_request(apiKey, secret, methodName, params):
    logger.info("Подключение к API Codeforces")
    base_url = 'https://codeforces.com/api/'
    apiSig = get_api_signature(apiKey, secret, methodName, params)
    params['apiSig'] = apiSig
    response = requests.get(base_url + methodName, params=params)
    logger.info("Выполнен запрос к API")
    return response.json()


# Получить задачи и статистику по тегам и сложности из makeapirequest
def get_problems_and_statistics(apiKey, secret, tags, difficulty, count, last_index):
    params = {
        'tags': urllib.parse.quote(tags),  # URL кодирование тегов
        'problemsetName': '',
        'minRating': difficulty,
        'maxRating': difficulty
    }
    methodName = 'problemset.problems'
    response = make_api_request(apiKey, secret, methodName, params)

    if response['status'] != 'OK':
        raise Exception(f"Ошибка от Codeforces API: {response['comment']}")

    problems = []
    start_adding = False if last_index != '0' else True
    for problem, stat in zip(response['result']['problems'], response['result']['problemStatistics']):
        if problem['index'] == last_index:
            start_adding = True
            continue
        if start_adding and 'contestId' in problem and 'rating' in problem and problem['rating'] == difficulty and set(
                tags.split(';')).issubset(set(problem['tags'])):
            problems.append({
                'contestId': problem['contestId'],
                'index': problem['index'],
                'name': problem['name'],
                'rating': problem['rating'],
                'solvedCount': stat['solvedCount'],
                'tags': tags,  # Добавить теги к словарю задачи
                'link': f"https://codeforces.com/problemset/problem/{problem['contestId']}/{problem['index']}"
            })
            if len(problems) >= count:
                break

    return problems


# Получить последний индекс из базы данных
def get_last_index_from_db():
    session = Session()
    last_fetched = session.query(LastFetched).order_by(LastFetched.id.desc()).first()
    if last_fetched:
        last_contest_id, last_index = last_fetched.last_contest_id, last_fetched.last_index
    else:
        last_contest_id, last_index = None, '0'
    session.close()
    return last_contest_id, last_index


# Обновить последний индекс в базе данных
def update_last_index_in_db(contest_id, index):
    session = Session()
    new_last_fetched = LastFetched(last_contest_id=contest_id, last_index=index)
    session.add(new_last_fetched)
    session.commit()
    session.close()


# Вставить задачи в базу данных, если они еще не существуют
def insert_problems_to_db(problems):
    session = Session()
    all_present = True

    for problem in problems:
        existing_problem = session.query(Problem).filter_by(contest_id=problem['contestId'],
                                                            index=problem['index']).first()
        if existing_problem:
            continue

        all_present = False
        new_problem = Problem(
            contest_id=problem['contestId'],
            index=problem['index'],
            name=problem['name'],
            rating=problem['rating'],
            solved_count=problem['solvedCount'],
            tags=problem['tags'],
            link=problem['link']
        )
        session.add(new_problem)

    session.commit()
    session.close()

    return all_present


def search_problems_by_tag(tag):
    session = Session()
    try:
        results = session.query(Problem).filter(Problem.tags.contains(tag)).all()
        return results
    finally:
        session.close()


def parser(apiKey, secret, tags, difficulty):
    try:
        last_contest_id, last_index = get_last_index_from_db()
        count = 10
        all_problems = []  # Добавляем список для всех задач

        while True:
            logger.info("Начало получения задач")
            problems = get_problems_and_statistics(apiKey, secret, tags, difficulty, count, last_index)
            if not problems:
                logger.info("Больше задач по указанным тегам и сложности не найдено.")
                break

            logger.info("Выполняется проверка и вставка данных в БД")
            all_present = insert_problems_to_db(problems)

            all_problems.extend(problems)  # Добавляем задачи в общий список

            if all_present:
                logger.info("Все данные из ответа API уже присутствуют в базе данных. Остановка парсинга.")
                break
            else:
                last_problem = problems[-1]
                update_last_index_in_db(last_problem['contestId'], last_problem['index'])

            count += 10
            last_index = last_problem['index']
            time.sleep(10)  # Избежать превышения лимита запросов к API

    except Exception as e:
        logger.error(f"Произошла ошибка: {e}")

    logger.info("Парсинг завершен")
    return all_problems  # Возвращаем список всех задач


# # Использовалось для начальной отладки
# def scheduled_task():
#     parser(apiKey, secret, tags, difficulty)
#
# # Запланировать задачу на каждые 10 секунд
# schedule.every(10).seconds.do(scheduled_task)
#
# # Постоянное выполнение скрипта для поддержания расписания
# while True:
#     schedule.run_pending()
#     time.sleep(5)
