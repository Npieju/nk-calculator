from __future__ import annotations

import copy
from datetime import datetime, timezone
import os
import threading
from typing import Any
from urllib.parse import parse_qs, urlparse

from .scraper import NetkeibaScraper


SCRAPE_CACHE_TTL_SECONDS = max(0, int(os.getenv("SCRAPE_CACHE_TTL_SECONDS", "120")))
_SCRAPE_CACHE: dict[str, dict[str, Any]] = {}
_SCRAPE_CACHE_LOCK = threading.Lock()
RACE_LIST_CACHE_TTL_SECONDS = max(0, int(os.getenv("RACE_LIST_CACHE_TTL_SECONDS", str(SCRAPE_CACHE_TTL_SECONDS))))
_RACE_LIST_CACHE: dict[str, dict[str, Any]] = {}
_RACE_LIST_CACHE_LOCK = threading.Lock()


def _cache_key_for_race_url(race_url: str) -> str:
    parsed = urlparse(race_url)
    race_id = parse_qs(parsed.query).get("race_id", [None])[0]
    race_id_text = str(race_id).strip() if race_id is not None else ""
    if race_id_text:
        return f"race_id:{race_id_text}"
    return race_url.strip()


def _normalize_race_list_date(date_value: str) -> str:
    digits = "".join(ch for ch in str(date_value) if ch.isdigit())
    if len(digits) != 8:
        raise ValueError("date は YYYYMMDD または YYYY-MM-DD 形式で指定してください")
    datetime.strptime(digits, "%Y%m%d")
    return digits


def _cache_key_for_race_list(scope: str, date_value: str) -> str:
    return f"{scope}:{date_value}"


def _is_past_race(race_date: str | None) -> bool:
    if not race_date:
        return False
    try:
        race_dt = datetime.strptime(str(race_date), "%Y-%m-%d").date()
        return race_dt < datetime.now(timezone.utc).date()
    except ValueError:
        return False


def _get_scraped_with_cache(race_url: str, force_refresh: bool) -> tuple[dict[str, Any], bool, int, str | None, str | None]:
    scraper = NetkeibaScraper()
    cache_key = _cache_key_for_race_url(race_url)

    if SCRAPE_CACHE_TTL_SECONDS > 0 and not force_refresh:
        with _SCRAPE_CACHE_LOCK:
            cached = _SCRAPE_CACHE.get(cache_key)
            if cached:
                cached_at = cached.get("cached_at")
                cached_scraped = cached.get("scraped")
                if isinstance(cached_at, datetime) and isinstance(cached_scraped, dict):
                    age_seconds = int((datetime.now(timezone.utc) - cached_at).total_seconds())
                    if age_seconds <= SCRAPE_CACHE_TTL_SECONDS:
                        source_fetched_at = cached.get("source_fetched_at")
                        cache_stored_at = cached_at.isoformat()
                        return copy.deepcopy(cached_scraped), True, max(0, age_seconds), source_fetched_at, cache_stored_at

    fetched_at = datetime.now(timezone.utc).isoformat()
    scraped = scraper.scrape(race_url)
    if SCRAPE_CACHE_TTL_SECONDS > 0:
        cached_at = datetime.now(timezone.utc)
        with _SCRAPE_CACHE_LOCK:
            _SCRAPE_CACHE[cache_key] = {
                "cached_at": cached_at,
                "source_fetched_at": fetched_at,
                "scraped": copy.deepcopy(scraped),
            }
        return scraped, False, 0, fetched_at, cached_at.isoformat()
    return scraped, False, 0, fetched_at, None


def _get_race_list_with_cache(scope: str, date_value: str, force_refresh: bool) -> tuple[dict[str, Any], bool, int, str | None, str | None]:
    scraper = NetkeibaScraper()
    cache_key = _cache_key_for_race_list(scope, date_value)

    if RACE_LIST_CACHE_TTL_SECONDS > 0 and not force_refresh:
        with _RACE_LIST_CACHE_LOCK:
            cached = _RACE_LIST_CACHE.get(cache_key)
            if cached:
                cached_at = cached.get("cached_at")
                cached_data = cached.get("data")
                if isinstance(cached_at, datetime) and isinstance(cached_data, dict):
                    age_seconds = int((datetime.now(timezone.utc) - cached_at).total_seconds())
                    if age_seconds <= RACE_LIST_CACHE_TTL_SECONDS:
                        source_fetched_at = cached.get("source_fetched_at")
                        cache_stored_at = cached_at.isoformat()
                        return copy.deepcopy(cached_data), True, max(0, age_seconds), source_fetched_at, cache_stored_at

    fetched_at = datetime.now(timezone.utc).isoformat()
    data = scraper.list_races(scope, date_value)
    if RACE_LIST_CACHE_TTL_SECONDS > 0:
        cached_at = datetime.now(timezone.utc)
        with _RACE_LIST_CACHE_LOCK:
            _RACE_LIST_CACHE[cache_key] = {
                "cached_at": cached_at,
                "source_fetched_at": fetched_at,
                "data": copy.deepcopy(data),
            }
        return data, False, 0, fetched_at, cached_at.isoformat()
    return data, False, 0, fetched_at, None


def analyze_race(
    race_url: str,
    excluded_horses: list[str] | None = None,
    force_refresh: bool = False,
) -> dict[str, Any]:
    scraped, cache_hit, cache_age_seconds, source_fetched_at, cache_stored_at = _get_scraped_with_cache(race_url, force_refresh)
    race_date = scraped.get("race_date")
    is_past_race = _is_past_race(race_date)
    _ = excluded_horses
    return {
        "race": {
            "race_url": scraped.get("race_url"),
            "race_id": scraped.get("race_id"),
            "race_name": scraped.get("race_name"),
            "race_date": race_date,
            "odds_updated_at": scraped.get("odds_updated_at"),
            "cache_hit": cache_hit,
            "cache_age_seconds": cache_age_seconds,
            "source_fetched_at": source_fetched_at,
            "cache_stored_at": cache_stored_at,
            "is_past_race": is_past_race,
            "refresh_recommended": not is_past_race,
            "analyzed_at": datetime.now(timezone.utc).isoformat(),
        },
        "entries": scraped.get("entries", []),
        "odds_status": scraped.get("odds_status", {}),
        "odds": scraped.get("odds", {}),
    }


def list_races(scope: str, date: str, force_refresh: bool = False) -> dict[str, Any]:
    normalized_scope = str(scope).strip().lower()
    if normalized_scope not in {"jra", "nar"}:
        raise ValueError("scope は jra または nar を指定してください")

    normalized_date = _normalize_race_list_date(date)
    data, cache_hit, cache_age_seconds, source_fetched_at, cache_stored_at = _get_race_list_with_cache(
        normalized_scope,
        normalized_date,
        force_refresh,
    )
    return {
        "scope": normalized_scope,
        "date": normalized_date,
        "cache_hit": cache_hit,
        "cache_age_seconds": cache_age_seconds,
        "source_fetched_at": source_fetched_at,
        "cache_stored_at": cache_stored_at,
        "meetings": data.get("meetings", []),
        "available_venues": data.get("available_venues", []),
    }
