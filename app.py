# --- Fragment endpoints for AJAX section refreshes ---

import json
import feedparser
from flask import Flask, render_template, request, jsonify
import os




from diskcache import Cache
# Diskcache-backed persistent cache for weather data
_weather_cache = Cache('./weather_cache_disk')
def get_cached_weather(key, fetch_func, cache_seconds=3600):
    entry = _weather_cache.get(key)
    if entry:
        data, ts = entry
        age = (datetime.datetime.now(datetime.timezone.utc) - ts).total_seconds()
        if age < cache_seconds:
            print(f"Weather cache hit for key: {key}")
            return data
        else:
            print(f"Weather cache expired for key: {key}")
    else:
        print(f"Weather cache miss for key: {key}")
    data = fetch_func()
    try:
        _weather_cache.set(key, (data, datetime.datetime.now(datetime.timezone.utc)), expire=cache_seconds)
        print(f"Weather cache set for key: {key}")
    except Exception as e:
        print(f"Weather cache write error for key: {key}: {e}")
    return data
from concurrent.futures import ThreadPoolExecutor
from icalendar import Calendar
import datetime
import os
import requests
from zoneinfo import ZoneInfo

# --- CONFIG ---
CONFIG_PATH = os.path.join(os.path.dirname(__file__), 'config_matrix.json')
with open(CONFIG_PATH) as f:
    config = json.load(f)

WEATHER_LOCATION = config["WEATHER_LOCATION"]
WEATHER_LATITUDE = config["WEATHER_LATITUDE"]
WEATHER_LONGITUDE = config["WEATHER_LONGITUDE"]
EAST_MED_WEATHER_LOCATION = config.get("EAST_MED_WEATHER_LOCATION", "Rhodes, Greece")
EAST_MED_WEATHER_LATITUDE = config.get("EAST_MED_WEATHER_LATITUDE", "36.4341")
EAST_MED_WEATHER_LONGITUDE = config.get("EAST_MED_WEATHER_LONGITUDE", "28.2176")
DUBROVNIK_WEATHER_LOCATION = config.get("DUBROVNIK_WEATHER_LOCATION", "Dubrovnik, Croatia")
DUBROVNIK_WEATHER_LATITUDE = config.get("DUBROVNIK_WEATHER_LATITUDE", "42.6507")
DUBROVNIK_WEATHER_LONGITUDE = config.get("DUBROVNIK_WEATHER_LONGITUDE", "18.0944")
FASTMAIL_CALENDARS = config["FASTMAIL_CALENDARS"]
WEATHER_MAP = config["WEATHER_MAP"]
PIRATEWEATHER_API_KEY = config.get("PIRATEWEATHER_API_KEY", "")
TODOIST_API_KEY = config.get("TODOIST_API_KEY", "")
BIN_ICS_URL = config.get("BIN_ICS_URL", "")
APP_TIMEZONE = ZoneInfo(config.get("TIMEZONE", "Europe/London"))

# Cruise itinerary port coordinates (lat/lon None = at sea, no temperature)
CRUISE_ITINERARY = [
    {'date': '2026-05-28', 'lat': 42.6507, 'lon': 18.0944},  # Dubrovnik
    {'date': '2026-05-29', 'lat': None,    'lon': None},      # At Sea
    {'date': '2026-05-30', 'lat': 35.8997, 'lon': 14.5147},  # Valletta
    {'date': '2026-05-31', 'lat': 38.1938, 'lon': 15.5540},  # Messina
    {'date': '2026-06-01', 'lat': 38.1742, 'lon': 20.4892},  # Argostoli
    {'date': '2026-06-02', 'lat': 39.6243, 'lon': 19.9217},  # Corfu
    {'date': '2026-06-03', 'lat': 42.4247, 'lon': 18.7712},  # Kotor
    {'date': '2026-06-04', 'lat': 42.6507, 'lon': 18.0944},  # Dubrovnik
]

# PirateWeather icon → Met Office significant weather code
ICON_TO_CODE = {
    'clear-day': '1',
    'clear-night': '0',
    'partly-cloudy-day': '3',
    'partly-cloudy-night': '2',
    'cloudy': '7',
    'rain': '12',
    'sleet': '18',
    'snow': '24',
    'wind': '8',
    'fog': '6',
    'hail': '20',
    'thunderstorm': '30',
}

app = Flask(__name__)

# Helper function to convert wind bearing (degrees) to compass direction
def bearing_to_direction(bearing):
    """Convert wind bearing in degrees to compass direction (N, NE, E, etc.)"""
    if bearing is None:
        return ""
    bearing = float(bearing)
    directions = ['N', 'NNE', 'NE', 'ENE', 'E', 'ESE', 'SE', 'SSE', 
                  'S', 'SSW', 'SW', 'WSW', 'W', 'WNW', 'NW', 'NNW']
    index = round(bearing / 22.5) % 16
    return directions[index]

# Register the filter for use in templates
app.jinja_env.filters['bearing_to_direction'] = bearing_to_direction


def now_local():
    return datetime.datetime.now(APP_TIMEZONE)


def as_local_datetime(value):
    if isinstance(value, datetime.datetime):
        if value.tzinfo is None:
            return value.replace(tzinfo=APP_TIMEZONE)
        return value.astimezone(APP_TIMEZONE)
    if isinstance(value, datetime.date):
        return datetime.datetime.combine(value, datetime.time.min, tzinfo=APP_TIMEZONE)
    return None


def format_event_display(dt_value, now_dt):
    tomorrow_date = (now_dt + datetime.timedelta(days=1)).date()

    def day_suffix(day):
        if day in (1, 21, 31):
            return 'st'
        if day in (2, 22):
            return 'nd'
        if day in (3, 23):
            return 'rd'
        return 'th'

    if isinstance(dt_value, datetime.datetime):
        adt = as_local_datetime(dt_value)
        try:
            hour = adt.strftime('%-I')
        except Exception:
            hour = adt.strftime('%I').lstrip('0')
        minute = adt.strftime('%M')
        ampm = adt.strftime('%p')
        if minute == '00':
            time_compact = f"{hour}{ampm}"
        else:
            time_compact = f"{hour}:{minute}{ampm}"

        if adt.date() == now_dt.date():
            delta = adt - now_dt
            secs = int(delta.total_seconds())
            if secs <= 0:
                time_text = "0h 0m"
            else:
                hours = secs // 3600
                minutes = (secs % 3600) // 60
                time_text = f"{hours}h {minutes}m"
            return f"Today in {time_text} - {time_compact}"
        if adt.date() == tomorrow_date:
            return f"Tomorrow - {time_compact}"
        return f"{adt.strftime('%b')} {adt.day}{day_suffix(adt.day)} - {time_compact}"

    if isinstance(dt_value, datetime.date):
        if dt_value == now_dt.date():
            return 'Today'
        if dt_value == tomorrow_date:
            return 'Tomorrow'
        return f"{dt_value.strftime('%b')} {dt_value.day}{day_suffix(dt_value.day)}"

    return ''


def get_weather_location(location_key='home'):
    key = (location_key or 'home').strip().lower()
    locations = {
        'home': {
            'name': WEATHER_LOCATION,
            'lat': WEATHER_LATITUDE,
            'lon': WEATHER_LONGITUDE,
        },
        'east_med': {
            'name': EAST_MED_WEATHER_LOCATION,
            'lat': EAST_MED_WEATHER_LATITUDE,
            'lon': EAST_MED_WEATHER_LONGITUDE,
        },
        'dubrovnik': {
            'name': DUBROVNIK_WEATHER_LOCATION,
            'lat': DUBROVNIK_WEATHER_LATITUDE,
            'lon': DUBROVNIK_WEATHER_LONGITUDE,
        },
    }
    return locations.get(key, locations['home'])

# --- Scaffolded data fetchers ---
def get_events():
    now = now_local()
    all_events = []
    for cal in FASTMAIL_CALENDARS:
        events = parse_ics_events_from_url(cal['url'], cal['name'], cal['color'])
        all_events.extend(events)
    # Sort and filter future events only
    def event_dt_as_datetime(e):
        dt = as_local_datetime(e['dt'])
        if dt is not None:
            return dt
        return datetime.datetime.max.replace(tzinfo=APP_TIMEZONE)
    
    all_events = [e for e in all_events if event_dt_as_datetime(e) >= now]
    all_events.sort(key=event_dt_as_datetime)
    return all_events

def get_pirate_weather_data(location_key='home'):
    """Fetch weather data from PirateWeather API (alternative provider)"""
    def fetch():
        location = get_weather_location(location_key)
        lat = location['lat']
        lon = location['lon']
        url = f"https://api.pirateweather.net/forecast/{PIRATEWEATHER_API_KEY}/{lat},{lon}"
        params = {
            'units': 'uk2',
            'exclude': 'minutely,alerts',
            'extend': 'hourly'
        }
        try:
            resp = requests.get(url, params=params, timeout=10)
            if resp.status_code != 200:
                print('PirateWeather API fetch failed:', resp.text)
                return (None, None, None, None, location['name'])
            data = resp.json()
            # Current weather
            currently = data.get('currently', {})
            if not currently:
                print('No current weather data from PirateWeather, full data:', data)
                return (None, None, None, None, location['name'])
            current_time = datetime.datetime.fromtimestamp(currently.get('time'), APP_TIMEZONE)
            iso_time = current_time.strftime('%Y-%m-%dT%H:%M:%SZ')
            icon = currently.get('icon', 'cloudy')
            weather_code = ICON_TO_CODE.get(icon, '7')
            current = {
                'time': iso_time,
                'significantWeatherCode': weather_code,
                'icon': icon,
                'maxScreenAirTemp': currently.get('temperature'),
                'feelsLikeTemperature': currently.get('apparentTemperature', currently.get('temperature')),
                'probOfPrecipitation': currently.get('precipProbability'),
                'windSpeed': currently.get('windSpeed'),
                'windGust': currently.get('windGust'),
                'windBearing': currently.get('windBearing'),
                'visibility': currently.get('visibility'),
                'pressure': currently.get('pressure'),
                'dewPoint': currently.get('dewPoint'),
                'summary': currently.get('summary', ''),
                'location': location['name']
            }
            # Forecast: next 7 days from 'daily' data
            daily = data.get('daily', {}).get('data', [])
            forecast_days = []
            for i in range(min(7, len(daily))):
                dt_utc = datetime.datetime.fromtimestamp(daily[i]['time'], datetime.timezone.utc)
                dt_local = dt_utc.astimezone(APP_TIMEZONE)
                weekday = dt_local.strftime('%a')
                day_icon = daily[i].get('icon', 'cloudy')
                day_weather_code = ICON_TO_CODE.get(day_icon, '7')
                day_data = {
                    'time': dt_utc.strftime('%Y-%m-%dT%H:%M:%SZ'),
                    'significantWeatherCode': day_weather_code,
                    'icon': day_icon,
                    'maxScreenAirTemp': daily[i].get('temperatureHigh'),
                    'minScreenAirTemp': daily[i].get('temperatureLow'),
                    'probOfPrecipitation': daily[i].get('precipProbability'),
                    'summary': daily[i].get('summary', '')
                }
                forecast_days.append((day_data, weekday))

            # Restore hourly and daily summaries if present
            hourly_summary = ''
            daily_summary = ''
            if 'hourly' in data and isinstance(data['hourly'], dict):
                hourly_summary = data['hourly'].get('summary', '') or ''
            if 'daily' in data and isinstance(data['daily'], dict):
                daily_summary = data['daily'].get('summary', '') or ''
            # Fallback: use first day's summary if daily_summary is empty
            if not daily_summary and daily and 'summary' in daily[0]:
                daily_summary = daily[0]['summary']
            return (current, forecast_days, hourly_summary, daily_summary, location['name'])
        except Exception as e:
            print('Error fetching weather from PirateWeather:', e)
            return (None, None, None, None, location['name'])
    return fetch()

def get_news_items():
    newsfeed_url = "http://feeds.bbci.co.uk/news/scotland/rss.xml"
    newsfeed = feedparser.parse(newsfeed_url)
    news_items = []
    if newsfeed and 'entries' in newsfeed:
        for entry in newsfeed.entries[:8]:
            # Try to extract published time if available
            pub_iso = None
            try:
                if 'published_parsed' in entry and entry.published_parsed:
                    dt = datetime.datetime(*entry.published_parsed[:6], tzinfo=datetime.timezone.utc)
                    pub_iso = dt.isoformat()
                elif 'updated_parsed' in entry and entry.updated_parsed:
                    dt = datetime.datetime(*entry.updated_parsed[:6], tzinfo=datetime.timezone.utc)
                    pub_iso = dt.isoformat()
                elif 'published' in entry:
                    # fallback to raw string
                    pub_iso = entry.get('published')
            except Exception:
                pub_iso = None

            news_items.append({
                'title': entry.title,
                'link': entry.link,
                'summary': entry.summary,
                'published': pub_iso
            })
    return news_items

# Helper: render just the events list
@app.route('/events-fragment')
def events_fragment():
    events = get_events()
    # Annotate each event with a display string for date/time (Today/Tomorrow handling)
    now_dt = now_local()

    for e in events:
        dt = e.get('dt')
        try:
            display = format_event_display(dt, now_dt)
        except Exception:
            display = ''
        e['display_date'] = display

    return render_template('fragments/events-fragment.html', events=events, now=now_dt)

# Separate AJAX endpoints for individual weather fragments
@app.route('/current-weather-fragment')
def current_weather_fragment():
    location_key = request.args.get('location', 'home')
    def fetch():
        return get_pirate_weather_data(location_key)
    cache_key = f"weather_current_{location_key}"
    pirate_weather, _, _, _, weather_location = get_cached_weather(cache_key, fetch, cache_seconds=900)  # 15 min cache
    return render_template('fragments/current-weather-fragment.html',
                         pirate_weather=pirate_weather,
                         weather_location=weather_location,
                         weather_map=WEATHER_MAP)

@app.route('/forecast-weather-fragment')
def forecast_weather_fragment():
    location_key = request.args.get('location', 'home')
    def fetch():
        return get_pirate_weather_data(location_key)
    cache_key = f"weather_forecast_{location_key}"
    _, pirate_forecast, hourly_summary, daily_summary, weather_location = get_cached_weather(cache_key, fetch, cache_seconds=1800)  # 30 min cache
    return render_template('fragments/forecast-weather-fragment.html',
                         pirate_forecast=pirate_forecast,
                         hourly_summary=hourly_summary,
                         daily_summary=daily_summary,
                         weather_location=weather_location,
                         weather_map=WEATHER_MAP)

# Helper: render just the news ticker
@app.route('/news-fragment')
def news_fragment():
    news_items = get_news_items()
    # Compute initial age string for the first news item (used in header)
    initial_age = ''
    try:
        if news_items and news_items[0].get('published'):
            pub = news_items[0].get('published')
            try:
                pub_dt = datetime.datetime.fromisoformat(pub)
            except Exception:
                # try parsing common formats
                pub_dt = None
            if pub_dt is not None:
                if pub_dt.tzinfo is None:
                    pub_dt = pub_dt.replace(tzinfo=datetime.timezone.utc)
                now_dt = datetime.datetime.now(datetime.timezone.utc)
                diff = now_dt - pub_dt
                hours = int(diff.total_seconds() // 3600)
                if hours <= 0:
                    initial_age = 'Less than 1 Hour ago'
                elif hours == 1:
                    initial_age = '1 Hour ago'
                else:
                    initial_age = f"{hours} Hours ago"
    except Exception:
        initial_age = ''

    return render_template('fragments/news-fragment.html', news_items=news_items, initial_news_age=initial_age)


# Helper: render just the Todoist list
@app.route('/todoist-fragment')
def todoist_fragment():
    tasks = get_todoist_tasks()
    return render_template('fragments/todoist-fragment.html', tasks=tasks, now=now_local())


@app.route('/cruise-temps')
def cruise_temps():
    """Return JSON {date: \"N°\"} for each cruise port that has coordinates."""
    to_fetch = [(e['date'], e['lat'], e['lon']) for e in CRUISE_ITINERARY if e['lat'] is not None]

    def fetch(date, lat, lon):
        try:
            url = f"https://api.pirateweather.net/forecast/{PIRATEWEATHER_API_KEY}/{lat},{lon}"
            resp = requests.get(url, params={'units': 'uk2', 'exclude': 'minutely,hourly,daily,alerts'}, timeout=8)
            if resp.status_code == 200:
                temp = resp.json().get('currently', {}).get('temperature')
                if temp is not None:
                    return f"{round(float(temp))}°"
        except Exception:
            pass
        return '-'

    results = {}
    with ThreadPoolExecutor(max_workers=7) as pool:
        for (date, lat, lon), label in zip(to_fetch, pool.map(lambda args: fetch(*args), to_fetch)):
            results[date] = label
    return jsonify(results)


@app.route('/bins-fragment')
def bins_fragment():
    bin_info = get_this_week_bins()
    return render_template('fragments/bins-fragment.html', bin_info=bin_info)





def _load_bin_details():
    with open(os.path.join(os.path.dirname(__file__), 'bin_schedule.json')) as f:
        data = json.load(f)
    bin_details = {b['name']: b for b in data.get('bins', [])}
    return bin_details, data


def _map_ics_summary_to_bin_name(summary_text):
    s = (summary_text or '').strip().lower().replace(' ', '')
    if 'garden' in s or 'brown' in s:
        return 'Garden'
    if 'grey' in s or 'waste' in s:
        return 'Waste'
    if 'glass' in s:
        return 'Glass'
    if 'paper' in s:
        return 'Paper'
    if 'recycling' in s:
        return 'Recycling'
    return None


def _next_weekly_occurrence(start_date, rrule, today):
    interval = int((rrule.get('INTERVAL') or [1])[0])
    if interval < 1:
        interval = 1

    step_days = 7 * interval
    if start_date >= today:
        occurrence = start_date
        n = 0
    else:
        delta_days = (today - start_date).days
        n = (delta_days + step_days - 1) // step_days
        occurrence = start_date + datetime.timedelta(days=n * step_days)
        if occurrence < today:
            n += 1
            occurrence = start_date + datetime.timedelta(days=n * step_days)

    count = rrule.get('COUNT')
    if count:
        max_occurrences = int(count[0])
        if n >= max_occurrences:
            return None

    until = rrule.get('UNTIL')
    if until:
        until_val = until[0]
        if isinstance(until_val, datetime.datetime):
            until_date = until_val.date()
        else:
            until_date = until_val
        if occurrence > until_date:
            return None

    return occurrence


def _get_next_occurrence_date(component, today):
    dtstart = component.get('dtstart')
    if not dtstart:
        return None

    start_val = dtstart.dt
    if isinstance(start_val, datetime.datetime):
        start_date = start_val.date()
    else:
        start_date = start_val

    rrule = component.get('rrule')
    if not rrule:
        return start_date if start_date >= today else None

    freq = (rrule.get('FREQ') or [''])[0]
    if str(freq).upper() != 'WEEKLY':
        return None

    return _next_weekly_occurrence(start_date, rrule, today)


def _get_bins_from_ics():
    bin_details, data = _load_bin_details()
    now = now_local()
    cutoff = now.date() + datetime.timedelta(days=1) if now.hour >= 8 else now.date()

    try:
        resp = requests.get(BIN_ICS_URL, timeout=15)
        if resp.status_code != 200:
            return None

        cal = Calendar.from_ical(resp.content)
        occurrences = []
        for component in cal.walk('VEVENT'):
            summary = str(component.get('summary') or '')
            mapped_name = _map_ics_summary_to_bin_name(summary)
            if not mapped_name:
                continue

            occ_date = _get_next_occurrence_date(component, cutoff)
            if not occ_date:
                continue

            occurrences.append((occ_date, mapped_name))

        if not occurrences:
            return None

        next_date = min(d for d, _ in occurrences)
        names = []
        for d, name in occurrences:
            if d == next_date and name not in names:
                names.append(name)

        bins = [bin_details[name] for name in names if name in bin_details]
        if not bins:
            return None

        return {
            'bins': bins,
            'collection_day': next_date.strftime('%A')
        }
    except Exception:
        return None


def get_this_week_bins():
    return _get_bins_from_ics() or {'bins': [], 'collection_day': 'Unknown'}


def get_todoist_tasks():
    """Fetch tasks using the Todoist sync API v1 and return tasks from
    the 'Personal' and 'Shopping' projects (case-insensitive).
    Uses `sync_token='*'` and `resource_types='["all"]'` as per the sync API example.
    """
    if not TODOIST_API_KEY:
        return []
    headers = {
        'Authorization': f'Bearer {TODOIST_API_KEY}'
    }
    data = {
        'sync_token': '*',
        'resource_types': '["all"]'
    }
    try:
        resp = requests.post('https://api.todoist.com/api/v1/sync', headers=headers, data=data, timeout=15)
        if resp.status_code != 200:
            return []
        payload = resp.json()
        projects = payload.get('projects', []) or []
        items = payload.get('items', []) or []

        # Find the 'Personal' project only (case-insensitive)
        personal = None
        for p in projects:
            if p.get('name', '').lower() == 'personal':
                personal = p
                break

        if personal is None:
            return []

        personal_id = personal.get('id')

        # Helper: map project name to a CSS color
        def project_color(name):
            n = (name or '').lower()
            if 'personal' in n:
                return '#1f77b4'
            return '#888888'

        # Helper to format due date
        def format_due(due):
            if not due:
                return ''
            date_str = due.get('date') or due.get('datetime')
            if not date_str:
                return ''
            try:
                if len(date_str) == 10:
                    return date_str
                ds = date_str.replace('Z', '+00:00')
                dt = datetime.datetime.fromisoformat(ds)
                return dt.strftime('%Y-%m-%d %H:%M')
            except Exception:
                return date_str

        # Build the personal project info
        project_info = {
            'id': personal_id,
            'name': personal.get('name'),
            'color': project_color(personal.get('name')),
            'tasks': []
        }

        # Collect tasks for personal project
        for it in items:
            if it.get('project_id') == personal_id:
                task = {
                    'content': it.get('content'),
                    'due': format_due(it.get('due')),
                    'id': it.get('id')
                }
                project_info['tasks'].append(task)

        # Sort tasks by due
        project_info['tasks'].sort(key=lambda t: (t['due'] == '', t['due']))

        return [project_info]
    except Exception:
        return []


# --- ICS PARSING ---
def parse_ics_events_from_url(url, cal_name, color):
    events = []
    try:
        resp = requests.get(url, timeout=10)
        if resp.status_code != 200:
            return events
        cal = Calendar.from_ical(resp.content)
        for component in cal.walk():
            if component.name == "VEVENT":
                dtstart = component.get('dtstart')
                if dtstart is None:
                    continue
                summary = str(component.get('summary'))
                events.append({
                    'dt': dtstart.dt,
                    'summary': summary,
                    'calendar': cal_name,
                    'color': color,
                })
    except Exception:
        pass
    return events


@app.route('/', methods=['GET', 'POST'])
def index():
    bin_info = get_this_week_bins()
    news_items = get_news_items()
    now = now_local()

    all_events = get_events()
    for e in all_events:
        dt = e.get('dt')
        try:
            display = format_event_display(dt, now)
        except Exception:
            display = ''
        e['display_date'] = display

    return render_template(
        'index.html',
        events=all_events,
        now=now,
        pirate_weather=None,
        pirate_forecast=None,
        hourly_summary='',
        daily_summary='',
        news_items=news_items,
        bin_info=bin_info,
        weather_location='',
        weather_map=WEATHER_MAP,
    )

if __name__ == '__main__':
    app.run(host="0.0.0.0", port="8000", debug=True)
