import os
import json
from celery import Celery
from celery.schedules import crontab
from app import get_weather_data


# Use in-memory broker and backend for Celery (not for production, but avoids Redis)
celery = Celery("matrix", broker="memory://", backend="cache+memory://")


@celery.task
def fetch_and_cache_weather():
    current_weather, forecast_days = get_weather_data()
    cache = {"current_weather": current_weather, "forecast_days": forecast_days}
    cache_path = os.path.join(os.path.dirname(__file__), "weather_cache.json")
    with open(cache_path, "w") as f:
        json.dump(cache, f)
    return True


# Optional: schedule periodic weather fetch every 15 minutes
celery.conf.beat_schedule = {
    "fetch-weather-every-15-minutes": {
        "task": "celery_worker.fetch_and_cache_weather",
        "schedule": crontab(minute="*/15"),
    },
}

if __name__ == "__main__":
    celery.start()
