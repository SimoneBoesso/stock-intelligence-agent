"""Resolve forward-test forecasts once 30d labels exist for forecast_date.

Reads/writes data/processed/forward_forecasts.parquet.
Requires up-to-date labels: download_prices → transform → build_labels.
"""

from __future__ import annotations

import argparse
import logging
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

BASE_DIR = Path(__file__).resolve().parent.parent
FORECASTS_FILE = BASE_DIR / "data" / "processed" / "forward_forecasts.parquet"
LABELS_FILE = BASE_DIR / "data" / "processed" / "labels.parquet"
LOG_DIR = BASE_DIR / "logs"
LOG_FILE = LOG_DIR / "forward_resolve.log"

LOG_DIR.mkdir(parents=True, exist_ok=True)
logging.basicConfig(
    filename=LOG_FILE,
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


def main() -> None:
    parser = argparse.ArgumentParser(description="Resolve forward forecasts against labels")
    parser.add_argument(
        "--re-resolve",
        action="store_true",
        help="Also refresh rows that already have a label",
    )
    args = parser.parse_args()

    if not FORECASTS_FILE.exists():
        raise SystemExit(f"Missing {FORECASTS_FILE}. Run scripts/forward_log.py first.")
    if not LABELS_FILE.exists():
        raise SystemExit(f"Missing {LABELS_FILE}. Run scripts/build_labels.py first.")

    forecasts = pd.read_parquet(FORECASTS_FILE).copy()
    labels = pd.read_parquet(LABELS_FILE).copy()
    labels["date"] = pd.to_datetime(labels["date"]).dt.strftime("%Y-%m-%d")
    lab_map = labels.set_index(["ticker", "date"])["label"]

    now = datetime.now(timezone.utc).isoformat()
    resolved = 0
    still_open = 0
    labels_out: list = []
    correct_out: list = []
    resolved_out: list = []

    for _, row in forecasts.iterrows():
        already = pd.notna(row.get("label"))
        if already and not args.re_resolve:
            labels_out.append(row["label"])
            correct_out.append(row["correct"])
            resolved_out.append(row.get("resolved_at_utc"))
            continue

        key = (row["ticker"], row["forecast_date"])
        if key in lab_map.index:
            true_label = lab_map.loc[key]
            if isinstance(true_label, pd.Series):
                true_label = true_label.iloc[0]
            labels_out.append(true_label)
            correct_out.append(bool(row["pred"] == true_label))
            resolved_out.append(now)
            resolved += 1
        else:
            labels_out.append(pd.NA)
            correct_out.append(pd.NA)
            resolved_out.append(pd.NA)
            still_open += 1

    forecasts["label"] = labels_out
    forecasts["correct"] = correct_out
    forecasts["resolved_at_utc"] = resolved_out
    forecasts.to_parquet(FORECASTS_FILE, index=False)

    print(f"Resolved {resolved} rows; still open {still_open} → {FORECASTS_FILE}")
    logger.info("resolved=%s open=%s", resolved, still_open)
    _print_summary(forecasts)


def _print_summary(forecasts: pd.DataFrame) -> None:
    done = forecasts[forecasts["label"].notna()]
    open_n = int(forecasts["label"].isna().sum())
    print(f"Track record: resolved={len(done)} open={open_n}")
    if done.empty:
        return
    hit = float(done["correct"].astype(bool).mean())
    print(f"Hit rate (resolved): {hit:.3f}")
    print(
        done.assign(correct=done["correct"].astype(bool))
        .groupby("ticker")["correct"]
        .agg(["count", "mean"])
        .to_string()
    )


if __name__ == "__main__":
    main()
