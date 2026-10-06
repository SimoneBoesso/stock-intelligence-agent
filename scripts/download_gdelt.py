"""Download company news from GDELT DOC 2.0 API into data/raw/news_gdelt/.

Free, no API key. Official rolling window ~3 months; max 250 records per call.
Default: one request per ticker (timespan) to stay under rate limits.
Use ``--start``/``--end`` for a calendar window (e.g. August for label overlap).
Optional ``--chunk-days`` splits a lookback/window into chunks for >250 hits/ticker.
Existing per-ticker JSON is merged by URL (idempotent re-runs).
"""

from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from pathlib import Path
import argparse
import json
import logging
import time

import requests
import yaml

BASE_DIR = Path(__file__).resolve().parent.parent
UNIVERSE_FILE = BASE_DIR / "config" / "universe.yaml"
OUT_DIR = BASE_DIR / "data" / "raw" / "news_gdelt"
LOG_DIR = BASE_DIR / "logs"
LOG_FILE = LOG_DIR / "download_gdelt.log"

URL = "https://api.gdeltproject.org/api/v2/doc/doc"
LOOKBACK_DAYS = 90
MAX_RECORDS = 250
# GDELT asks ~1 req / 5s; after 429 they stay hot for longer.
SLEEP_SECONDS = 15.0
MAX_RETRIES = 8

LOG_DIR.mkdir(parents=True, exist_ok=True)
OUT_DIR.mkdir(parents=True, exist_ok=True)

logging.basicConfig(
    filename=LOG_FILE,
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

with open(UNIVERSE_FILE) as f:
    universe = yaml.safe_load(f)
TICKERS: list[str] = universe["tickers"]
NAMES: dict[str, str] = universe["names"]


def _fmt(dt: datetime) -> str:
    return dt.strftime("%Y%m%d%H%M%S")


def _backoff(attempt: int) -> float:
    # 15, 30, 60, 120, ... capped at 180s
    return min(SLEEP_SECONDS * (2 ** (attempt - 1)), 180.0)


def _parse_ymd(value: str) -> date:
    return datetime.strptime(value, "%Y-%m-%d").date()


def fetch_artlist(query: str, extra_params: dict) -> list[dict]:
    params = {
        "query": query,
        "mode": "ArtList",
        "format": "json",
        "maxrecords": MAX_RECORDS,
        "sort": "DateDesc",
        **extra_params,
    }
    headers = {"User-Agent": "stock-intelligence-agent/0.1 (research)"}
    last_error: Exception | None = None

    for attempt in range(1, MAX_RETRIES + 1):
        try:
            response = requests.get(URL, params=params, headers=headers, timeout=60)
            text = response.text.strip()
            limited = response.status_code == 429 or text.startswith("Please limit requests")
            if limited:
                last_error = RuntimeError(f"GDELT rate limit (HTTP {response.status_code})")
                wait = _backoff(attempt)
                logger.warning("rate limit; sleep %.0fs (attempt %d/%d)", wait, attempt, MAX_RETRIES)
                print(f"  rate limit → sleep {wait:.0f}s (attempt {attempt}/{MAX_RETRIES})")
                time.sleep(wait)
                continue

            response.raise_for_status()
            if not text:
                return []
            payload = response.json()
            articles = payload.get("articles", []) if isinstance(payload, dict) else []
            if not isinstance(articles, list):
                raise ValueError(f"Unexpected GDELT payload: {payload!r}")
            return articles
        except (requests.RequestException, ValueError) as e:
            last_error = e
            wait = _backoff(attempt)
            logger.warning("request error %s; sleep %.0fs", e, wait)
            time.sleep(wait)

    raise RuntimeError(f"GDELT fetch failed after {MAX_RETRIES} retries: {last_error}")


def _collect_range(
    query: str,
    start: date,
    end: date,
    chunk_days: int | None,
    ticker: str,
) -> dict[str, dict]:
    by_url: dict[str, dict] = {}
    if chunk_days is None:
        chunk_start = datetime.combine(start, datetime.min.time(), tzinfo=timezone.utc)
        chunk_end = datetime.combine(end, datetime.max.time(), tzinfo=timezone.utc)
        articles = fetch_artlist(
            query,
            {
                "startdatetime": _fmt(chunk_start),
                "enddatetime": _fmt(chunk_end),
            },
        )
        for article in articles:
            url = article.get("url")
            if url:
                by_url[url] = article
        logger.info("%s range %s→%s: %d hits", ticker, start, end, len(by_url))
        return by_url

    chunk_start = datetime.combine(start, datetime.min.time(), tzinfo=timezone.utc)
    end_dt = datetime.combine(end, datetime.max.time(), tzinfo=timezone.utc)
    while chunk_start < end_dt:
        chunk_end = min(chunk_start + timedelta(days=chunk_days), end_dt)
        articles = fetch_artlist(
            query,
            {
                "startdatetime": _fmt(chunk_start),
                "enddatetime": _fmt(chunk_end),
            },
        )
        for article in articles:
            url = article.get("url")
            if url:
                by_url[url] = article
        logger.info(
            "%s chunk %s→%s: %d hits (unique %d)",
            ticker,
            chunk_start.date(),
            chunk_end.date(),
            len(articles),
            len(by_url),
        )
        time.sleep(SLEEP_SECONDS)
        chunk_start = chunk_end
    return by_url


def download_ticker(
    ticker: str,
    name: str,
    *,
    days: int,
    chunk_days: int | None,
    start: date | None,
    end: date | None,
) -> list[dict]:
    query = f'"{name}" sourcelang:english'

    if start is not None and end is not None:
        by_url = _collect_range(query, start, end, chunk_days, ticker)
        return list(by_url.values())

    if chunk_days is None:
        by_url: dict[str, dict] = {}
        articles = fetch_artlist(query, {"timespan": f"{days}d"})
        for article in articles:
            url = article.get("url")
            if url:
                by_url[url] = article
        logger.info("%s timespan=%sd: %d hits", ticker, days, len(by_url))
        return list(by_url.values())

    end_d = date.today()
    start_d = end_d - timedelta(days=days)
    return list(_collect_range(query, start_d, end_d, chunk_days, ticker).values())


def load_existing(path: Path) -> dict[str, dict]:
    if not path.exists():
        return {}
    try:
        payload = json.loads(path.read_text())
    except (OSError, json.JSONDecodeError) as e:
        logger.warning("Could not read %s (%s); starting fresh", path, e)
        return {}
    if not isinstance(payload, list):
        return {}
    by_url: dict[str, dict] = {}
    for article in payload:
        if isinstance(article, dict):
            url = article.get("url")
            if url:
                by_url[url] = article
    return by_url


def merge_and_save(path: Path, new_articles: list[dict]) -> tuple[int, int]:
    """Merge by URL into existing JSON. Returns (total, newly_added)."""
    by_url = load_existing(path)
    before = len(by_url)
    for article in new_articles:
        url = article.get("url")
        if url:
            by_url[url] = article
    path.write_text(json.dumps(list(by_url.values()), indent=2))
    return len(by_url), len(by_url) - before


def main() -> None:
    parser = argparse.ArgumentParser(description="Download GDELT DOC ArtList news")
    parser.add_argument("--ticker", help="Single ticker (default: full universe)")
    parser.add_argument("--days", type=int, default=LOOKBACK_DAYS, help="Lookback days")
    parser.add_argument("--start", help="Window start YYYY-MM-DD (with --end)")
    parser.add_argument("--end", help="Window end YYYY-MM-DD (with --start)")
    parser.add_argument(
        "--chunk-days",
        type=int,
        default=None,
        help="If set, split window/lookback into chunks (more requests)",
    )
    args = parser.parse_args()

    start: date | None = None
    end: date | None = None
    if args.start or args.end:
        if not (args.start and args.end):
            raise SystemExit("Provide both --start and --end (YYYY-MM-DD)")
        start = _parse_ymd(args.start)
        end = _parse_ymd(args.end)
        if end < start:
            raise SystemExit("--end must be >= --start")

    tickers = [args.ticker] if args.ticker else TICKERS
    missing = [t for t in tickers if t not in NAMES]
    if missing:
        raise SystemExit(f"Missing names in universe.yaml for: {missing}")

    ok = 0
    fail = 0
    for i, ticker in enumerate(tickers):
        out_path = OUT_DIR / f"{ticker}.json"
        try:
            if i:
                time.sleep(SLEEP_SECONDS)
            articles = download_ticker(
                ticker,
                NAMES[ticker],
                days=args.days,
                chunk_days=args.chunk_days,
                start=start,
                end=end,
            )
            total, added = merge_and_save(out_path, articles)
            logger.info("OK %s (fetched %d, +%d new, total %d)", ticker, len(articles), added, total)
            print(f"OK {ticker}: fetched {len(articles)}, +{added} new, total {total}")
            ok += 1
        except (requests.RequestException, ValueError, RuntimeError, OSError) as e:
            logger.exception("FAIL %s: %s", ticker, e)
            print(f"FAIL {ticker}: {e}")
            fail += 1
            time.sleep(_backoff(3))

    print(f"Done. ok={ok} fail={fail} → {OUT_DIR}")
    if fail:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
