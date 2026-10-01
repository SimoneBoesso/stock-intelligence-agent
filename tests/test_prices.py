from datetime import date

import pandas as pd
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
TRANSFORMED_FILE = BASE_DIR / "data" / "processed" / "prices.parquet"

EXPECTED_COLUMNS = {
    "ticker",
    "date",
    "open",
    "high",
    "low",
    "close",
    "volume",
    "ingested_at",
}


def test_files_exist():
    assert TRANSFORMED_FILE.exists()


def test_prices_schema_and_quality():
    df = pd.read_parquet(TRANSFORMED_FILE)

    assert EXPECTED_COLUMNS.issubset(df.columns)
    assert not df.empty
    assert df.duplicated(subset=["ticker", "date"]).sum() == 0
    assert pd.to_datetime(df["date"]).dt.date.max() <= date.today()
    assert "SPY" in set(df["ticker"])
