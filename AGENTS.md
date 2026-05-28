# Agent Instructions

## Testing preferences

- Write all Python tests as `pytest` style functions, not unittest classes
- Use descriptive function names starting with `test_`
- Prefer fixtures over setup/teardown methods
- Use assert statements directly, not self.assertEqual

**Correct style:**
```python
import pytest
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
```

**Incorrect style (do not use):**
```python
import unittest

class MyTests(unittest.TestCase):
    def setUp(self):
        ...
    def test_something(self):
        self.assertEqual(...)
```

## Testing approach

- Never create throwaway test scripts or ad hoc verification files
- If you need to test functionality, write a proper test in the test suite
- All tests go in the `tests/` directory following the project structure
- Tests should be runnable with the rest of the suite
- Even for quick verification, write it as a real test that provides ongoing value

## Project structure

- Flask/Jinja2 dashboard app: `app.py` (main backend), `templates/` (Jinja2), `static/` (CSS/JS)
- Fragment endpoints return partial HTML for AJAX section refreshes (e.g. `/events-fragment`, `/news-fragment`)
- Config lives in `config_matrix.json` (gitignored — copy from `config_matrix.json.sample`)
- Python virtual environment: `venv/` — always activate before running or testing
- Run tests: `python run_tests.py` or `pytest tests/` from project root

## Running the app

- Dev: `./run.sh`
- Production: managed by `matrix.service` (gunicorn) + `kiosk.service` (Chromium fullscreen)
- After code changes, restart both: `sudo systemctl restart matrix.service && sudo systemctl restart kiosk.service`

## Code conventions

- Timezone-aware datetime handling throughout — use `now_local()` helper (returns `datetime.now(APP_TIMEZONE)`), never `datetime.utcnow()`
- `APP_TIMEZONE` is a `ZoneInfo` object loaded from config key `TIMEZONE` (default `Europe/London`)
- API keys and secrets belong in `config_matrix.json`, not hardcoded in `app.py`
- The `icon_to_code` mapping (PirateWeather icon → Met Office weather code) is a module-level constant, not defined inside a function

## Existing tests are in the wrong style

The files `tests/test_app.py`, `tests/test_bins_and_buses.py`, and `tests/test_events_fragment.py` currently use `unittest.TestCase` classes. When modifying or adding to these files, convert the relevant tests to pytest style. Do not add new unittest-style tests.