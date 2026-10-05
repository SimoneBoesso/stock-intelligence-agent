from enum import Enum

from pydantic import BaseModel, Field


class Direction(str, Enum):
    up = "up"
    down = "down"


class Forecast(BaseModel):
    ticker: str
    forecast_date: str  # ISO date, e.g. "2026-09-28"
    direction: Direction
    confidence: float = Field(ge=0.0, le=1.0)
    rationale: str = Field(min_length=1)
    sources: list[str] = Field(min_length=1)  # at least one cited source
