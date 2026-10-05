"""CLI: retrieve PIT news → LLM → validated Forecast."""

from __future__ import annotations

import argparse
import logging
from pathlib import Path

from sentence_transformers import SentenceTransformer

from stock_intelligence.agent.forecast import run_forecast
from stock_intelligence.rag.retrieve_news import retrieve_news

BASE_DIR = Path(__file__).resolve().parent.parent
LOG_DIR = BASE_DIR / "logs"
LOG_FILE = LOG_DIR / "run_forecast.log"
EMBED_MODEL = "BAAI/bge-small-en-v1.5"

LOG_DIR.mkdir(parents=True, exist_ok=True)
logging.basicConfig(
    filename=LOG_FILE,
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


def main() -> None:
    parser = argparse.ArgumentParser(description="Run a point-in-time LLM forecast")
    parser.add_argument("--ticker", default="AAPL")
    parser.add_argument("--date", required=True, help="Forecast date (YYYY-MM-DD)")
    parser.add_argument("--k", type=int, default=5, help="News top-k")
    parser.add_argument(
        "--query",
        default=None,
        help="Retrieval query (default: '{ticker} company news earnings')",
    )
    args = parser.parse_args()

    query = args.query or f"{args.ticker} company news earnings"
    logger.info("run_forecast ticker=%s date=%s k=%s", args.ticker, args.date, args.k)

    embedder = SentenceTransformer(EMBED_MODEL)
    news_df = retrieve_news(
        model=embedder,
        ticker=args.ticker,
        query=query,
        current_date=args.date,
        top_k=args.k,
    )
    print(f"Retrieved {len(news_df)} news articles (published_at < {args.date})")

    forecast = run_forecast(args.ticker, args.date, news_df)
    logger.info("forecast=%s", forecast.model_dump())
    print(forecast.model_dump_json(indent=2))


if __name__ == "__main__":
    main()
