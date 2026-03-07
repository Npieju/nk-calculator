from __future__ import annotations

import os
from pathlib import Path
import sys
from urllib.parse import parse_qs, urlparse, urlunparse

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from .schemas import AnalyzeRequest, AnalyzeResponse


ROOT_DIR = Path(__file__).resolve().parents[3]
CORE_DIR = ROOT_DIR / "packages" / "core"
if str(CORE_DIR) not in sys.path:
    sys.path.insert(0, str(CORE_DIR))

from nk_core import analyze_race, list_races

app = FastAPI(title="nk-calculator-api", version="0.1.0")

allowed_origins_raw = os.getenv("ALLOWED_ORIGINS", "*")
allowed_origins: list[str] = []
for item in allowed_origins_raw.split(","):
    origin = item.strip()
    if not origin:
        continue
    if origin != "*":
        origin = origin.rstrip("/")
    allowed_origins.append(origin)
    lowered = origin.lower()
    allowed_origins.append(lowered)
allowed_origins = list(dict.fromkeys(allowed_origins))
if not allowed_origins:
    allowed_origins = ["*"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/v1/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/v1/race-selector")
def race_selector(scope: str, date: str, force_refresh: bool = False) -> dict:
    try:
        return list_races(scope=scope, date=date, force_refresh=force_refresh)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"レース一覧の取得に失敗しました: {exc}") from exc


def _normalize_race_url(raw_url: str) -> str:
    race_url = str(raw_url).strip()
    parsed = urlparse(race_url)
    if not parsed.scheme or not parsed.netloc:
        return race_url

    host = (parsed.hostname or "").lower()
    query = parse_qs(parsed.query)
    race_id = str((query.get("race_id") or [""])[0]).strip()

    if host == "race.sp.netkeiba.com":
        host = "race.netkeiba.com"
    if host == "nar.sp.netkeiba.com":
        host = "nar.netkeiba.com"

    if host not in {"race.netkeiba.com", "nar.netkeiba.com"}:
        return race_url
    if not race_id:
        return race_url

    canonical_query = f"race_id={race_id}"
    return urlunparse(("https", host, "/race/shutuba.html", "", canonical_query, ""))


@app.post("/v1/analyze", response_model=AnalyzeResponse)
def analyze(payload: AnalyzeRequest) -> dict:
    race_url = _normalize_race_url(payload.race_url)
    parsed = urlparse(race_url)
    host = (parsed.hostname or "").lower()
    is_supported_host = host in {"race.netkeiba.com", "nar.netkeiba.com"}
    has_race_id = "race_id" in parse_qs(parsed.query)
    if not (is_supported_host and has_race_id):
        raise HTTPException(status_code=400, detail="対応URLは netkeiba のレースページURL（race_id=... を含む）です")
    try:
        return analyze_race(
            race_url,
            excluded_horses=payload.excluded_horses,
            force_refresh=payload.force_refresh,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"分析に失敗しました: {exc}") from exc
