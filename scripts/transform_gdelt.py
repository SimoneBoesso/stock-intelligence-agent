"""Normalize GDELT raw JSON and append into data/processed/news.parquet.

Keeps existing Finnhub rows. Dedupes on (ticker, url) then (ticker, article_id).
Re-run this after ``transform_news.py`` if Finnhub was rebuilt (that script overwrites).
"""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
import hashlib
import json
import logging

import pandas as pd

BASE_DIR = Path(__file__).resolve().parent.parent
LOG_DIR = BASE_DIR / "logs"
LOG_FILE = LOG_DIR / "transform_gdelt.log"
RAW_DIR = BASE_DIR / "data" / "raw" / "news_gdelt"
OUT_FILE = BASE_DIR / "data" / "processed" / "news.parquet"

LOG_DIR.mkdir(parents=True, exist_ok=True)
OUT_FILE.parent.mkdir(parents=True, exist_ok=True)

logging.basicConfig(
    filename=LOG_FILE,
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


def article_id_from_url(url: str) -> int:
    """Stable positive int64 from URL (GDELT has no numeric id)."""
    digest = hashlib.md5(url.encode("utf-8")).hexdigest()
    return int(digest[:15], 16)


def parse_seendate(value: str | None) -> datetime | None:
    if not value:
        return None
    # JSON ArtList: 20261002T104500Z
    try:
        return datetime.strptime(value, "%Y%m%dT%H%M%SZ").replace(tzinfo=timezone.utc)
    except ValueError:
        pass
    # Fallback ISO-ish
    try:
        return pd.to_datetime(value, utc=True).to_pydatetime()
    except (ValueError, TypeError):
        return None


def load_gdelt_rows() -> pd.DataFrame:
    rows: list[dict] = []
    for path in sorted(RAW_DIR.glob("*.json")):
        ticker = path.stem
        articles = json.loads(path.read_text())
        if not isinstance(articles, list):
            logger.warning("Skip %s: expected list, got %s", path.name, type(articles))
            continue
        for article in articles:
            url = article.get("url")
            title = article.get("title")
            published_at = parse_seendate(article.get("seendate"))
            if not url or not title or published_at is None:
                continue
            rows.append(
                {
                    "ticker": ticker,
                    "article_id": article_id_from_url(url),
                    "published_at": published_at,
                    "headline": title,
                    "summary": None,
                    "source": article.get("domain") or "gdelt",
                    "url": url,
                }
            )
    return pd.DataFrame(rows)


def main() -> None:
    if not RAW_DIR.exists():
        raise SystemExit(f"No GDELT raw dir: {RAW_DIR} (run download_gdelt.py first)")

    gdelt = load_gdelt_rows()
    if gdelt.empty:
        raise SystemExit(f"No GDELT rows built from {RAW_DIR}")

    gdelt["ingested_at"] = datetime.now(timezone.utc)

    if OUT_FILE.exists():
        existing = pd.read_parquet(OUT_FILE)
        before = len(existing)
        combined = pd.concat([existing, gdelt], ignore_index=True)
    else:
        before = 0
        combined = gdelt

    combined = combined.drop_duplicates(subset=["ticker", "url"], keep="first")
    combined = combined.drop_duplicates(subset=["ticker", "article_id"], keep="first")
    combined = combined.sort_values(["ticker", "published_at"]).reset_index(drop=True)
    combined.to_parquet(OUT_FILE, index=False)

    added = len(combined) - before
    logger.info("Saved %s articles (+%s GDELT) → %s", len(combined), added, OUT_FILE)
    print(f"Saved {len(combined)} articles to {OUT_FILE} (added ~{max(added, 0)} new)")
    print(gdelt.groupby("ticker").size().to_string())


if __name__ == "__main__":
    main()
