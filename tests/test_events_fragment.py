import unittest
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


if __name__ == '__main__':
    unittest.main()
