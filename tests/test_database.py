import pytest
from sqlalchemy import inspect, create_engine, Integer, String
from sqlalchemy.orm import sessionmaker
from database.config import Base, engine  # Подставьте правильный импорт конфигурации базы данных
from database.models import Problem  # Подставьте правильный импорт модели данных Problem
from parser import search_problems_by_tag

# Создание временной базы данных для тестов
TEST_DATABASE_URL = "sqlite:///:memory:"
engine = create_engine(TEST_DATABASE_URL)
Session = sessionmaker(bind=engine)
Base.metadata.create_all(engine)  # Создание таблиц


@pytest.fixture(autouse=True, scope='function')
def setup_database():
    Base.metadata.create_all(engine)
    session = Session()
    yield session
    session.close()
    Base.metadata.drop_all(engine)


def test_table_exists(setup_database):
    inspector = inspect(engine)
    assert 'problems' in inspector.get_table_names()


def test_fields_exist():
    table_columns = Problem.__table__.columns.keys()
    expected_columns = ['id', 'contest_id', 'index', 'name', 'rating', 'solved_count', 'tags', 'link']
    assert all(column in table_columns for column in expected_columns)


def test_field_types():
    table_columns = Problem.__table__.columns
    expected_types = {
        'id': Integer,
        'contest_id': Integer,
        'index': String,
        'name': String,
        'rating': Integer,
        'solved_count': Integer,
        'tags': String,
        'link': String
    }

    for column_name, expected_type in expected_types.items():
        assert isinstance(table_columns[column_name].type, expected_type)


def test_search_problems_by_tag(setup_database, mocker):
    # Создаем тестовые данные
    session = setup_database
    test_problem = Problem(
        contest_id=1234,
        index='A',
        name='Test Problem',
        rating=1200,
        solved_count=500,
        tags='math',
        link='https://codeforces.com/problemset/problem/1234/A'
    )
    session.add(test_problem)
    session.commit()

    # Мокаем функцию sessionmaker, чтобы возвращать нашу сессию
    mocker.patch('parser.Session', return_value=session)

    # Вызываем функцию для поиска по тегу
    results = search_problems_by_tag('math')

    # Проверяем результаты
    assert len(results) == 1
    assert results[0].name == 'Test Problem'
    assert results[0].tags == 'math'
