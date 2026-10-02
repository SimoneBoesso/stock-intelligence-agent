from __future__ import annotations

from datetime import date, datetime
from pathlib import Path

import lancedb
import logging
import pandas as pd
from sentence_transformers import SentenceTransformer

logger = logging.getLogger(__name__)

TABLE_NAME = "news"
INDEX_DIR = (
    Path(__file__).resolve().parents[3] / "data" / "indexes" / "news_lancedb"
)


def retrieve_news(
    model: SentenceTransformer,
    ticker: str,
    query: str,
    current_date: date | datetime | str,
    top_k: int = 10,
) -> pd.DataFrame:
    """Retrieve top-k news for ticker with point-in-time filter.

    Only documents with published_at < current_date are returned.
    """
    cutoff = pd.Timestamp(current_date)
    if cutoff.tzinfo is None:
        cutoff = cutoff.tz_localize("UTC")
    else:
        cutoff = cutoff.tz_convert("UTC")

    db = lancedb.connect(INDEX_DIR)
    table = db.open_table(TABLE_NAME)

    query_vector = model.encode(query, normalize_embeddings=True)

    results = (
        table.search(query_vector)
        .where(f"ticker = '{ticker}' AND published_at < '{cutoff.isoformat()}'")
        .limit(top_k)
        .to_pandas()
    )

    if results.empty:
        return results

    results["published_at"] = pd.to_datetime(results["published_at"], utc=True)
    results = results.loc[results["published_at"] < cutoff].reset_index(drop=True)
    logger.info(
        "retrieve_news ticker=%s cutoff=%s hits=%s",
        ticker,
        cutoff.isoformat(),
        len(results),
    )
    return results
