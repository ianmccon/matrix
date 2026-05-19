import pytest
import datetime
from unittest.mock import patch
from app import app as flask_app


@pytest.fixture
def client():
    flask_app.testing = True
    with flask_app.test_client() as c:
        yield c


def test_events_fragment_returns_list(client):
    resp = client.get('/events-fragment')
    assert resp.status_code == 200
    assert '<ul class="events-list"' in resp.get_data(as_text=True)


@patch('app.parse_ics_events_from_url')
@patch('app.FASTMAIL_CALENDARS', new=[{'url': 'dummy', 'name': 'Events', 'color': '#fff'}])
def test_events_fragment_excludes_past_event_today(mock_parse_events, client):
    now = datetime.datetime.now()
    mock_parse_events.return_value = [
        {
            'dt': now - datetime.timedelta(hours=1),
            'summary': 'Past Today',
            'calendar': 'Events'
        },
        {
            'dt': now + datetime.timedelta(hours=1),
            'summary': 'Future Today',
            'calendar': 'Events'
        }
    ]

    resp = client.get('/events-fragment')
    assert resp.status_code == 200
    html = resp.get_data(as_text=True)
    assert 'Past Today' not in html
    assert 'Future Today' in html
