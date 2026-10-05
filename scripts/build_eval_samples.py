"""Build a small eval sample: (ticker, date, label) with prior news available.
We keep rows where at least ``min_news`` articles exist with published_at < date.
"""

from __future__ import annotations

import argparse
import logging
from pathlib import Path

import pandas as pd

BASE_DIR = Path(__file__).resolve().parent.parent
LABELS_FILE = BASE_DIR / "data" / "processed" / "labels.parquet"
NEWS_FILE = BASE_DIR / "data" / "processed" / "news.parquet"
OUT_FILE = BASE_DIR / "data" / "processed" / "eval_sample.parquet"
LOG_DIR = BASE_DIR / "logs"
LOG_FILE = LOG_DIR / "build_eval_samples.log"

LOG_DIR.mkdir(parents=True, exist_ok=True)
logging.basicConfig(
    filename=LOG_FILE,
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


def rows_with_prior_news(
    labels: pd.DataFrame,
    news: pd.DataFrame,
    *,
    min_news: int,
) -> pd.DataFrame:
    """Keep label rows that have enough point-in-time news for that ticker."""
    news = news.copy()
    news["published_at"] = pd.to_datetime(news["published_at"], utc=True)
    labels = labels.copy()
    labels["date"] = pd.to_datetime(labels["date"])

    # Restrict to the calendar window where news exists at all.
    news_start = news["published_at"].min().tz_convert("UTC").tz_localize(None).normalize()
    news_end = news["published_at"].max().tz_convert("UTC").tz_localize(None).normalize()
    candidates = labels[
        (labels["date"] > news_start) & (labels["date"] <= news_end + pd.Timedelta(days=1))
    ].copy()

    kept: list[pd.DataFrame] = []
    for ticker, grp in candidates.groupby("ticker", sort=False):
        t_news = news.loc[news["ticker"] == ticker, "published_at"]
        if t_news.empty:
            continue
        # For each forecast date, count news strictly before that date (UTC midnight).
        dates = grp["date"].sort_values().unique()
        counts = []
        for d in dates:
            cutoff = pd.Timestamp(d, tz="UTC")
            counts.append((d, int((t_news < cutoff).sum())))
        count_df = pd.DataFrame(counts, columns=["date", "n_prior_news"])
        merged = grp.merge(count_df, on="date", how="left")
        kept.append(merged.loc[merged["n_prior_news"] >= min_news])

    if not kept:
        return pd.DataFrame(columns=["ticker", "date", "label", "n_prior_news"])
    return pd.concat(kept, ignore_index=True)


def sample_rows(pool: pd.DataFrame, *, n_per_ticker: int, seed: int) -> pd.DataFrame:
    parts = []
    for ticker, grp in pool.groupby("ticker", sort=True):
        take = min(n_per_ticker, len(grp))
        parts.append(grp.sample(n=take, random_state=seed))
    out = pd.concat(parts, ignore_index=True)
    return out.sort_values(["date", "ticker"]).reset_index(drop=True)


def main() -> None:
    parser = argparse.ArgumentParser(description="Build eval sample for Phase 4")
    parser.add_argument("--n-per-ticker", type=int, default=2)
    parser.add_argument("--min-news", type=int, default=1)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--max-total", type=int, default=40)
    args = parser.parse_args()

    labels = pd.read_parquet(LABELS_FILE)
    news = pd.read_parquet(NEWS_FILE)

    pool = rows_with_prior_news(labels, news, min_news=args.min_news)
    logger.info("Eligible rows with prior news: %s", len(pool))
    if pool.empty:
        raise SystemExit(
            "No (ticker, date) with labels and prior news. "
            "Extend news history or rebuild labels with a shorter horizon."
        )

    sample = sample_rows(pool, n_per_ticker=args.n_per_ticker, seed=args.seed)
    if len(sample) > args.max_total:
        sample = sample.sample(n=args.max_total, random_state=args.seed).sort_values(
            ["date", "ticker"]
        ).reset_index(drop=True)

    out = sample[["ticker", "date", "label", "n_prior_news"]].copy()
    # Keep excess_ret if present (useful later for IC)
    if "excess_ret" in sample.columns:
        out["excess_ret"] = sample["excess_ret"]

    out.to_parquet(OUT_FILE, index=False)
    logger.info("Wrote %s rows → %s", len(out), OUT_FILE)
    print(f"Wrote {len(out)} rows → {OUT_FILE}")
    print(out.groupby("ticker").size().to_string())
    print("date range:", out["date"].min(), "→", out["date"].max())
    print("label counts:", out["label"].value_counts().to_dict())


if __name__ == "__main__":
    main()
