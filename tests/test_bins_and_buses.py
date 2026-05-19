import pytest
from app import app as flask_app


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
