"""Normalize Finnhub raw news JSON into data/processed/news.parquet."""

from datetime import datetime, timezone
from pathlib import Path
import json
import logging

import pandas as pd

BASE_DIR = Path(__file__).resolve().parent.parent
LOG_DIR = BASE_DIR / "logs"
LOG_FILE = LOG_DIR / "transform_news.log"
NEWS_DIR = BASE_DIR / "data" / "raw" / "news"
OUT_FILE = BASE_DIR / "data" / "processed" / "news.parquet"

LOG_DIR.mkdir(parents=True, exist_ok=True)
OUT_FILE.parent.mkdir(parents=True, exist_ok=True)

logging.basicConfig(
    filename=LOG_FILE,
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


def main() -> None:
    rows: list[dict] = []

    for path in NEWS_DIR.glob("*.json"):
        ticker = path.stem
        articles = json.loads(path.read_text())
        if not isinstance(articles, list):
            logger.warning("Skip %s: expected list, got %s", path.name, type(articles))
            continue

        for article in articles:
            ts = article.get("datetime")
            headline = article.get("headline")
            article_id = article.get("id")
            if ts is None or not headline or article_id is None:
                continue

            rows.append(
                {
                    "ticker": ticker,
                    "article_id": int(article_id),
                    "published_at": datetime.fromtimestamp(int(ts), tz=timezone.utc),
                    "headline": headline,
                    "summary": article.get("summary") or None,
                    "source": article.get("source") or None,
                    "url": article.get("url") or None,
                }
            )

    df = pd.DataFrame(rows)
    if df.empty:
        raise SystemExit(f"No news rows built from {NEWS_DIR}")

    df = df.drop_duplicates(subset=["ticker", "article_id"])
    df["ingested_at"] = datetime.now(timezone.utc)
    df = df.sort_values(["ticker", "published_at"]).reset_index(drop=True)
    df.to_parquet(OUT_FILE, index=False)

    logger.info("Saved %s articles to %s", len(df), OUT_FILE)
    print(f"Saved {len(df)} articles to {OUT_FILE}")
    print(df.groupby("ticker").size().to_string())


if __name__ == "__main__":
    main()
