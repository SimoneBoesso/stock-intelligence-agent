"""Point-in-time filter tests — the most important tests in the project."""

from __future__ import annotations

from pathlib import Path

import lancedb
import numpy as np
import pandas as pd
import pytest
from sentence_transformers import SentenceTransformer

from stock_intelligence.rag import retrieve_news as retrieve_mod

MODEL_NAME = "BAAI/bge-small-en-v1.5"


@pytest.fixture(scope="module")
def embedder() -> SentenceTransformer:
    return SentenceTransformer(MODEL_NAME)


@pytest.fixture()
def tiny_news_index(tmp_path: Path, embedder: SentenceTransformer, monkeypatch: pytest.MonkeyPatch) -> Path:
    texts = [
        "Apple released a new iPhone before the cutoff date.",
        "Apple announced quarterly results after the cutoff date.",
    ]
    vectors = embedder.encode(texts, normalize_embeddings=True)

    table_df = pd.DataFrame(
        {
            "vector": list(np.asarray(vectors)),
            "text": texts,
            "ticker": ["AAPL", "AAPL"],
            "published_at": [
                "2026-09-01 12:00:00+00:00",
                "2026-09-20 12:00:00+00:00",
            ],
            "article_id": [1, 2],
            "source": ["test", "test"],
            "url": ["http://example.com/1", "http://example.com/2"],
        }
    )

    index_dir = tmp_path / "news_lancedb"
    db = lancedb.connect(str(index_dir))
    db.create_table(retrieve_mod.TABLE_NAME, data=table_df, mode="overwrite")

    monkeypatch.setattr(retrieve_mod, "INDEX_DIR", index_dir)
    return index_dir


def test_retrieve_keeps_only_docs_before_forecast_date(tiny_news_index: Path, embedder: SentenceTransformer):
    hits = retrieve_mod.retrieve_news(
        model=embedder,
        ticker="AAPL",
        query="Apple iPhone announcement",
        current_date="2026-09-10",
        top_k=5,
    )

    assert len(hits) == 1
    assert int(hits.iloc[0]["article_id"]) == 1
    assert hits["published_at"].max() < pd.Timestamp("2026-09-10", tz="UTC")


def test_retrieve_returns_empty_if_all_docs_are_in_the_future(
    tiny_news_index: Path, embedder: SentenceTransformer
):
    hits = retrieve_mod.retrieve_news(
        model=embedder,
        ticker="AAPL",
        query="Apple iPhone announcement",
        current_date="2026-08-01",
        top_k=5,
    )
    assert hits.empty
