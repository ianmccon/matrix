import os
from celery import Celery
import json
from app import get_weather_data

CELERY_BROKER_URL = os.environ.get('CELERY_BROKER_URL', 'redis://localhost:6379/0')
CELERY_RESULT_BACKEND = os.environ.get('CELERY_RESULT_BACKEND', 'redis://localhost:6379/0')

celery = Celery('matrix', broker=CELERY_BROKER_URL, backend=CELERY_RESULT_BACKEND)

@celery.task
def fetch_and_cache_weather():
    current_weather, forecast_days = get_weather_data()
    cache = {
        'current_weather': current_weather,
        'forecast_days': forecast_days
    }
    cache_path = os.path.join(os.path.dirname(__file__), 'weather_cache.json')
    with open(cache_path, 'w') as f:
        json.dump(cache, f)
    return True

# Optional: schedule periodic weather fetch every 15 minutes
from celery.schedules import crontab
celery.conf.beat_schedule = {
    'fetch-weather-every-15-minutes': {
        'task': 'celery_worker.fetch_and_cache_weather',
        'schedule': crontab(minute='*/15'),
    },
}

if __name__ == '__main__':
    celery.start()
