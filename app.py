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

WEATHER_LOCATION = config["WEATHER_LOCATION"]
WEATHER_LATITUDE = config["WEATHER_LATITUDE"]
WEATHER_LONGITUDE = config["WEATHER_LONGITUDE"]
FASTMAIL_CALENDARS = config["FASTMAIL_CALENDARS"]
WEATHER_MAP = config["WEATHER_MAP"]
PIRATEWEATHER_API_KEY = config.get("PIRATEWEATHER_API_KEY", "")
# Todoist API key (Personal project)
TODOIST_API_KEY = 'ce6e344c9815d4a39bfcc3533254d046dfdf1c2b'

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

# --- Scaffolded data fetchers ---
def get_events():
    now = datetime.datetime.now()
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

def get_pirate_weather_data():
    """Fetch weather data from PirateWeather API (alternative provider)"""
    if not PIRATEWEATHER_API_KEY:
        print('PirateWeather API key not configured')
        return (None, None, None, None)
    
    lat = WEATHER_LATITUDE
    lon = WEATHER_LONGITUDE
    url = f"https://api.pirateweather.net/forecast/{PIRATEWEATHER_API_KEY}/{lat},{lon}"
    params = {
        'units': 'uk2'  # UK units: Celsius, m/s
    }
    
    try:
        resp = requests.get(url, params=params, timeout=10)
        if resp.status_code != 200:
            print('PirateWeather API fetch failed:', resp.text)
            return (None, None, None, None)
        
        data = resp.json()
        
        # Extract summaries
        hourly_summary = data.get('hourly', {}).get('summary', '')
        daily_summary = data.get('daily', {}).get('summary', '')
        
        # Current weather from 'currently' block
        currently = data.get('currently', {})
        if not currently:
            print('No current weather data from PirateWeather')
            return (None, None, None, None, None)
        
        # Convert PirateWeather response to Met Office-like format for template compatibility
        # Convert Unix timestamp to ISO8601 string
        current_time = datetime.datetime.utcfromtimestamp(currently.get('time', 0))
        iso_time = current_time.strftime('%Y-%m-%dT%H:%M:%SZ')
        
        # Map icon to significantWeatherCode (0-30)
        icon_to_code = {
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
            'thunderstorm': '30'
        }
        icon = currently.get('icon', 'cloudy')
        weather_code = icon_to_code.get(icon, '8')
        
        current = {
            'time': iso_time,
            'significantWeatherCode': int(weather_code),
            'icon': icon,
            'maxScreenAirTemp': currently.get('temperature'),
            'feelsLikeTemperature': currently.get('apparentTemperature'),
            'probOfPrecipitation': int(currently.get('precipProbability', 0) * 100),
            'windSpeed': currently.get('windSpeed'),
            'windGust': currently.get('windGust'),
            'windBearing': currently.get('windBearing'),
            'visibility': currently.get('visibility'),
            'pressure': currently.get('pressure'),
            'dewPoint': currently.get('dewPoint'),
            'summary': currently.get('summary', '')
        }
        
        # Forecast: next 7 days from 'daily' data
        daily_data = data.get('daily', {}).get('data', [])
        if not daily_data:
            print('No daily forecast data from PirateWeather')
            return (None, None)
        
        forecast_days = []
        for day in daily_data[:7]:
            dt = datetime.datetime.utcfromtimestamp(day['time'])
            weekday = dt.strftime('%a')
            
            # Convert daily data to Met Office-like format
            day_iso_time = dt.strftime('%Y-%m-%dT%H:%M:%SZ')
            day_icon = day.get('icon', 'cloudy')
            day_weather_code = icon_to_code.get(day_icon, '8')
            
            day_data = {
                'time': day_iso_time,
                'significantWeatherCode': int(day_weather_code),
                'icon': day_icon,
                'maxScreenAirTemp': day.get('temperatureMax'),
                'minScreenAirTemp': day.get('temperatureMin'),
                'feelsLikeTemperature': day.get('apparentTemperatureMax'),
                'probOfPrecipitation': int(day.get('precipProbability', 0) * 100),
                'windSpeed': day.get('windSpeed'),
                'windGust': day.get('windGust'),
                'windBearing': day.get('windBearing'),
                'humidity': int(day.get('humidity', 0) * 100),
                'visibility': day.get('visibility'),
                'cloudCover': int(day.get('cloudCover', 0) * 100),
                'summary': day.get('summary', '')
            }
            
            forecast_days.append((day_data, weekday))
        
        return (current, forecast_days, hourly_summary, daily_summary)
    
    except Exception as e:
        print('Error fetching weather from PirateWeather:', e)
        return (None, None, None, None)

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
    now_dt = datetime.datetime.now()
    tomorrow_date = (now_dt + datetime.timedelta(days=1)).date()

    def day_suffix(day):
        if day in (1, 21, 31):
            return 'st'
        if day in (2, 22):
            return 'nd'
        if day in (3, 23):
            return 'rd'
        return 'th'

    for e in events:
        dt = e.get('dt')
        display = ''
        try:
            if isinstance(dt, datetime.datetime):
                adt = dt
                if adt.tzinfo is not None:
                    adt = adt.astimezone(datetime.timezone.utc).replace(tzinfo=None)
                # helper: compact time like '9AM' or '9:05AM'
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
                    # Show relative time until the event in hours and minutes (e.g. 3h 40m)
                    delta = adt - now_dt
                    secs = int(delta.total_seconds())
                    if secs <= 0:
                        time_text = "0h 0m"
                    else:
                        hours = secs // 3600
                        minutes = (secs % 3600) // 60
                        time_text = f"{hours}h {minutes}m"
                    display = f"Today in {time_text} - {time_compact}"
                elif adt.date() == tomorrow_date:
                    display = f"Tomorrow - {time_compact}"
                else:
                    display = f"{adt.strftime('%b')} {adt.day}{day_suffix(adt.day)} - {time_compact}"
            elif isinstance(dt, datetime.date):
                if dt == now_dt.date():
                    display = 'Today'
                elif dt == tomorrow_date:
                    display = 'Tomorrow'
                else:
                    display = f"{dt.strftime('%b')} {dt.day}{day_suffix(dt.day)}"
        except Exception:
            display = ''
        e['display_date'] = display

    return render_template('fragments/events-fragment.html', events=events, now=now_dt)

# Helper: render just the weather column
@app.route('/weather-fragment')
def weather_fragment():
    pirate_weather, pirate_forecast, hourly_summary, daily_summary = get_pirate_weather_data()
    
    return render_template('fragments/weather_fragment.html', 
                         pirate_weather=pirate_weather,
                         pirate_forecast=pirate_forecast,
                         hourly_summary=hourly_summary,
                         daily_summary=daily_summary,
                         weather_map=WEATHER_MAP)

# Separate AJAX endpoints for individual weather fragments
@app.route('/current-weather-fragment')
def current_weather_fragment():
    pirate_weather, _, _, _ = get_pirate_weather_data()
    
    return render_template('fragments/current-weather-fragment.html',
                         pirate_weather=pirate_weather,
                         weather_map=WEATHER_MAP)

@app.route('/forecast-weather-fragment')
def forecast_weather_fragment():
    _, pirate_forecast, hourly_summary, daily_summary = get_pirate_weather_data()
    
    return render_template('fragments/forecast-weather-fragment.html',
                         pirate_forecast=pirate_forecast,
                         hourly_summary=hourly_summary,
                         daily_summary=daily_summary,
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
    return render_template('fragments/todoist-fragment.html', tasks=tasks, now=datetime.datetime.now())





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
    
    # Fetch weather
    pirate_weather, pirate_forecast, hourly_summary, daily_summary = get_pirate_weather_data()
    
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
    # Annotate events with display strings for initial page load (Today/Tomorrow handling)
    now_dt = datetime.datetime.now()
    tomorrow_date = (now_dt + datetime.timedelta(days=1)).date()

    def day_suffix(day):
        if day in (1, 21, 31):
            return 'st'
        if day in (2, 22):
            return 'nd'
        if day in (3, 23):
            return 'rd'
        return 'th'

    for e in all_events:
        dt = e.get('dt')
        display = ''
        try:
            if isinstance(dt, datetime.datetime):
                adt = dt
                if adt.tzinfo is not None:
                    adt = adt.astimezone(datetime.timezone.utc).replace(tzinfo=None)
                # build compact time (e.g. 9AM or 9:05AM) so it's available for all branches
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
                    # Show relative time until the event in hours and minutes (e.g. 3h 40m)
                    delta = adt - now_dt
                    secs = int(delta.total_seconds())
                    if secs <= 0:
                        time_text = "0h 0m"
                    else:
                        hours = secs // 3600
                        minutes = (secs % 3600) // 60
                        time_text = f"{hours}h {minutes}m"
                    display = f"Today in {time_text} - {time_compact}"
                elif adt.date() == tomorrow_date:
                    display = f"Tomorrow - {time_compact}"
                else:
                    display = f"{adt.strftime('%b')} {adt.day}{day_suffix(adt.day)} - {time_compact}"
            elif isinstance(dt, datetime.date):
                if dt == now_dt.date():
                    display = 'Today'
                elif dt == tomorrow_date:
                    display = 'Tomorrow'
                else:
                    display = f"{dt.strftime('%b')} {dt.day}{day_suffix(dt.day)}"
        except Exception:
            display = ''
        e['display_date'] = display
    # Fetch Todoist tasks for initial render
    todoist_tasks = get_todoist_tasks()

    return render_template(
        'index.html',
        events=all_events,
        now=now,
        pirate_weather=pirate_weather,
        pirate_forecast=pirate_forecast,
        hourly_summary=hourly_summary,
        daily_summary=daily_summary,
        datetimeformat=datetimeformat,
        news_items=news_items,
        bin_info=bin_info,
        weather_map=WEATHER_MAP,
        todoist_tasks=todoist_tasks,
    )

if __name__ == '__main__':
    app.run(host="0.0.0.0", port="8000", debug=True)
