import pandas as pd
from pathlib import Path
import logging

BASE_DIR = Path(__file__).resolve().parent.parent
LOG_DIR = BASE_DIR / "logs"
LOG_FILE = LOG_DIR / "build_features.log"
LOG_DIR.mkdir(parents=True, exist_ok=True)

logging.basicConfig(
    filename=LOG_FILE,
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

def build_features(prices: pd.DataFrame, time_intervals: list[int]) -> pd.DataFrame:
    prices.sort_values(["ticker", "date"], inplace=True)
    for interval in time_intervals:
        prices[f"ret_{interval}d"] = (
            prices.groupby("ticker")["close"].pct_change(interval)
        )
    # takes 21 days from the current day to compute the volatility
    prices["vol_21d"] = prices.groupby("ticker")["ret_1d"].rolling(21).std().reset_index(level=0, drop=True)
    
    cols = ["ticker", "date", "ret_1d", "ret_5d", "ret_21d", "vol_21d"]
    out = prices[cols].dropna()
    return out

def main():
    prices = pd.read_parquet(BASE_DIR / "data" / "processed" / "prices.parquet")
    features = build_features(prices, [1, 5, 21])
    out = BASE_DIR / "data" / "processed" / "features.parquet"
    features.to_parquet(out, index=False)
    logger.info("Saved %s rows to %s", len(features), out)

if __name__ == "__main__":
    main()