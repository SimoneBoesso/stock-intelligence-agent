"""Run the analyst forecast: prompt → LLM → validated Forecast."""

from __future__ import annotations

import json
import re

import pandas as pd
from pydantic import ValidationError

from stock_intelligence.agent.prompt import build_forecast_prompt
from stock_intelligence.llm.call import call_llm
from stock_intelligence.schemas.forecast import Forecast


def extract_json(text: str) -> str:
    """Pull a JSON object out of an LLM reply (handles ```json fences)."""
    text = text.strip()
    fence = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
    if fence:
        return fence.group(1)
    start, end = text.find("{"), text.rfind("}")
    if start != -1 and end != -1 and end > start:
        return text[start : end + 1]
    raise ValueError("No JSON object found in LLM response")


def run_forecast(
    ticker: str,
    forecast_date: str,
    news_df: pd.DataFrame,
    metrics: dict | None = None,
    max_retries: int = 1,
) -> Forecast:
    prompt = build_forecast_prompt(ticker, forecast_date, news_df, metrics)
    last_error: Exception | None = None

    for attempt in range(max_retries + 1):
        raw = call_llm(prompt if attempt == 0 else f"{prompt}\n\nValidation error: {last_error}. Fix the JSON.")
        try:
            cleaned = extract_json(raw)
            return Forecast.model_validate_json(cleaned)
        except (ValueError, ValidationError, json.JSONDecodeError) as e:
            last_error = e

    raise RuntimeError(f"Forecast validation failed after retries: {last_error}")
