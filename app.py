# --- Fragment endpoints for AJAX section refreshes ---
from flask import render_template_string, render_template, current_app
import json
import feedparser
from flask import Flask, render_template, request, redirect, url_for
from icalendar import Calendar
import datetime
import os
import requests
from collections import defaultdict
# --- CONFIG ---
CONFIG_PATH = os.path.join(os.path.dirname(__file__), 'config_matrix.json')
with open(CONFIG_PATH) as f:
    config = json.load(f)

METOFFICE_API_KEY = config["METOFFICE_API_KEY"]
WEATHER_LOCATION = config["WEATHER_LOCATION"]
WEATHER_LATITUDE = config["WEATHER_LATITUDE"]
WEATHER_LONGITUDE = config["WEATHER_LONGITUDE"]
FASTMAIL_CALENDARS = config["FASTMAIL_CALENDARS"]
WEATHER_MAP = config["WEATHER_MAP"]

app = Flask(__name__)

now = datetime.datetime.now()
# --- Scaffolded data fetchers ---
def get_events():
    all_events = []
    for cal in FASTMAIL_CALENDARS:
        events = parse_ics_events_from_url(cal['url'], cal['name'], cal['color'])
        all_events.extend(events)
    # Sort and filter future events only
    def event_dt_as_datetime(e):
        dt = e['dt']
        if isinstance(dt, datetime.datetime):
            if dt.tzinfo is not None:
                dt = dt.astimezone(datetime.timezone.utc).replace(tzinfo=None)
            return dt
        elif isinstance(dt, datetime.date):
            return datetime.datetime.combine(dt, datetime.time.min)
        return datetime.datetime.max
    
    all_events = [e for e in all_events if event_dt_as_datetime(e) >= now]
    all_events.sort(key=event_dt_as_datetime)
    return all_events

def get_bus_departures():
    url = f"https://lothianapi.co.uk/departureBoards/website?stops=6280325770"
    try:
        resp = requests.get(url, timeout=5)
        if resp.status_code == 200:
            data = resp.json()
            service_map = defaultdict(list)
            for service in data.get("services", []):
                service_name = service.get("service_name", "?")
                for dep in service.get("departures", []):
                    # Use the service name from the service object
                    time = dep.get("departure_time", "?")
                    dest = dep.get("destination", "?")
                    service_map[service_name].append({"time": time, "destination": dest})

            # Only keep next 3 for each service
            bus_departures = []
            for service, times in service_map.items():
                bus_departures.append({
                    "service": service,
                    "departures": times
                })
            return bus_departures
        else:
            return None
    except Exception:
        return None

def get_weather_data():
    # Try to read from cache file written by Celery
    import os
    import json
    cache_path = os.path.join(os.path.dirname(__file__), 'weather_cache.json')
    if os.path.exists(cache_path):
        try:
            with open(cache_path, 'r') as f:
                cache = json.load(f)
            current_weather = cache.get('current_weather')
            forecast_days = cache.get('forecast_days')
            # If cache is valid, return it
            if current_weather and forecast_days:
                return (current_weather, forecast_days)
        except Exception as e:
            print('Error reading weather cache:', e)
            # fallback to live fetch below
    # Fallback: fetch live from Met Office
    lat = WEATHER_LATITUDE
    lon = WEATHER_LONGITUDE
    api_key = METOFFICE_API_KEY
    base_url = "https://data.hub.api.metoffice.gov.uk/sitespecific/v0/point/three-hourly"
    url = f"{base_url}?includeLocationName=true&latitude={lat}&longitude={lon}"
    headers = {
        "apikey": api_key,
        "accept": "application/json"
    }
    try:
        resp = requests.get(url, headers=headers)
        if resp.status_code != 200:
            print('Met Office weather fetch failed:', resp.text)
            return (None, None)
        data = resp.json()
        features = data.get('features', [])
        if not features:
            print('No weather data returned from Met Office')
            return (None, None)
        properties = features[0].get('properties', {})
        periods = properties.get('timeSeries', [])
        if not periods:
            print('No timeSeries data in Met Office response')
            return (None, None)
        # Current weather: first period
        current = periods[0]
        # Forecast: next 7 days (group by date)
        from collections import OrderedDict
        forecast_days_dict = OrderedDict()
        for period in periods:
            dt = datetime.datetime.fromisoformat(period['time'][:-1])  # Remove 'Z'
            day_key = dt.date()
            # Use the first period for each day as the day's forecast
            if day_key not in forecast_days_dict:
                forecast_days_dict[day_key] = period
            if len(forecast_days_dict) >= 7:
                break
        forecast = list(forecast_days_dict.values())
        forecast_days = []
        if forecast:
            for day in forecast:
                # Met Office periods use ISO8601 string in 'time', not 'dt'
                dt = datetime.datetime.fromisoformat(day['time'][:-1])  # Remove 'Z'
                weekday = dt.strftime('%a')
                forecast_days.append((day, weekday))
        return (current, forecast_days)
    except Exception as e:
        print('Error fetching weather:', e)
        return (None, None)

def get_news_items():
    newsfeed_url = "http://feeds.bbci.co.uk/news/scotland/rss.xml"
    newsfeed = feedparser.parse(newsfeed_url)
    news_items = []
    if newsfeed and 'entries' in newsfeed:
        for entry in newsfeed.entries[:8]:
            news_items.append({
                'title': entry.title,
                'link': entry.link,
                'summary': entry.summary
            })
    return news_items

# Helper: render just the events list
@app.route('/events-fragment')
def events_fragment():
    events = get_events()
    return render_template('fragments/events_fragment.html', events=events)

# Helper: render just the bus times block
@app.route('/buses-fragment')
def buses_fragment():
    bus_departures = get_bus_departures()  # Adjust to your actual logic
    all_deps = []
    for bus in bus_departures:
        for dep in bus['departures'][:2]:
            all_deps.append({'service': bus['service'], 'destination': dep['destination'], 'time': dep['time']})
    sorted_deps = sorted(all_deps, key=lambda d: d['time'])
    return render_template('fragments/buses_fragment.html', sorted_deps=sorted_deps)

# Helper: render just the weather column
@app.route('/weather-fragment')
def weather_fragment():
    current_weather, forecast_days = get_weather_data()
    if current_weather and forecast_days is None:
        return render_template('fragments/weather_fragment.html', current_weather=None, forecast_days=None)
    # Adjust to your actual logic
    return render_template('fragments/weather_fragment.html', current_weather=current_weather, forecast_days=forecast_days)

# Helper: render just the news ticker
@app.route('/news-fragment')
def news_fragment():
    news_items = get_news_items()  # Adjust to your actual logic
    return render_template('fragments/news_fragment.html', news_items=news_items)





def get_this_week_bins():
    # Load bin schedule config
    with open(os.path.join(os.path.dirname(__file__), 'bin_schedule.json')) as f:
        config = json.load(f)
    # Determine week number (0 or 1) with week starting on Friday
    today = datetime.date.today()
    # weekday(): Monday=0, ..., Sunday=6; so Friday=4
    if today.weekday() >= 4:
        week_num = today.isocalendar()[1] % 2
    else:
        # For Mon-Thu, use previous week
        prev_week = (today - datetime.timedelta(days=(today.weekday() + 3)))  # Go back to previous Friday
        week_num = prev_week.isocalendar()[1] % 2
    # Find bins for this week
    schedule = config['schedule']
    bins_this_week = []
    for entry in schedule:
        if entry['week'] == week_num:
            bins_this_week = entry['bins']
            break
    # Get bin details
    bin_details = {b['name']: b for b in config['bins']}
    # Brown bin only collected March-November
    month = today.month
    bins = []
    for name in bins_this_week:
        if name == 'Brown Bin' and (month < 3 or month > 11):
            continue
        if name in bin_details:
            bins.append(bin_details[name])
    return {
        'bins': bins,
        'collection_day': config.get('collection_day', 'Thursday')
    }


if app is None:
    app = Flask(__name__)

# --- ICS PARSING ---
def parse_ics_events_from_url(url, cal_name, color):
    events = []
    try:
        resp = requests.get(url)
        if resp.status_code != 200:
            return events
        cal = Calendar.from_ical(resp.content)
        for component in cal.walk():
            if component.name == "VEVENT":
                summary = str(component.get('summary'))
                dtstart = component.get('dtstart').dt
                events.append({
                    'dt': dtstart,
                    'summary': summary,
                    'calendar': cal_name
                })
    except Exception as e:
        pass
    return events


@app.route('/', methods=['GET', 'POST'])
def index():
    # Wheelie bin info
    bin_info = get_this_week_bins()
    # Fetch BBC Scotland newsfeed
    news_items = get_news_items()
    # Current time
    now = datetime.datetime.now()
    # Fetch current weather and forecast

    current_weather, forecast_days = get_weather_data()
    # Prepare weekday names for forecast
    
    
    
    def datetimeformat(ts):
        # Accepts either a UNIX timestamp or ISO8601 string
        if isinstance(ts, (int, float)):
            return datetime.datetime.fromtimestamp(int(ts)).strftime('%H:%M')
        try:
            # Try ISO8601 string (Met Office 'time')
            return datetime.datetime.fromisoformat(ts[:-1]).strftime('%H:%M')
        except Exception:
            return str(ts)
    all_events = get_events()
    bus_departures = get_bus_departures()
    return render_template(
        'index.html',
        events=all_events,
        now=now,
        current_weather=current_weather,
        forecast_days=forecast_days,
        datetimeformat=datetimeformat,
        news_items=news_items,
        bin_info=bin_info,
        bus_departures=bus_departures,
        weather_map=WEATHER_MAP,
    )

if __name__ == '__main__':
    app.run(host="0.0.0.0", port="8000", debug=True)
