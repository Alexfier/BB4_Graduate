import pytest
from unittest.mock import MagicMock, patch
from bot import search_problems_by_tag


@pytest.fixture
def mocker_fixture(mocker):
    return mocker

def test_search_problems_by_tag(mocker):
    mock_session = MagicMock()
    mock_session.query.return_value.filter.return_value.all.return_value = []
    mocker.patch('parser.Session', return_value=mock_session)

    results = search_problems_by_tag('math')
    assert results == []
