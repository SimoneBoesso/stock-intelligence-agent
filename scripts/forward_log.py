"""Forward-test job: emit PIT LLM+RAG forecasts for today (no labels yet).

Appends to data/processed/forward_forecasts.parquet.
Idempotent per (ticker, forecast_date): skips rows that already exist.
Resolve outcomes later with scripts/forward_resolve.py (~30 trading days).
"""

from __future__ import annotations

import argparse
import json
import logging
import time
from datetime import date, datetime, timezone
from pathlib import Path

import pandas as pd
import yaml
from sentence_transformers import SentenceTransformer

from stock_intelligence.agent.forecast import run_forecast
from stock_intelligence.experiments.log import new_run_id
from stock_intelligence.llm import call as llm_call
from stock_intelligence.rag.retrieve_news import retrieve_news

BASE_DIR = Path(__file__).resolve().parent.parent
UNIVERSE_FILE = BASE_DIR / "config" / "universe.yaml"
OUT_FILE = BASE_DIR / "data" / "processed" / "forward_forecasts.parquet"
LOG_DIR = BASE_DIR / "logs"
LOG_FILE = LOG_DIR / "forward_log.log"
EMBED_MODEL = "BAAI/bge-small-en-v1.5"
LLM_MODEL = getattr(llm_call, "MODEL_NAME", "openai/gpt-oss-20b")

LOG_DIR.mkdir(parents=True, exist_ok=True)
OUT_FILE.parent.mkdir(parents=True, exist_ok=True)
logging.basicConfig(
    filename=LOG_FILE,
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


def load_existing() -> pd.DataFrame:
    if not OUT_FILE.exists():
        return pd.DataFrame()
    return pd.read_parquet(OUT_FILE)


def already_logged(existing: pd.DataFrame, ticker: str, forecast_date: str) -> bool:
    if existing.empty:
        return False
    return (
        (existing["ticker"] == ticker) & (existing["forecast_date"] == forecast_date)
    ).any()


def main() -> None:
    parser = argparse.ArgumentParser(description="Log forward-test forecasts (no labels)")
    parser.add_argument("--date", default=None, help="Forecast date YYYY-MM-DD (default: today UTC)")
    parser.add_argument("--ticker", help="Single ticker (default: full universe)")
    parser.add_argument("--k", type=int, default=5)
    parser.add_argument("--sleep", type=float, default=1.0)
    parser.add_argument(
        "--force",
        action="store_true",
        help="Re-run even if (ticker, date) already logged",
    )
    args = parser.parse_args()

    forecast_date = args.date or date.today().isoformat()
    with open(UNIVERSE_FILE) as f:
        universe = yaml.safe_load(f)
    tickers = [args.ticker] if args.ticker else list(universe["tickers"])

    run_id = new_run_id()
    existing = load_existing()
    embedder = SentenceTransformer(EMBED_MODEL)
    new_rows: list[dict] = []

    print(f"run_id={run_id} forecast_date={forecast_date} tickers={len(tickers)}")

    for i, ticker in enumerate(tickers):
        if not args.force and already_logged(existing, ticker, forecast_date):
            print(f"SKIP {ticker}: already logged for {forecast_date}")
            continue
        try:
            if i and new_rows:
                time.sleep(args.sleep)
            query = f"{ticker} company news earnings"
            news_df = retrieve_news(
                model=embedder,
                ticker=ticker,
                query=query,
                current_date=forecast_date,
                top_k=args.k,
            )
            forecast = run_forecast(ticker, forecast_date, news_df)
            row = {
                "run_id": run_id,
                "logged_at_utc": datetime.now(timezone.utc).isoformat(),
                "ticker": ticker,
                "forecast_date": forecast_date,
                "pred": forecast.direction.value,
                "confidence": float(forecast.confidence),
                "rationale": forecast.rationale,
                "sources": json.dumps(forecast.sources),
                "n_news": int(len(news_df)),
                "embed_model": EMBED_MODEL,
                "llm_model": LLM_MODEL,
                "k": args.k,
                "label": pd.NA,
                "correct": pd.NA,
                "resolved_at_utc": pd.NA,
            }
            new_rows.append(row)
            print(
                f"OK {ticker}: pred={row['pred']} conf={row['confidence']:.2f} n_news={row['n_news']}"
            )
            logger.info("OK %s %s pred=%s", ticker, forecast_date, row["pred"])
        except Exception as e:
            logger.exception("FAIL %s: %s", ticker, e)
            print(f"FAIL {ticker}: {e}")

    if not new_rows:
        print(f"No new rows. Registry → {OUT_FILE}")
        return

    add = pd.DataFrame(new_rows)
    if args.force and not existing.empty:
        # drop prior rows for same (ticker, forecast_date) then append
        keyset = set(zip(add["ticker"], add["forecast_date"]))
        keep = existing[
            ~existing.apply(lambda r: (r["ticker"], r["forecast_date"]) in keyset, axis=1)
        ]
        out = pd.concat([keep, add], ignore_index=True)
    elif existing.empty:
        out = add
    else:
        out = pd.concat([existing, add], ignore_index=True)

    out.to_parquet(OUT_FILE, index=False)
    print(f"Saved {len(add)} new forecasts (total {len(out)}) → {OUT_FILE}")
    print("Resolve later: python scripts/forward_resolve.py")


if __name__ == "__main__":
    main()
