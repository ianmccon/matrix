import unittest
from app import app

class AppTestCase(unittest.TestCase):
    def setUp(self):
        self.app = app.test_client()
        self.app.testing = True

    def test_events_fragment_renders(self):
        response = self.app.get('/events-fragment')
        self.assertEqual(response.status_code, 200)
        html = response.get_data(as_text=True)
        self.assertIn('events-list', html)  # Check for the events list container

    def test_news_fragment(self):
        response = self.app.get('/news-fragment')
        self.assertEqual(response.status_code, 200)
        html = response.get_data(as_text=True)
        self.assertIn('news', html.lower())

    def test_weather_fragment(self):
        response = self.app.get('/current-weather-fragment')
        self.assertEqual(response.status_code, 200)
        html = response.get_data(as_text=True)
        self.assertIn('weather', html.lower())

if __name__ == '__main__':
    unittest.main()
