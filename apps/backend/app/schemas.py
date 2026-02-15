from __future__ import annotations

from pydantic import BaseModel, Field


class AnalyzeRequest(BaseModel):
    race_url: str = Field(..., min_length=10)
    excluded_horses: list[str] = Field(default_factory=list)


class AnalyzeResponse(BaseModel):
    race: dict
    odds_status: dict
    odds: dict
    comparisons: dict
