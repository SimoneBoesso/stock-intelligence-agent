from datetime import date, datetime, timezone

import pandas as pd
import yaml
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
NEWS_FILE = BASE_DIR / "data" / "processed" / "news.parquet"
UNIVERSE_FILE = BASE_DIR / "config" / "universe.yaml"

EXPECTED_COLUMNS = {
    "ticker",
    "article_id",
    "published_at",
    "headline",
    "summary",
    "source",
    "url",
    "ingested_at",
}


def test_news_file_exists():
    assert NEWS_FILE.exists()


def test_news_schema_and_quality():
    df = pd.read_parquet(NEWS_FILE)
    universe = yaml.safe_load(UNIVERSE_FILE.read_text())
    allowed_tickers = set(universe["tickers"])

    assert EXPECTED_COLUMNS.issubset(df.columns)
    assert not df.empty
    assert df["headline"].notna().all()
    assert df["published_at"].notna().all()
    assert df.duplicated(subset=["ticker", "article_id"]).sum() == 0
    assert set(df["ticker"]).issubset(allowed_tickers)
    # Finnhub free tier may miss some symbols (e.g. BRK-B)
    assert df["ticker"].nunique() >= 15
    assert df["published_at"].max() <= datetime.now(timezone.utc)
    assert pd.to_datetime(df["published_at"]).dt.date.min() <= date.today()
