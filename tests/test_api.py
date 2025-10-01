import pytest
from parser import get_current_time, generate_sha512_hash, get_api_signature, make_api_request
from dotenv import load_dotenv
import os, requests


# Загрузка переменных окружения
load_dotenv(encoding="utf-8")

API_KEY = os.getenv("apiKey")
SECRET = os.getenv("secret")


def test_get_current_time():
    current_time = get_current_time()
    assert isinstance(current_time, int), "Ожидается, что время будет целым числом"
    assert current_time > 0, "Ожидается, что время будет больше 0"


def test_generate_sha512_hash():
    data = "test_data"
    hash_result = generate_sha512_hash(data)
    assert isinstance(hash_result, str), "Ожидается, что хэш будет строкой"
    assert len(hash_result) == 128, "Ожидается, что длина SHA-512 хэша будет 128 символов"


def test_get_api_signature():
    methodName = 'problemset.problems'
    params = {"param1": "value1", "param2": "value2"}
    signature = get_api_signature(API_KEY, SECRET, methodName, params)
    assert isinstance(signature, str), "Ожидается, что подпись будет строкой"
    assert len(signature) == 128 + 6, "Ожидается, что длина подписи будет 134 символа"


@pytest.fixture
def api_key():
    return 'your_api_key'

@pytest.fixture
def secret():
    return 'your_secret'

@pytest.fixture
def method_name():
    return 'problemset.problems'

@pytest.fixture
def params():
    return {
        'tags': 'implementation',
        'minRating': 800,
        'maxRating': 800
    }


def test_make_api_request(api_key, secret, method_name, params):
    response = make_api_request(api_key, secret, method_name, params)
    assert response is not None
    assert isinstance(response, dict)
    assert 'status' in response


