import pandas as pd
from pathlib import Path
import logging
from datetime import datetime, timezone

BASE_DIR = Path(__file__).resolve().parent.parent
RAW_DIR = BASE_DIR / "data" / "raw"
PRICES_DIR = RAW_DIR / "prices"
TRANSFORMED_DIR = BASE_DIR / "data" / "processed"
TRANSFORMED_FILE = TRANSFORMED_DIR / "prices.parquet"
LOG_DIR = BASE_DIR / "logs"
LOG_FILE = LOG_DIR / "transform.log"

TRANSFORMED_DIR.mkdir(parents=True, exist_ok=True)
LOG_DIR.mkdir(parents=True, exist_ok=True)

logging.basicConfig(filename=LOG_FILE, level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def transform_prices():
    future_df = []

    for file in PRICES_DIR.glob("*.parquet"):
        df = merge_prices(file)
        future_df.append(df)
    
    future_df = pd.concat(future_df)
    future_df["ingested_at"] = datetime.now(timezone.utc)

    future_df.to_parquet(TRANSFORMED_FILE)
        

def merge_prices(file: Path) -> pd.DataFrame:
    df = pd.read_parquet(file)
    df["date"] = df.index.date
    df = df.reset_index(drop=True)
    df["ticker"] = file.stem
    
    df.columns = df.columns.str.lower()

    df = df.dropna(subset = ["close"])
    return df


if __name__ == "__main__":
    transform_prices()