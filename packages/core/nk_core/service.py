from __future__ import annotations

from typing import Any

from .predictor import build_comparisons
from .scraper import NetkeibaScraper


def analyze_race(race_url: str, excluded_horses: list[str] | None = None) -> dict[str, Any]:
    scraper = NetkeibaScraper()
    scraped = scraper.scrape(race_url)
    comparisons = build_comparisons(
        odds=scraped.get("odds", {}),
        entries=scraped.get("entries", []),
        excluded_horses=excluded_horses,
    )
    return {
        "race": {
            "race_url": scraped.get("race_url"),
            "race_id": scraped.get("race_id"),
            "race_name": scraped.get("race_name"),
            "race_date": scraped.get("race_date"),
        },
        "odds_status": scraped.get("odds_status", {}),
        "odds": scraped.get("odds", {}),
        "comparisons": comparisons,
    }
