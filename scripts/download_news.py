"""Download company news from Finnhub (free tier) into data/raw/news/."""

from datetime import date, timedelta
from pathlib import Path
import json
import logging
import os
import time

import requests
import yaml
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
UNIVERSE_FILE = BASE_DIR / "config" / "universe.yaml"
NEWS_DIR = BASE_DIR / "data" / "raw" / "news"
LOG_DIR = BASE_DIR / "logs"
LOG_FILE = LOG_DIR / "download_news.log"
URL = "https://finnhub.io/api/v1/company-news"

# Free tier: keep the window modest; adjust if Finnhub rejects the range.
LOOKBACK_DAYS = 365
SLEEP_SECONDS = 1.0  # be gentle on free-tier rate limits

LOG_DIR.mkdir(parents=True, exist_ok=True)
NEWS_DIR.mkdir(parents=True, exist_ok=True)

logging.basicConfig(
    filename=LOG_FILE,
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

load_dotenv(BASE_DIR / ".env")

API_KEY = os.getenv("FINNHUB_API_KEY")
if not API_KEY:
    raise SystemExit("Set FINNHUB_API_KEY in .env")

with open(UNIVERSE_FILE) as f:
    universe = yaml.safe_load(f)
TICKERS = universe["tickers"]  # equity only; skip SPY benchmark


def download_ticker_news(ticker: str, start: date, end: date) -> list:
    response = requests.get(
        URL,
        params={
            "symbol": ticker,
            "from": start.isoformat(),
            "to": end.isoformat(),
            "token": API_KEY,
        },
        timeout=30,
    )
    response.raise_for_status()
    payload = response.json()
    if not isinstance(payload, list):
        raise ValueError(f"Unexpected response for {ticker}: {payload!r}")
    return payload


def main() -> None:
    end = date.today()
    start = end - timedelta(days=LOOKBACK_DAYS)
    ok = 0
    fail = 0

    for ticker in TICKERS:
        out_path = NEWS_DIR / f"{ticker}.json"
        try:
            articles = download_ticker_news(ticker, start, end)
            out_path.write_text(json.dumps(articles, indent=2))
            logger.info("OK %s (%d articles) %s → %s", ticker, len(articles), start, end)
            print(f"OK {ticker}: {len(articles)} articles")
            ok += 1
        except (requests.RequestException, ValueError, OSError) as e:
            logger.exception("FAIL %s: %s", ticker, e)
            print(f"FAIL {ticker}: {e}")
            fail += 1
        time.sleep(SLEEP_SECONDS)

    print(f"Done. ok={ok} fail={fail} → {NEWS_DIR}")
    if fail:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
