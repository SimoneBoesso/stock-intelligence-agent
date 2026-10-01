from datetime import date

import pandas as pd
import yaml
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
FILINGS_FILE = BASE_DIR / "data" / "processed" / "filings.parquet"
UNIVERSE_FILE = BASE_DIR / "config" / "universe.yaml"

EXPECTED_COLUMNS = {
    "ticker",
    "cik",
    "form",
    "filed_at",
    "accession_number",
    "primary_document",
    "ingested_at",
}
ALLOWED_FORMS = {"10-K", "10-Q", "8-K"}


def test_filings_file_exists():
    assert FILINGS_FILE.exists()


def test_filings_schema_and_quality():
    df = pd.read_parquet(FILINGS_FILE)
    universe = yaml.safe_load(UNIVERSE_FILE.read_text())
    expected_tickers = set(universe["tickers"])

    assert EXPECTED_COLUMNS.issubset(df.columns)
    assert not df.empty
    assert set(df["form"]).issubset(ALLOWED_FORMS)
    assert df.duplicated(subset=["ticker", "accession_number"]).sum() == 0
    assert pd.to_datetime(df["filed_at"]).dt.date.max() <= date.today()
    assert set(df["ticker"]) == expected_tickers
