import pytest
from unittest.mock import patch
from app import app as flask_app


@pytest.fixture
def client():
    flask_app.testing = True
    with flask_app.test_client() as c:
        yield c


def test_events_fragment_renders(client):
    response = client.get('/events-fragment')
    assert response.status_code == 200
    assert 'events-list' in response.get_data(as_text=True)


@patch('app.get_news_items', return_value=[])
def test_news_fragment_returns_200(mock_news, client):
    response = client.get('/news-fragment')
    assert response.status_code == 200


@patch('app.get_news_items', return_value=[
    {'title': 'Test', 'link': 'http://example.com', 'summary': 'Summary', 'published': None}
])
def test_news_fragment_contains_news_item(mock_news, client):
    response = client.get('/news-fragment')
    assert response.status_code == 200
    assert 'Test' in response.get_data(as_text=True)


_EMPTY_WEATHER = (None, None, None, None, 'Home')


@patch('app.get_openmeteo_weather_data', return_value=_EMPTY_WEATHER)
def test_current_weather_fragment_returns_200(mock_weather, client):
    response = client.get('/current-weather-fragment')
    assert response.status_code == 200


@patch('app.get_openmeteo_weather_data', return_value=(None, None, None, None, 'Rhodes, Greece'))
def test_current_weather_fragment_passes_location_param(mock_weather, client):
    response = client.get('/current-weather-fragment?location=east_med')
    assert response.status_code == 200
    mock_weather.assert_called_once_with('east_med')


@patch('app.get_openmeteo_weather_data', return_value=(None, [], '', '', 'Home'))
def test_forecast_weather_fragment_returns_200(mock_weather, client):
    response = client.get('/forecast-weather-fragment')
    assert response.status_code == 200


@patch('app.get_openmeteo_weather_data', return_value=(None, [], '', '', 'Rhodes, Greece'))
def test_forecast_weather_fragment_passes_location_param(mock_weather, client):
    response = client.get('/forecast-weather-fragment?location=east_med')
    assert response.status_code == 200
    mock_weather.assert_called_once_with('east_med')


@patch('app.get_todoist_tasks', return_value=[])
def test_todoist_fragment_returns_200(mock_tasks, client):
    response = client.get('/todoist-fragment')
    assert response.status_code == 200


@patch('app.get_todoist_tasks', return_value=[
    {'id': '1', 'name': 'Test Project', 'color': '#fff',
     'tasks': [{'content': 'Buy milk', 'due': '', 'id': 't1'}]}
])
def test_todoist_fragment_renders_task(mock_tasks, client):
    response = client.get('/todoist-fragment')
    assert response.status_code == 200
    assert 'Buy milk' in response.get_data(as_text=True)
