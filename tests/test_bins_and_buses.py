import pytest
from unittest.mock import patch
from app import app as flask_app, get_this_week_bins


@pytest.fixture
def client():
    flask_app.testing = True
    with flask_app.test_client() as c:
        yield c


def test_bin_collection_index_renders(client):
    response = client.get('/')
    assert response.status_code == 200
    assert 'bin' in response.get_data(as_text=True).lower()


def test_bins_fragment_returns_200(client):
    response = client.get('/bins-fragment')
    assert response.status_code == 200


def test_bins_fragment_contains_bin_collection(client):
    response = client.get('/bins-fragment')
    html = response.get_data(as_text=True)
    assert 'bin-collection' in html


@patch('app._get_bins_from_ics', return_value=None)
def test_get_this_week_bins_returns_safe_default_on_ics_failure(mock_ics):
    result = get_this_week_bins()
    assert result is not None
    assert 'bins' in result
    assert 'collection_day' in result
    assert isinstance(result['bins'], list)


@patch('app.get_this_week_bins', return_value={'bins': [], 'collection_day': 'Unknown'})
def test_bins_fragment_renders_when_ics_fails(mock_bins, client):
    response = client.get('/bins-fragment')
    assert response.status_code == 200
    assert 'bin-collection' in response.get_data(as_text=True)
