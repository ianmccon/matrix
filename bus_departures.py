import requests
import re
import datetime

DEFAULT_USER_AGENT = 'matrix-dashboard/1.0 (+https://example.com)'


def fetch_departures_from_ett(stop_id, timeout=8):
    """Attempt to fetch departures for a stop from Edinburgh Travel Tracker.

    This function tries a few common URL patterns and attempts to parse
    JSON responses or embedded JSON within HTML. Returns a list of
    departures as dicts with keys: service, destination, time.
    """
    candidates = []
    # Common plausible endpoints (may need adjustment depending on ETT API)
    candidates.append(f"https://www.edinburghtraveltracker.co.uk/#/liveDepartures?stopId={stop_id}")
    candidates.append(f"https://www.edinburghtraveltracker.co.uk/StopBoard/{stop_id}")
    candidates.append(f"https://api.edinburghtraveltracker.co.uk/StopBoard/Get/{stop_id}")
    candidates.append(f"https://api.edinburghtraveltracker.co.uk/Stop/{stop_id}/services")

    headers = { 'User-Agent': DEFAULT_USER_AGENT }

    for url in candidates:
        try:
            resp = requests.get(url, headers=headers, timeout=timeout)
        except Exception:
            continue

        if resp.status_code != 200:
            continue

        ctype = resp.headers.get('Content-Type', '')
        text = resp.text

        # If JSON response, try parsing expected structure
        if 'application/json' in ctype or text.strip().startswith('{') or text.strip().startswith('['):
            try:
                data = resp.json()
            except Exception:
                data = None
            if data:
                deps = _parse_common_json_formats(data)
                if deps:
                    return deps

        # Fallback: try to extract JSON embedded in HTML
        # Look for a JavaScript variable or JSON blob
        m = re.search(r'window\.stopData\s*=\s*(\{.*?\});', text, re.S)
        if not m:
            m = re.search(r'var\s+stopBoard\s*=\s*(\{.*?\});', text, re.S)
        if not m:
            # Look for any large JSON array/object in the HTML
            m = re.search(r'(\{\s*"departures".*?\})', text, re.S)
        if m:
            try:
                import json
                payload = json.loads(m.group(1))
                deps = _parse_common_json_formats(payload)
                if deps:
                    return deps
            except Exception:
                pass

    # If all attempts fail, return empty list
    return []


def _parse_common_json_formats(data):
    """Normalize several possible JSON shapes into a list of departures."""
    deps = []

    # Case: top-level list of departures
    if isinstance(data, list):
        for item in data:
            d = _extract_dep_from_item(item)
            if d:
                deps.append(d)
        return deps

    # Case: object with 'departures' or 'services'
    if isinstance(data, dict):
        for key in ('departures', 'services', 'stopBoard', 'data'):
            if key in data and isinstance(data[key], (list, dict)):
                sub = data[key]
                if isinstance(sub, dict):
                    # some shapes use nested keys
                    for v in sub.values():
                        if isinstance(v, list):
                            for item in v:
                                d = _extract_dep_from_item(item)
                                if d:
                                    deps.append(d)
                else:
                    for item in sub:
                        d = _extract_dep_from_item(item)
                        if d:
                            deps.append(d)
                if deps:
                    return deps

        # Try to find departures inside nested structures
        for v in data.values():
            if isinstance(v, list):
                for item in v:
                    d = _extract_dep_from_item(item)
                    if d:
                        deps.append(d)
            elif isinstance(v, dict):
                for vv in v.values():
                    if isinstance(vv, list):
                        for item in vv:
                            d = _extract_dep_from_item(item)
                            if d:
                                deps.append(d)
        return deps

    return deps


def _extract_dep_from_item(item):
    """Try to extract service, destination and time from a JSON item."""
    if not isinstance(item, dict):
        return None
    service = item.get('service') or item.get('line') or item.get('route') or item.get('serviceNo')
    dest = item.get('destination') or item.get('towards') or item.get('direction') or item.get('headsign')
    # time fields could be 'expectedArrival', 'time', 'due', 'expected'
    time_field = None
    for k in ('expectedArrival', 'expected', 'time', 'due', 'arrivalTime'):
        if k in item and item[k]:
            time_field = item[k]
            break

    if not (service and dest and time_field):
        # try shallow fields
        if 'aimed_departure_time' in item and 'expected_departure_time' in item:
            service = service or item.get('route')
            dest = dest or item.get('destination')
            time_field = item.get('expected_departure_time') or item.get('aimed_departure_time')

    if not service or not dest or not time_field:
        return None

    # Normalize time_field to HH:MM if possible
    tstr = str(time_field)
    try:
        # ISO datetime
        dt = None
        if 'T' in tstr:
            dt = datetime.datetime.fromisoformat(tstr.replace('Z', '+00:00'))
            tformatted = dt.strftime('%H:%M')
        else:
            # Try to extract HH:MM
            m = re.search(r'(\d{1,2}:\d{2})', tstr)
            if m:
                tformatted = m.group(1)
            else:
                tformatted = tstr
    except Exception:
        tformatted = tstr

    return {'service': str(service), 'destination': str(dest), 'time': tformatted}


def get_departures_for_stop(stop_id):
    """Public helper: fetch departures and return a sorted list.

    Sorted by time string (lexicographic is usually fine for HH:MM),
    but any non-parseable times will be placed at the end.
    """
    deps = fetch_departures_from_ett(stop_id)
    # Remove duplicates and sort
    unique = []
    seen = set()
    for d in deps:
        key = (d.get('service'), d.get('destination'), d.get('time'))
        if key in seen:
            continue
        seen.add(key)
        unique.append(d)

    def sort_key(d):
        t = d.get('time') or ''
        m = re.match(r'^(\d{1,2}):(\d{2})$', t)
        if m:
            return int(m.group(1))*60 + int(m.group(2))
        return 24*60 + 1

    unique.sort(key=sort_key)
    return unique
