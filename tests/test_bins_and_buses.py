import unittest
from app import app

class BinsAndBusesTestCase(unittest.TestCase):
    def setUp(self):
        self.app = app.test_client()
        self.app.testing = True

    def test_buses_fragment(self):
        response = self.app.get('/buses-fragment')
        self.assertEqual(response.status_code, 200)
        html = response.get_data(as_text=True)
        self.assertIn('bus', html.lower())
        # Optionally check for a service or destination string

    def test_bin_collection(self):
        # Bin info is rendered in the main index page
        response = self.app.get('/')
        self.assertEqual(response.status_code, 200)
        html = response.get_data(as_text=True)
        self.assertIn('bin', html.lower())
        # Optionally check for a bin name from config

if __name__ == '__main__':
    unittest.main()
