import logging
from pathlib import Path

import pandas as pd

BASE_DIR = Path(__file__).resolve().parent.parent
LOG_DIR = BASE_DIR / "logs"
LOG_FILE = LOG_DIR / "load_dataset.log"
PROCESSED_DIR = BASE_DIR / "data" / "processed"
DEFAULT_SPLIT_DATE = "2023-01-01"

LOG_DIR.mkdir(parents=True, exist_ok=True)
logging.basicConfig(
    filename=LOG_FILE,
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


def load_dataset() -> pd.DataFrame:
    labels = pd.read_parquet(PROCESSED_DIR / "labels.parquet")
    features = pd.read_parquet(PROCESSED_DIR / "features.parquet")

    labels["date"] = pd.to_datetime(labels["date"])
    features["date"] = pd.to_datetime(features["date"])

    out = labels.merge(features, on=["ticker", "date"], how="inner")
    logger.info(
        "Loaded labels=%s features=%s merged=%s",
        len(labels),
        len(features),
        len(out),
    )
    return out


def split_dataset(
    dataset: pd.DataFrame, split_date: str = DEFAULT_SPLIT_DATE
) -> tuple[pd.DataFrame, pd.DataFrame]:
    split = pd.Timestamp(split_date)
    train = dataset[dataset["date"] < split].copy()
    test = dataset[dataset["date"] >= split].copy()
    logger.info(
        "Temporal split at %s: total=%s train=%s test=%s",
        split_date,
        len(dataset),
        len(train),
        len(test),
    )
    return train, test


def main() -> None:
    dataset = load_dataset()
    train, test = split_dataset(dataset, DEFAULT_SPLIT_DATE)

    train_path = PROCESSED_DIR / "train.parquet"
    test_path = PROCESSED_DIR / "test.parquet"
    train.to_parquet(train_path, index=False)
    test.to_parquet(test_path, index=False)

    logger.info("Saved train=%s → %s", len(train), train_path)
    logger.info("Saved test=%s → %s", len(test), test_path)
    print(f"train={len(train)} test={len(test)} split={DEFAULT_SPLIT_DATE}")


if __name__ == "__main__":
    main()
