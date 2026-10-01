from pathlib import Path
import pandas as pd
import logging

BASE_DIR = Path(__file__).resolve().parent.parent
LOG_DIR = BASE_DIR / "logs"
LOG_FILE = LOG_DIR / "build_labels.log"
LOG_DIR.mkdir(parents=True, exist_ok=True)

logging.basicConfig(
    filename=LOG_FILE,
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


def build_labels(prices: pd.DataFrame) -> pd.DataFrame:

    prices = prices.sort_values(["ticker", "date"])
    prices["fwd_ret"] = (
        prices.groupby("ticker")["close"].shift(-30) / prices["close"] - 1
    )

    spy = (
        prices.loc[prices["ticker"] == "SPY", ["date", "fwd_ret"]]
        .rename(columns={"fwd_ret": "spy_fwd_ret"})
)

    stocks = prices.loc[prices["ticker"] != "SPY"].copy()
    out = stocks.merge(spy, on="date", how="inner")

    out["excess_ret"] = out["fwd_ret"] - out["spy_fwd_ret"]
    out["label"] = (out["excess_ret"] > 0).map({True: "up", False: "down"})

    n_before = len(out)
    out = out.dropna(subset=["fwd_ret", "spy_fwd_ret"])
    n_after = len(out)
    logger.info(
        "Labels: %s rows before dropna, dropped %s NaN rows, %s remaining",
        n_before,
        n_before - n_after,
        n_after,
    )
    return out[["ticker", "date", "fwd_ret", "spy_fwd_ret", "excess_ret", "label"]]


def main():
    prices = pd.read_parquet(BASE_DIR / "data" / "processed" / "prices.parquet")
    prices["date"] = pd.to_datetime(prices["date"])
    labels = build_labels(prices)
    out = BASE_DIR / "data" / "processed" / "labels.parquet"
    labels.to_parquet(out, index=False)
    logger.info("Saved %s rows to %s | %s", len(labels), out, labels["label"].value_counts().to_dict())

if __name__ == "__main__":
    main()