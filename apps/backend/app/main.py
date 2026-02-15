from __future__ import annotations

import os
from pathlib import Path
import sys

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from .schemas import AnalyzeRequest, AnalyzeResponse


ROOT_DIR = Path(__file__).resolve().parents[3]
CORE_DIR = ROOT_DIR / "packages" / "core"
if str(CORE_DIR) not in sys.path:
    sys.path.insert(0, str(CORE_DIR))

from nk_core import analyze_race

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


@app.post("/v1/analyze", response_model=AnalyzeResponse)
def analyze(payload: AnalyzeRequest) -> dict:
    race_url = str(payload.race_url).strip()
    if "race.netkeiba.com/race/shutuba.html" not in race_url or "race_id=" not in race_url:
        raise HTTPException(status_code=400, detail="対応URLは netkeiba の出馬表ページ（/race/shutuba.html?race_id=...）です")
    try:
        return analyze_race(race_url, excluded_horses=payload.excluded_horses)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"分析に失敗しました: {exc}") from exc
