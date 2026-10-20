from datetime import date, datetime, timezone

from aujobsscraper.utils import posted_time
from aujobsscraper.utils.posted_time import EMPTY, PostedTime, from_date, from_iso, from_relative
from aujobsscraper.utils.scraper_utils import calculate_posted_date

UTC = timezone.utc
NOW = datetime(2026, 10, 19, 18, 30, tzinfo=UTC)  # = 2026-10-20 05:30 AEDT


def test_relative_minutes():
    p = from_relative("Posted 25m ago", "AU", now=NOW)
    assert p == PostedTime("2026-10-20", "2026-10-20T05:05:00+11:00", "minute")


def test_relative_hours_uses_board_local_date_when_utc_is_previous_day():
    p = from_relative("Posted 2h ago", "AU", now=NOW)
    assert p.date == "2026-10-20" and p.precision == "hour"
    assert p.ts == "2026-10-20T03:30:00+11:00"


def test_relative_days_is_local_midnight():
    assert from_relative("Posted 2d ago", "AU", now=NOW) == PostedTime(
        "2026-10-18", "2026-10-18T00:00:00+11:00", "day"
    )


def test_relative_30_plus_days():
    assert from_relative("Posted 30+d ago", "AU", now=NOW).date == "2026-09-20"


def test_relative_combined_day_hour():
    p = from_relative("Posted 2d/1h ago", "AU", now=NOW)
    assert p.precision == "hour" and p.ts == "2026-10-18T04:30:00+11:00"


def test_relative_nz_uses_auckland():
    p = from_relative("Posted 25m ago", "NZ", now=NOW)
    assert p.ts == "2026-10-20T07:05:00+13:00" and p.date == "2026-10-20"


def test_unparseable_text_returns_none():
    assert from_relative("Featured", "AU", now=NOW) == EMPTY


def test_from_iso_with_time_is_minute():
    p = from_iso("2026-10-19T22:15:00Z", "AU")
    assert p == PostedTime("2026-10-20", "2026-10-20T09:15:00+11:00", "minute")


def test_from_iso_date_only_is_day():
    assert from_iso("2026-10-19", "AU") == PostedTime("2026-10-19", "2026-10-19T00:00:00+11:00", "day")


def test_from_iso_invalid_and_none():
    assert from_iso("not a date", "AU") == EMPTY and from_iso(None, "AU") == EMPTY


def test_from_date_accepts_date_and_string():
    assert from_date(date(2026, 10, 19), "AU").precision == "day"
    assert from_date("2026-10-19", "AU").ts == "2026-10-19T00:00:00+11:00"


def test_calculate_posted_date_still_returns_local_date(monkeypatch):
    monkeypatch.setattr(posted_time, "_utcnow", lambda: NOW)
    assert calculate_posted_date("Posted 2h ago") == "2026-10-20"
