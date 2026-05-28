"""Unit tests for pure helper functions in app.py."""

import datetime
import pytest
from zoneinfo import ZoneInfo
from unittest.mock import patch

from app import (
    bearing_to_direction,
    format_event_display,
    as_local_datetime,
    _map_ics_summary_to_bin_name,
    _next_weekly_occurrence,
    get_weather_location,
    parse_ics_events_from_url,
)

TZ = ZoneInfo("Europe/London")

# ---------------------------------------------------------------------------
# bearing_to_direction
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "bearing,expected",
    [
        (0, "N"),
        (22.5, "NNE"),
        (45, "NE"),
        (90, "E"),
        (135, "SE"),
        (180, "S"),
        (225, "SW"),
        (270, "W"),
        (315, "NW"),
        (360, "N"),  # wraps
    ],
)
def test_bearing_to_direction(bearing, expected):
    assert bearing_to_direction(bearing) == expected


def test_bearing_to_direction_none_returns_empty():
    assert bearing_to_direction(None) == ""


# ---------------------------------------------------------------------------
# as_local_datetime
# ---------------------------------------------------------------------------


def test_as_local_datetime_naive_datetime_gets_timezone():
    naive = datetime.datetime(2026, 5, 4, 12, 0, 0)
    result = as_local_datetime(naive)
    assert result.tzinfo is not None
    assert result.year == 2026 and result.month == 5 and result.day == 4


def test_as_local_datetime_aware_datetime_converted_to_app_tz():
    utc_dt = datetime.datetime(2026, 5, 4, 11, 0, 0, tzinfo=datetime.timezone.utc)
    result = as_local_datetime(utc_dt)
    assert result.tzinfo is not None
    # BST is UTC+1 in May, so 11:00 UTC → 12:00 local
    assert result.hour == 12


def test_as_local_datetime_date_becomes_midnight():
    d = datetime.date(2026, 6, 15)
    result = as_local_datetime(d)
    assert isinstance(result, datetime.datetime)
    assert result.hour == 0 and result.minute == 0 and result.second == 0


def test_as_local_datetime_unknown_type_returns_none():
    assert as_local_datetime("not-a-date") is None


# ---------------------------------------------------------------------------
# format_event_display
# ---------------------------------------------------------------------------

# Fixed reference point: Mon 4 May 2026 12:00 BST
NOW = datetime.datetime(2026, 5, 4, 12, 0, 0, tzinfo=TZ)


def test_format_event_display_datetime_today_in_future():
    future = datetime.datetime(2026, 5, 4, 14, 30, 0, tzinfo=TZ)
    result = format_event_display(future, NOW)
    assert result.startswith("Today in")
    assert "2h 30m" in result


def test_format_event_display_datetime_today_in_past_shows_zero():
    past = datetime.datetime(2026, 5, 4, 10, 0, 0, tzinfo=TZ)
    result = format_event_display(past, NOW)
    assert result.startswith("Today in")
    assert "0h 0m" in result


def test_format_event_display_datetime_tomorrow():
    tomorrow = datetime.datetime(2026, 5, 5, 9, 0, 0, tzinfo=TZ)
    result = format_event_display(tomorrow, NOW)
    assert result.startswith("Tomorrow")


def test_format_event_display_datetime_future_date():
    future = datetime.datetime(2026, 6, 1, 10, 0, 0, tzinfo=TZ)
    result = format_event_display(future, NOW)
    assert "Jun" in result
    assert "1st" in result


def test_format_event_display_date_today():
    assert format_event_display(datetime.date(2026, 5, 4), NOW) == "Today"


def test_format_event_display_date_tomorrow():
    assert format_event_display(datetime.date(2026, 5, 5), NOW) == "Tomorrow"


def test_format_event_display_date_future():
    result = format_event_display(datetime.date(2026, 6, 3), NOW)
    assert result == "Jun 3rd"


@pytest.mark.parametrize(
    "day,suffix",
    [
        (1, "st"),
        (2, "nd"),
        (3, "rd"),
        (4, "th"),
        (11, "th"),
        (12, "th"),
        (13, "th"),
        (21, "st"),
        (22, "nd"),
        (23, "rd"),
        (31, "st"),
    ],
)
def test_format_event_display_day_suffixes(day, suffix):
    d = datetime.date(2026, 7, day)
    result = format_event_display(d, NOW)
    assert f"{day}{suffix}" in result


# ---------------------------------------------------------------------------
# _map_ics_summary_to_bin_name
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "summary,expected",
    [
        ("Grey Wheelie Bin", "Waste"),
        ("GREY WASTE BIN", "Waste"),
        ("Garden Waste", "Garden"),  # 'garden' now checked before 'waste'
        ("Brown Bin", "Garden"),
        ("Glass Box", "Glass"),
        ("Recycling Box", "Recycling"),
        ("Paper/Cardboard", "Paper"),
        ("PaperBin", "Paper"),
        ("Unknown Bin", None),
        ("", None),
    ],
)
def test_map_ics_summary_to_bin_name(summary, expected):
    assert _map_ics_summary_to_bin_name(summary) == expected


# ---------------------------------------------------------------------------
# _next_weekly_occurrence
# ---------------------------------------------------------------------------

TODAY = datetime.date(2026, 5, 4)


def test_next_weekly_occurrence_start_today():
    result = _next_weekly_occurrence(TODAY, {"INTERVAL": [1]}, TODAY)
    assert result == TODAY


def test_next_weekly_occurrence_start_7_days_ago():
    start = TODAY - datetime.timedelta(days=7)
    result = _next_weekly_occurrence(start, {"INTERVAL": [1]}, TODAY)
    assert result == TODAY


def test_next_weekly_occurrence_start_in_future():
    start = TODAY + datetime.timedelta(days=3)
    result = _next_weekly_occurrence(start, {"INTERVAL": [1]}, TODAY)
    assert result == start


def test_next_weekly_occurrence_biweekly():
    start = TODAY - datetime.timedelta(days=14)
    result = _next_weekly_occurrence(start, {"INTERVAL": [2]}, TODAY)
    assert result == TODAY


def test_next_weekly_occurrence_expired_count():
    start = TODAY - datetime.timedelta(days=7)
    # n will be 1, COUNT=1 means max_occurrences=1, n>=1 → None
    result = _next_weekly_occurrence(start, {"INTERVAL": [1], "COUNT": [1]}, TODAY)
    assert result is None


def test_next_weekly_occurrence_expired_until():
    start = TODAY - datetime.timedelta(days=7)
    # next occurrence would be TODAY, but UNTIL is yesterday
    until = TODAY - datetime.timedelta(days=1)
    result = _next_weekly_occurrence(start, {"INTERVAL": [1], "UNTIL": [until]}, TODAY)
    assert result is None


def test_next_weekly_occurrence_future_until_allows_occurrence():
    start = TODAY - datetime.timedelta(days=7)
    until = TODAY + datetime.timedelta(days=7)
    result = _next_weekly_occurrence(start, {"INTERVAL": [1], "UNTIL": [until]}, TODAY)
    assert result == TODAY


# ---------------------------------------------------------------------------
# get_weather_location
# ---------------------------------------------------------------------------


def test_get_weather_location_home_returns_dict_keys():
    result = get_weather_location("home")
    assert {"name", "lat", "lon"} == set(result.keys())


def test_get_weather_location_east_med():
    result = get_weather_location("east_med")
    assert "Rhodes" in result["name"]


def test_get_weather_location_dubrovnik():
    result = get_weather_location("dubrovnik")
    assert "Dubrovnik" in result["name"]
    assert {"name", "lat", "lon"} == set(result.keys())


def test_get_weather_location_unknown_falls_back_to_home():
    home = get_weather_location("home")
    unknown = get_weather_location("no_such_place")
    assert unknown == home


def test_get_weather_location_strips_whitespace_and_case():
    home = get_weather_location("home")
    assert get_weather_location("  HOME  ") == home


# ---------------------------------------------------------------------------
# parse_ics_events_from_url
# ---------------------------------------------------------------------------


def _make_ics_bytes(summary, dtstart_str):
    """Build a minimal ICS bytes string with one VEVENT."""
    return (
        "BEGIN:VCALENDAR\r\n"
        "VERSION:2.0\r\n"
        "BEGIN:VEVENT\r\n"
        f"SUMMARY:{summary}\r\n"
        f"DTSTART;VALUE=DATE:{dtstart_str}\r\n"
        "END:VEVENT\r\n"
        "END:VCALENDAR\r\n"
    ).encode()


def _make_ics_bytes_no_dtstart(summary):
    return (
        "BEGIN:VCALENDAR\r\n"
        "VERSION:2.0\r\n"
        "BEGIN:VEVENT\r\n"
        f"SUMMARY:{summary}\r\n"
        "END:VEVENT\r\n"
        "END:VCALENDAR\r\n"
    ).encode()


@patch("app.requests.get")
def test_parse_ics_events_returns_event_with_color(mock_get):
    mock_get.return_value.status_code = 200
    mock_get.return_value.content = _make_ics_bytes("Team Meeting", "20260601")
    events = parse_ics_events_from_url(
        "http://example.com/cal.ics", "Events", "#abc123"
    )
    assert len(events) == 1
    assert events[0]["color"] == "#abc123"
    assert events[0]["calendar"] == "Events"
    assert events[0]["summary"] == "Team Meeting"


@patch("app.requests.get")
def test_parse_ics_events_skips_event_with_no_dtstart(mock_get):
    mock_get.return_value.status_code = 200
    mock_get.return_value.content = _make_ics_bytes_no_dtstart("Bad Event")
    events = parse_ics_events_from_url("http://example.com/cal.ics", "Events", "#fff")
    assert events == []


@patch("app.requests.get")
def test_parse_ics_events_returns_empty_on_http_error(mock_get):
    mock_get.return_value.status_code = 404
    events = parse_ics_events_from_url("http://example.com/cal.ics", "Events", "#fff")
    assert events == []


@patch("app.requests.get")
def test_parse_ics_events_uses_timeout(mock_get):
    mock_get.return_value.status_code = 200
    mock_get.return_value.content = _make_ics_bytes("Event", "20260601")
    parse_ics_events_from_url("http://example.com/cal.ics", "Events", "#fff")
    _, kwargs = mock_get.call_args
    assert kwargs.get("timeout") == 10
