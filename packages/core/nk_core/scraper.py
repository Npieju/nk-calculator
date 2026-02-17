from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from itertools import permutations
import json
import re
from typing import Any
from urllib.parse import parse_qs, urlparse

import requests
from bs4 import BeautifulSoup


BET_TYPES = ["単勝", "複勝", "枠連", "馬連", "ワイド", "馬単", "三連複", "三連単"]
ODDS_TYPE_MAP = {
    "単勝": "b1",
    "複勝": "b1",
    "枠連": "b2",
    "馬連": "b4",
    "ワイド": "b5",
    "馬単": "b6",
    "三連複": "b7",
    "三連単": "b8",
}
ODDS_TYPE_MAP_NAR = {
    "単勝": "b1",
    "複勝": "b1",
    "枠連": "b3",
    "馬連": "b4",
    "ワイド": "b5",
    "馬単": "b6",
    "三連複": "b7",
    "三連単": "b8",
}
API_ODDS_TYPE_MAP = {
    "単勝": "1",
    "複勝": "2",
    "枠連": "3",
    "馬連": "4",
    "ワイド": "5",
    "馬単": "6",
    "三連複": "7",
    "三連単": "8",
}


@dataclass
class ScrapeOptions:
    timeout: int = 20
    user_agent: str = (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
    )


class NetkeibaScraper:
    def __init__(self, options: ScrapeOptions | None = None) -> None:
        self.options = options or ScrapeOptions()
        self.session = requests.Session()
        self.session.headers.update(
            {
                "User-Agent": self.options.user_agent,
                "Accept-Language": "ja,en-US;q=0.9,en;q=0.8",
            }
        )

    def scrape(self, race_url: str) -> dict[str, Any]:
        html = self._fetch_html(race_url)
        soup = BeautifulSoup(html, "lxml")
        is_nar = self._is_nar_race_url(race_url)

        race_id = self._extract_race_id(race_url)
        race_date = self._extract_race_date(race_id)
        race_name = self._extract_race_name(soup)
        entries = self._extract_race_entries(soup)

        odds: dict[str, Any] = {bet_type: [] for bet_type in BET_TYPES}
        odds_status: dict[str, Any] = {}
        odds_updated_at: str | None = None

        for bet_type in BET_TYPES:
            source_url = self._build_odds_type_url(race_id, bet_type, is_nar=is_nar)
            rows: list[dict[str, str]] = []
            if race_id:
                try:
                    if is_nar:
                        rows = self._extract_odds_rows_from_odds_page(source_url, bet_type, entries)
                    else:
                        api_type = API_ODDS_TYPE_MAP.get(bet_type)
                        if api_type:
                            payload = self._fetch_jra_odds_payload(race_id, api_type, source_url)
                            if odds_updated_at is None:
                                odds_updated_at = self._extract_official_datetime(payload)
                            rows = self._extract_odds_rows_from_api_payload(payload or {}, bet_type, entries)
                        if not rows:
                            rows = self._extract_odds_rows_from_odds_page(source_url, bet_type, entries)
                except Exception:
                    rows = []
            odds[bet_type] = rows
            odds_status[bet_type] = self._build_odds_status(bet_type, rows, source_url, race_date)

        return {
            "race_url": race_url,
            "race_id": race_id,
            "race_name": race_name,
            "race_date": race_date,
            "odds_updated_at": odds_updated_at,
            "entries": entries,
            "odds": odds,
            "odds_status": odds_status,
        }

    @staticmethod
    def _extract_official_datetime(payload: dict[str, Any] | None) -> str | None:
        if not isinstance(payload, dict):
            return None
        data = payload.get("data")
        if not isinstance(data, dict):
            return None
        value = data.get("official_datetime")
        if value is None:
            return None
        text = str(value).strip()
        return text or None

    def _build_odds_status(
        self,
        bet_type: str,
        rows: list[dict[str, str]],
        source_url: str | None,
        race_date: str | None,
    ) -> dict[str, Any]:
        race_date_hint = self._build_future_race_hint(race_date)
        if not rows:
            api_reason = self._fetch_jra_odds_reason(source_url, bet_type)
            message = f"{bet_type}のオッズを取得できませんでした"
            if api_reason:
                message = f"{message} (api_reason: {api_reason})"
            if race_date_hint:
                message = f"{message} ({race_date_hint})"
            return {
                "status": "missing",
                "rows": 0,
                "message": message,
                "source_url": source_url,
            }

        has_odds = any(self._has_available_odds(row.get("オッズ", "")) for row in rows)
        if has_odds:
            return {
                "status": "ok",
                "rows": len(rows),
                "message": f"{bet_type}のオッズを取得しました",
                "source_url": source_url,
            }

        api_reason = self._fetch_jra_odds_reason(source_url, bet_type)
        message = f"{bet_type}は発売前または未更新の可能性があります"
        if api_reason:
            message = f"{message} (api_reason: {api_reason})"
        if race_date_hint:
            message = f"{message} ({race_date_hint})"
        return {
            "status": "unavailable",
            "rows": len(rows),
            "message": message,
            "source_url": source_url,
        }

    @staticmethod
    def _extract_race_id(url: str) -> str | None:
        parsed = urlparse(url)
        return parse_qs(parsed.query).get("race_id", [None])[0]

    @staticmethod
    def _is_nar_race_url(url: str) -> bool:
        host = (urlparse(url).hostname or "").lower()
        return host == "nar.netkeiba.com"

    @staticmethod
    def _extract_race_date(race_id: str | None) -> str | None:
        if not race_id:
            return None
        digits = "".join(ch for ch in race_id if ch.isdigit())
        if len(digits) < 8:
            return None
        yyyymmdd = digits[:8]
        try:
            date_obj = datetime.strptime(yyyymmdd, "%Y%m%d")
            return date_obj.strftime("%Y-%m-%d")
        except ValueError:
            return None

    @staticmethod
    def _build_future_race_hint(race_date: str | None) -> str | None:
        if not race_date:
            return None
        try:
            race_dt = datetime.strptime(race_date, "%Y-%m-%d")
            if race_dt.date() > datetime.now().date():
                return f"race_date={race_date} は未来日付"
        except ValueError:
            return None
        return None

    @staticmethod
    def _build_odds_type_url(race_id: str | None, bet_type: str, is_nar: bool = False) -> str | None:
        if not race_id:
            return None
        odds_type = (ODDS_TYPE_MAP_NAR if is_nar else ODDS_TYPE_MAP).get(bet_type)
        if not odds_type:
            return None
        if is_nar:
            return f"https://nar.netkeiba.com/odds/?race_id={race_id}&type={odds_type}"
        return f"https://race.netkeiba.com/odds/index.html?type={odds_type}&race_id={race_id}"

    def _extract_odds_rows_from_odds_page(
        self,
        source_url: str | None,
        bet_type: str,
        entries: list[dict[str, str]],
    ) -> list[dict[str, str]]:
        if not source_url:
            return []

        html = self._fetch_html(source_url)
        soup = BeautifulSoup(html, "lxml")

        if bet_type in {"単勝", "複勝"}:
            return self._extract_single_place_rows_from_page(soup, bet_type)
        return self._extract_combo_rows_from_page(soup, bet_type)

    def _extract_single_place_rows_from_page(self, soup: BeautifulSoup, bet_type: str) -> list[dict[str, str]]:
        tables = soup.select("table.RaceOdds_HorseList_Table")
        if not tables:
            return []

        table_index = 0 if bet_type == "単勝" else 1
        table = tables[table_index] if len(tables) > table_index else tables[0]
        rows: list[dict[str, str]] = []

        for tr in table.select("tr")[1:]:
            tds = tr.select("td")
            if not tds:
                continue
            values = [td.get_text(" ", strip=True) for td in tds]
            odds_value = self._normalize_odds_value(values[-1] if values else "")
            if not odds_value:
                continue

            horse_no = ""
            for value in values[1:4] + values[:2]:
                text = str(value).strip()
                if text.isdigit():
                    horse_no = str(int(text))
                    break
            if not horse_no:
                continue

            horse_name = values[-2] if len(values) >= 2 else ""
            rows.append({"馬番": horse_no, "馬名": horse_name, "オッズ": odds_value})

        rows.sort(key=lambda row: int(row.get("馬番", "9999")) if row.get("馬番", "").isdigit() else 9999)
        return rows

    def _extract_combo_rows_from_page(self, soup: BeautifulSoup, bet_type: str) -> list[dict[str, str]]:
        unordered = {"枠連", "馬連", "ワイド", "三連複"}
        table_nodes = soup.select("table.Odds_Table")
        if not table_nodes:
            return []

        rows: list[dict[str, str]] = []
        combo_seen: set[tuple[str, str]] = set()

        for table in table_nodes:
            head = table.select_one("tr.col_label th")
            left_no = str(head.get_text(" ", strip=True)) if head else ""

            for tr in table.select("tr.Graph_Odds"):
                odds_cell = tr.select_one("td.Odds")
                if odds_cell is None:
                    continue
                odds_value = self._normalize_odds_value(odds_cell.get_text(" ", strip=True))
                if not odds_value:
                    continue

                cart_item = str(odds_cell.get("cart-item") or "")
                combo_numbers = self._extract_combo_numbers_from_cart_item(cart_item)

                if not combo_numbers:
                    tds = tr.select("td")
                    right_no = str(tds[0].get_text(" ", strip=True)) if tds else ""
                    if left_no.isdigit() and right_no.isdigit():
                        combo_numbers = [str(int(left_no)), str(int(right_no))]

                if not combo_numbers:
                    continue

                if bet_type in unordered:
                    for ordered in permutations(combo_numbers, len(combo_numbers)):
                        combo = "-".join(ordered)
                        key = (combo, odds_value)
                        if key in combo_seen:
                            continue
                        combo_seen.add(key)
                        rows.append({"組み合わせ": combo, "オッズ": odds_value})
                else:
                    combo = "-".join(combo_numbers)
                    key = (combo, odds_value)
                    if key in combo_seen:
                        continue
                    combo_seen.add(key)
                    rows.append({"組み合わせ": combo, "オッズ": odds_value})

        rows.sort(key=lambda row: self._combo_sort_key(row.get("組み合わせ", "")))
        return rows

    @staticmethod
    def _extract_combo_numbers_from_cart_item(cart_item: str) -> list[str]:
        if not cart_item:
            return []
        match = re.search(r"_b\d+_c\d+_([0-9_]+)$", cart_item)
        if not match:
            return []
        parts = [part for part in match.group(1).split("_") if part]
        out: list[str] = []
        for part in parts:
            if part.isdigit():
                out.append(str(int(part)))
        return out

    def _fetch_jra_odds_reason(self, source_url: str | None, bet_type: str) -> str | None:
        race_id = self._extract_race_id(source_url or "")
        if not race_id:
            return None
        odds_type = API_ODDS_TYPE_MAP.get(bet_type)
        if not odds_type:
            return None
        try:
            payload = self._fetch_jra_odds_payload(race_id, odds_type, source_url)
            if not isinstance(payload, dict):
                return None
            data = payload.get("data")
            if isinstance(data, dict):
                odds = data.get("odds")
                if isinstance(odds, dict):
                    typed = odds.get(odds_type)
                    if isinstance(typed, dict) and typed:
                        return None
            reason = payload.get("reason")
            if reason:
                return str(reason)
            status = payload.get("status")
            return str(status) if status else None
        except Exception:
            return None

    def _fetch_jra_odds_payload(
        self,
        race_id: str,
        api_odds_type: str,
        referer_url: str | None,
    ) -> dict[str, Any] | None:
        api_url = "https://race.netkeiba.com/api/api_get_jra_odds.html"
        response = self.session.get(
            api_url,
            params={
                "pid": "api_get_jra_odds",
                "input": "UTF-8",
                "output": "json",
                "race_id": race_id,
                "type": api_odds_type,
                "action": "init",
                "sort": "odds",
                "compress": "0",
            },
            headers={"Referer": referer_url or ""},
            timeout=self.options.timeout,
        )
        response.raise_for_status()
        payload = json.loads(response.text)
        return payload if isinstance(payload, dict) else None

    def _extract_odds_rows_from_api_payload(
        self,
        payload: dict[str, Any],
        bet_type: str,
        entries: list[dict[str, str]],
    ) -> list[dict[str, str]]:
        api_type = API_ODDS_TYPE_MAP.get(bet_type)
        if not api_type:
            return []

        data = payload.get("data")
        if not isinstance(data, dict):
            return []
        odds = data.get("odds")
        if not isinstance(odds, dict):
            return []
        typed_odds = odds.get(api_type)
        if not isinstance(typed_odds, dict) or not typed_odds:
            return []

        horse_name_by_no: dict[str, str] = {}
        for row in entries:
            horse_no = self._extract_horse_number_from_entry_row(row)
            if horse_no:
                horse_name_by_no[horse_no] = self._extract_horse_name_from_entry_row(row)

        rows: list[dict[str, str]] = []

        if bet_type in {"単勝", "複勝"}:
            for horse_no_key, values in typed_odds.items():
                horse_no = str(int(horse_no_key)) if str(horse_no_key).isdigit() else str(horse_no_key)
                if not isinstance(values, list) or not values:
                    continue
                odds_value = str(values[0]).strip() if values[0] is not None else ""
                if bet_type == "複勝" and len(values) >= 2 and values[1] is not None and str(values[1]).strip() not in {"", "0"}:
                    odds_value = f"{str(values[0]).strip()} - {str(values[1]).strip()}"
                rows.append(
                    {
                        "馬番": horse_no,
                        "馬名": horse_name_by_no.get(horse_no, ""),
                        "オッズ": self._normalize_odds_value(odds_value),
                    }
                )
            rows.sort(key=lambda row: int(row.get("馬番", "9999")) if row.get("馬番", "").isdigit() else 9999)
            return rows

        combo_size = 3 if bet_type in {"三連複", "三連単"} else 2
        for combo_key, values in typed_odds.items():
            if not isinstance(values, list) or not values:
                continue
            combo_str = str(combo_key)
            parts = [combo_str[i : i + 2] for i in range(0, len(combo_str), 2)]
            if len(parts) != combo_size or not all(part.isdigit() for part in parts):
                continue
            combo = "-".join(str(int(part)) for part in parts)
            odds_value = str(values[0]).strip() if values[0] is not None else ""
            if bet_type == "ワイド" and len(values) >= 2 and values[1] is not None and str(values[1]).strip() not in {"", "0"}:
                odds_value = f"{str(values[0]).strip()} - {str(values[1]).strip()}"

            odds_text = self._normalize_odds_value(odds_value)
            if bet_type in {"枠連", "馬連", "ワイド", "三連複"}:
                nums = combo.split("-")
                for ordered in permutations(nums, len(nums)):
                    rows.append(
                        {
                            "組み合わせ": "-".join(ordered),
                            "オッズ": odds_text,
                        }
                    )
            else:
                rows.append(
                    {
                        "組み合わせ": combo,
                        "オッズ": odds_text,
                    }
                )

        rows.sort(key=lambda row: self._combo_sort_key(row.get("組み合わせ", "")))
        return rows

    def _fetch_html(self, url: str) -> str:
        response = self.session.get(url, timeout=self.options.timeout)
        response.raise_for_status()
        if not response.encoding:
            response.encoding = response.apparent_encoding
        return response.text

    @staticmethod
    def _extract_race_name(soup: BeautifulSoup) -> str | None:
        candidates = [
            soup.select_one("h1"),
            soup.select_one(".RaceName"),
            soup.select_one(".RaceData01"),
            soup.select_one("title"),
        ]
        for item in candidates:
            if item and item.get_text(strip=True):
                return item.get_text(" ", strip=True)
        return None

    def _extract_race_entries(self, soup: BeautifulSoup) -> list[dict[str, str]]:
        table = self._find_table_by_keywords(soup, ["馬名"]) or self._find_largest_table(soup)
        if table is None:
            return []
        return self._parse_table(table)

    @staticmethod
    def _find_largest_table(soup: BeautifulSoup):
        tables = soup.select("table")
        if not tables:
            return None
        return max(tables, key=lambda t: len(t.select("tr")))

    @staticmethod
    def _find_table_by_keywords(soup: BeautifulSoup, keywords: list[str]):
        for table in soup.select("table"):
            text = table.get_text(" ", strip=True)
            if all(keyword in text for keyword in keywords):
                return table
        return None

    @staticmethod
    def _parse_table(table_tag: Any) -> list[dict[str, str]]:
        rows = table_tag.select("tr")
        if not rows:
            return []

        headers = [th.get_text(" ", strip=True) for th in rows[0].select("th")]
        if not headers:
            thead = table_tag.select_one("thead tr")
            if thead:
                headers = [th.get_text(" ", strip=True) for th in thead.select("th")]

        data: list[dict[str, str]] = []
        for row in rows[1:]:
            cells = row.select("td")
            if not cells:
                continue
            values = [cell.get_text(" ", strip=True) for cell in cells]
            if headers and len(headers) == len(values):
                data.append(dict(zip(headers, values, strict=False)))
            else:
                data.append({f"col_{idx + 1}": value for idx, value in enumerate(values)})
        return data

    @staticmethod
    def _extract_horse_number_from_entry_row(row: dict[str, str]) -> str:
        normalized = {key.replace(" ", ""): str(value).strip() for key, value in row.items()}
        for key in ["馬番", "col_2", "col_1"]:
            value = normalized.get(key, "")
            if value.isdigit():
                return str(int(value))
        return ""

    @staticmethod
    def _extract_horse_name_from_entry_row(row: dict[str, str]) -> str:
        normalized = {key.replace(" ", ""): str(value).strip() for key, value in row.items()}
        for key in ["馬名", "col_4", "col_3"]:
            value = normalized.get(key, "")
            if value:
                return value
        return ""

    @staticmethod
    def _combo_sort_key(combo: str) -> tuple[int, ...]:
        values = [int(x) for x in combo.split("-") if x.isdigit()]
        return tuple(values)

    @staticmethod
    def _normalize_odds_value(value: str) -> str:
        return value.replace(",", "").strip()

    @staticmethod
    def _parse_numeric_odds(value: str) -> float | None:
        text = str(value).strip()
        if not text or text in {"-", "--", "---.-"}:
            return None
        text = text.replace(",", "")
        if "-" in text:
            return None
        try:
            return float(text)
        except ValueError:
            return None

    @staticmethod
    def _has_available_odds(value: str) -> bool:
        text = str(value).strip()
        if not text or text in {"-", "--", "---.-"}:
            return False
        if NetkeibaScraper._parse_numeric_odds(text) is not None:
            return True
        return bool(re.match(r"^\s*([0-9]+(?:\.[0-9]+)?)\s*-\s*([0-9]+(?:\.[0-9]+)?)\s*$", text))
