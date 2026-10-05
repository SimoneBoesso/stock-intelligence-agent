"""Phase 4 smoke eval on eval_sample.parquet (tiny n — not statistically meaningful)."""

from __future__ import annotations

import argparse
import logging
import time
from pathlib import Path

import numpy as np
import pandas as pd
from sentence_transformers import SentenceTransformer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

from stock_intelligence.agent.forecast import run_forecast
from stock_intelligence.experiments.log import log_experiment, new_run_id
from stock_intelligence.rag.retrieve_news import retrieve_news
from stock_intelligence.llm import call as llm_call

BASE_DIR = Path(__file__).resolve().parent.parent
SAMPLE_FILE = BASE_DIR / "data" / "processed" / "eval_sample.parquet"
FEATURES_FILE = BASE_DIR / "data" / "processed" / "features.parquet"
LABELS_FILE = BASE_DIR / "data" / "processed" / "labels.parquet"
PREDS_DIR = BASE_DIR / "data" / "processed" / "experiments"
LOG_DIR = BASE_DIR / "logs"
LOG_FILE = LOG_DIR / "eval_smoke.log"
EMBED_MODEL = "BAAI/bge-small-en-v1.5"
FEATURE_COLS = ["ret_1d", "ret_5d", "ret_21d", "vol_21d"]
SPLIT_DATE = "2023-01-01"
# Best-effort: read model name from call.py constant if present later
LLM_MODEL = getattr(llm_call, "MODEL_NAME", "openai/gpt-oss-20b")

LOG_DIR.mkdir(parents=True, exist_ok=True)
logging.basicConfig(
    filename=LOG_FILE,
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


def hit_rate(y_true: pd.Series, y_pred: pd.Series | np.ndarray) -> float:
    return float((np.asarray(y_pred) == y_true.to_numpy()).mean())


def naive_hits(sample: pd.DataFrame) -> dict[str, float]:
    y = sample["label"]
    rng = np.random.default_rng(42)
    random_pred = rng.choice(["up", "down"], size=len(y))
    return {
        "always_up": hit_rate(y, np.array(["up"] * len(y))),
        "always_down": hit_rate(y, np.array(["down"] * len(y))),
        "random": hit_rate(y, random_pred),
    }


def metrics_logreg_hits(sample: pd.DataFrame) -> float | None:
    labels = pd.read_parquet(LABELS_FILE)
    features = pd.read_parquet(FEATURES_FILE)
    labels["date"] = pd.to_datetime(labels["date"])
    features["date"] = pd.to_datetime(features["date"])
    sample = sample.copy()
    sample["date"] = pd.to_datetime(sample["date"])

    train = labels.merge(features, on=["ticker", "date"], how="inner")
    train = train[train["date"] < pd.Timestamp(SPLIT_DATE)]
    if train.empty:
        return None

    pipe = Pipeline(
        [
            ("scaler", StandardScaler()),
            ("clf", LogisticRegression(max_iter=1000)),
        ]
    )
    pipe.fit(train[FEATURE_COLS], train["label"])

    scored = sample.merge(features, on=["ticker", "date"], how="inner")
    if scored.empty or scored[FEATURE_COLS].isna().any().any():
        return None
    pred = pipe.predict(scored[FEATURE_COLS])
    return hit_rate(scored["label"], pred)


def run_llm_rag(sample: pd.DataFrame, *, k: int, sleep_s: float) -> pd.DataFrame:
    embedder = SentenceTransformer(EMBED_MODEL)
    rows = []
    for _, row in sample.iterrows():
        ticker = row["ticker"]
        date = pd.Timestamp(row["date"]).strftime("%Y-%m-%d")
        query = f"{ticker} company news earnings"
        news_df = retrieve_news(
            model=embedder,
            ticker=ticker,
            query=query,
            current_date=date,
            top_k=k,
        )
        forecast = run_forecast(ticker, date, news_df)
        rows.append(
            {
                "ticker": ticker,
                "date": row["date"],
                "label": row["label"],
                "pred": forecast.direction.value,
                "confidence": forecast.confidence,
                "n_news": len(news_df),
                "rationale": forecast.rationale,
            }
        )
        logger.info("LLM+RAG %s %s pred=%s label=%s", ticker, date, forecast.direction, row["label"])
        time.sleep(sleep_s)
    return pd.DataFrame(rows)


def main() -> None:
    parser = argparse.ArgumentParser(description="Smoke eval on eval_sample.parquet")
    parser.add_argument("--k", type=int, default=5)
    parser.add_argument("--sleep", type=float, default=1.0)
    parser.add_argument("--skip-llm", action="store_true")
    parser.add_argument("--notes", default="", help="Free-text note stored in experiment log")
    args = parser.parse_args()

    if not SAMPLE_FILE.exists():
        raise SystemExit(f"Missing {SAMPLE_FILE}. Run scripts/build_eval_samples.py first.")

    run_id = new_run_id()
    PREDS_DIR.mkdir(parents=True, exist_ok=True)
    preds_path: Path | None = None

    sample = pd.read_parquet(SAMPLE_FILE)
    print(f"run_id={run_id}")
    print(f"Sample n={len(sample)} (smoke only — not statistically meaningful)")
    print(sample[["ticker", "date", "label"]].to_string(index=False))
    print()

    hits = naive_hits(sample)
    ml_hit = metrics_logreg_hits(sample)
    if ml_hit is not None:
        hits["metrics_logreg"] = ml_hit

    if not args.skip_llm:
        llm_df = run_llm_rag(sample, k=args.k, sleep_s=args.sleep)
        preds_path = PREDS_DIR / f"{run_id}_preds.parquet"
        llm_df.to_parquet(preds_path, index=False)
        hits["llm_rag"] = hit_rate(llm_df["label"], llm_df["pred"])
        print("LLM+RAG predictions:")
        print(llm_df[["ticker", "date", "label", "pred", "confidence", "n_news"]].to_string(index=False))
        print()

    print("Hit rates:")
    for name, value in hits.items():
        print(f"  {name:16s} {value:.3f}")

    registry = log_experiment(
        run_id=run_id,
        kind="smoke_eval",
        n=len(sample),
        metrics=hits,
        sample_path=str(SAMPLE_FILE),
        preds_path=str(preds_path) if preds_path else None,
        notes=args.notes or "Phase 4 smoke eval; tiny n",
        extra={
            "embed_model": EMBED_MODEL,
            "llm_model": LLM_MODEL,
            "k": args.k,
            "skip_llm": args.skip_llm,
        },
    )
    print(f"Logged experiment → {registry}")
    logger.info("run_id=%s hits=%s n=%s", run_id, hits, len(sample))


if __name__ == "__main__":
    main()
