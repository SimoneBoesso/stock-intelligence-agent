"""Summarize forward-test track record from forward_forecasts.parquet.

Safe to run daily (e.g. after forward_resolve): read-only on the registry.
"""

from __future__ import annotations

import argparse
import logging
from pathlib import Path

import pandas as pd

BASE_DIR = Path(__file__).resolve().parent.parent
FORECASTS_FILE = BASE_DIR / "data" / "processed" / "forward_forecasts.parquet"
LOG_DIR = BASE_DIR / "logs"
LOG_FILE = LOG_DIR / "forward_report.log"

LOG_DIR.mkdir(parents=True, exist_ok=True)
logging.basicConfig(
    filename=LOG_FILE,
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


def summarize(forecasts: pd.DataFrame) -> dict[str, float | int]:
    n_total = len(forecasts)
    done = forecasts[forecasts["label"].notna()]
    n_resolved = int(len(done))
    n_open = n_total - n_resolved
    out: dict[str, float | int] = {
        "n_total": n_total,
        "n_resolved": n_resolved,
        "n_open": n_open,
    }
    if n_resolved:
        out["hit_rate"] = float(done["correct"].astype(bool).mean())
    return out


def main() -> None:
    parser = argparse.ArgumentParser(description="Forward-test track record summary")
    parser.add_argument(
        "--by-ticker",
        action="store_true",
        help="Print per-ticker hit rate for resolved rows",
    )
    args = parser.parse_args()

    if not FORECASTS_FILE.exists():
        print(f"No registry yet ({FORECASTS_FILE}). Run scripts/forward_log.py first.")
        return

    forecasts = pd.read_parquet(FORECASTS_FILE)
    metrics = summarize(forecasts)
    logger.info("forward_report %s", metrics)

    print(f"Forward track record → {FORECASTS_FILE}")
    print(f"  n_total={metrics['n_total']} n_resolved={metrics['n_resolved']} n_open={metrics['n_open']}")
    if metrics["n_resolved"]:
        print(f"  hit_rate={metrics['hit_rate']:.3f}")
    else:
        print("  hit_rate=n/a (no resolved rows yet)")

    if args.by_ticker and metrics["n_resolved"]:
        done = forecasts[forecasts["label"].notna()].copy()
        done["correct"] = done["correct"].astype(bool)
        print()
        print(
            done.groupby("ticker")["correct"]
            .agg(["count", "mean"])
            .rename(columns={"count": "n", "mean": "hit_rate"})
            .to_string()
        )


if __name__ == "__main__":
    main()
