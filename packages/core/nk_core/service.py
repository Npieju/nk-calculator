from __future__ import annotations

import copy
from datetime import datetime, timezone
import os
import threading
from typing import Any
from urllib.parse import parse_qs, urlparse

from .predictor import build_comparisons
from .scraper import NetkeibaScraper


SCRAPE_CACHE_TTL_SECONDS = max(0, int(os.getenv("SCRAPE_CACHE_TTL_SECONDS", "120")))
_SCRAPE_CACHE: dict[str, dict[str, Any]] = {}
_SCRAPE_CACHE_LOCK = threading.Lock()


COMPARE_COLUMN_MAP = {
    "馬番": "horse_no",
    "馬名": "horse_name",
    "単勝オッズ": "win_odds",
    "複勝オッズ": "place_odds",
    "馬連流し合成オッズ": "quinella_flow_odds",
    "ワイド流し合成オッズ": "wide_flow_odds",
    "馬単(1着流し)合成オッズ": "exacta_first_flow_odds",
    "馬単(2着流し)合成オッズ": "exacta_second_flow_odds",
    "三連複流し合成オッズ": "trio_flow_odds",
    "三連単1頭流し合成オッズ": "trifecta_single_head_flow_odds",
    "三連単(1着流し)合成オッズ": "trifecta_first_flow_odds",
    "三連単(2着流し)合成オッズ": "trifecta_second_flow_odds",
    "三連単(3着流し)合成オッズ": "trifecta_third_flow_odds",
    "差異率": "spread",
    "差異幅": "spread",
    "馬番A": "horse_no_a",
    "馬名A": "horse_name_a",
    "馬番B": "horse_no_b",
    "馬名B": "horse_name_b",
    "馬連オッズ": "quinella_odds",
    "馬単表裏合成オッズ": "exacta_both_flow_odds",
    "三連単1-2着裏表3着全流し合成オッズ": "trifecta_top2_both_any_third_odds",
}


def _to_english_row(row: dict[str, Any]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for key, value in row.items():
        out[COMPARE_COLUMN_MAP.get(key, key)] = value
    return out


def _to_english_comparisons(comparisons: dict[str, Any]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for table_key, rows in comparisons.items():
        if isinstance(rows, list):
            out[table_key] = [_to_english_row(row) if isinstance(row, dict) else row for row in rows]
        else:
            out[table_key] = rows
    return out


def _cache_key_for_race_url(race_url: str) -> str:
    parsed = urlparse(race_url)
    race_id = parse_qs(parsed.query).get("race_id", [None])[0]
    race_id_text = str(race_id).strip() if race_id is not None else ""
    if race_id_text:
        return f"race_id:{race_id_text}"
    return race_url.strip()


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


def analyze_race(
    race_url: str,
    excluded_horses: list[str] | None = None,
    force_refresh: bool = False,
) -> dict[str, Any]:
    scraped, cache_hit, cache_age_seconds, source_fetched_at, cache_stored_at = _get_scraped_with_cache(race_url, force_refresh)
    race_date = scraped.get("race_date")
    is_past_race = _is_past_race(race_date)
    comparisons = build_comparisons(
        odds=scraped.get("odds", {}),
        entries=scraped.get("entries", []),
        excluded_horses=excluded_horses,
    )
    comparisons_en = _to_english_comparisons(comparisons)
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
        "odds_status": scraped.get("odds_status", {}),
        "odds": scraped.get("odds", {}),
        "comparisons": comparisons_en,
    }
