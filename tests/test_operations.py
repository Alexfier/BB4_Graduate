import pytest
from unittest.mock import MagicMock, patch
from parser import get_problems_and_statistics, get_last_index_from_db, update_last_index_in_db, insert_problems_to_db, \
    search_problems_by_tag, parser


@pytest.fixture
def api_response():
    return {
        'status': 'OK',
        'result': {
            'problems': [
                {'contestId': 1111, 'index': 'A', 'name': 'Problem 1', 'rating': 1000, 'tags': ['math']},
                {'contestId': 1112, 'index': 'B', 'name': 'Problem 2', 'rating': 1000, 'tags': ['math']}
            ],
            'problemStatistics': [
                {'solvedCount': 1000},
                {'solvedCount': 2000}
            ]
        }
    }


def test_get_problems_and_statistics(api_response, mocker):
    mocker.patch('parser.make_api_request', return_value=api_response)
    problems = get_problems_and_statistics('fake_key', 'fake_secret', 'math', 1000, 10, '0')
    assert len(problems) == 2
    assert problems[0]['name'] == 'Problem 1'
    assert problems[1]['name'] == 'Problem 2'


def test_get_last_index_from_db(mocker):
    mock_session = MagicMock()
    mock_session.query.return_value.order_by.return_value.first.return_value = None
    mocker.patch('parser.Session', return_value=mock_session)

    last_contest_id, last_index = get_last_index_from_db()
    assert last_index == '0'


def test_update_last_index_in_db(mocker):
    mock_session = MagicMock()
    mocker.patch('parser.Session', return_value=mock_session)

    update_last_index_in_db(1111, 'A')
    mock_session.add.assert_called_once()
    mock_session.commit.assert_called_once()


def test_insert_problems_to_db(mocker):
    problems = [
        {'contestId': 1111, 'index': 'A', 'name': 'Problem 1', 'rating': 1000, 'solvedCount': 1000, 'tags': 'math',
         'link': 'link1'},
        {'contestId': 1112, 'index': 'B', 'name': 'Problem 2', 'rating': 1000, 'solvedCount': 2000, 'tags': 'math',
         'link': 'link2'}
    ]
    mock_session = MagicMock()
    mock_session.query.return_value.filter_by.return_value.first.side_effect = [None, None]
    mocker.patch('parser.Session', return_value=mock_session)

    all_present = insert_problems_to_db(problems)
    assert not all_present
    assert mock_session.add.call_count == 2
    mock_session.commit.assert_called_once()


def test_search_problems_by_tag(mocker):
    mock_session = MagicMock()
    mock_session.query.return_value.filter.return_value.all.return_value = []
    mocker.patch('parser.Session', return_value=mock_session)

    results = search_problems_by_tag('math')
    assert results == []


# def test_parser(mocker, api_response):
#     mocker.patch('parser.get_last_index_from_db', return_value=(None, '0'))
#     mocker.patch('parser.get_problems_and_statistics', return_value=[
#         {'contestId': 1111, 'index': 'A', 'name': 'Problem 1', 'rating': 1000, 'solvedCount': 1000, 'tags': 'math',
#          'link': 'link1'}
#     ])
#     mocker.patch('parser.insert_problems_to_db', return_value=False)
#     mocker.patch('parser.update_last_index_in_db')
#     mocker.patch('time.sleep', return_value=None)  # Мокаем time.sleep
#
#     problems = parser('fake_key', 'fake_secret', 'math', 1000)
#     assert len(problems) == 1
#     assert problems[0]['name'] == 'Problem 1'
