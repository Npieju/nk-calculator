from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from .predictor import build_comparisons
from .scraper import NetkeibaScraper


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
    "三連単(1着流し)合成オッズ": "trifecta_first_flow_odds",
    "三連単(2着流し)合成オッズ": "trifecta_second_flow_odds",
    "三連単(3着流し)合成オッズ": "trifecta_third_flow_odds",
    "差異幅": "spread",
    "馬番A": "horse_no_a",
    "馬名A": "horse_name_a",
    "馬番B": "horse_no_b",
    "馬名B": "horse_name_b",
    "馬連オッズ": "quinella_odds",
    "馬単表裏合成オッズ": "exacta_both_flow_odds",
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


def analyze_race(race_url: str, excluded_horses: list[str] | None = None) -> dict[str, Any]:
    scraper = NetkeibaScraper()
    scraped = scraper.scrape(race_url)
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
            "race_date": scraped.get("race_date"),
            "odds_updated_at": scraped.get("odds_updated_at"),
            "analyzed_at": datetime.now(timezone.utc).isoformat(),
        },
        "odds_status": scraped.get("odds_status", {}),
        "odds": scraped.get("odds", {}),
        "comparisons": comparisons_en,
    }
