from __future__ import annotations

from pydantic import BaseModel, Field


class AnalyzeRequest(BaseModel):
    race_url: str = Field(..., min_length=10)
    excluded_horses: list[str] = Field(default_factory=list)
    force_refresh: bool = False


class AnalyzeResponse(BaseModel):
    race: dict
    entries: list[dict] = Field(default_factory=list)
    odds_status: dict
    odds: dict
