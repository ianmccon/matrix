import unittest
import datetime
from unittest.mock import patch
from app import app


class EventsFragmentTestCase(unittest.TestCase):
    def setUp(self):
        self.app = app.test_client()
        self.app.testing = True

    def test_events_fragment_returns_list(self):
        resp = self.app.get('/events-fragment')
        self.assertEqual(resp.status_code, 200)
        html = resp.get_data(as_text=True)
        # The fragment should contain the events list container
        self.assertIn('<ul class="events-list"', html)

    @patch('app.parse_ics_events_from_url')
    @patch('app.FASTMAIL_CALENDARS', new=[{'url': 'dummy', 'name': 'Events', 'color': '#fff'}])
    def test_events_fragment_excludes_past_event_today(self, mock_parse_events):
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

        resp = self.app.get('/events-fragment')
        self.assertEqual(resp.status_code, 200)
        html = resp.get_data(as_text=True)
        self.assertNotIn('Past Today', html)
        self.assertIn('Future Today', html)


if __name__ == '__main__':
    unittest.main()
