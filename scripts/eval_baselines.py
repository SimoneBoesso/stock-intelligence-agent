import pandas as pd
import logging
import numpy as np
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent.parent
LOG_DIR = BASE_DIR / "logs"
LOG_FILE = LOG_DIR / "eval_baseline.log"
LOG_DIR.mkdir(parents=True, exist_ok=True)

logging.basicConfig(
    filename=LOG_FILE,
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

def eval_baselines(labels: pd.DataFrame) -> dict:
    metrics = {}
    hit_always_up = labels[labels["label"] == "up"].shape[0]
    hit_always_down = labels[labels["label"] == "down"].shape[0]
    metrics["hit_always_up"] = hit_always_up
    metrics["hit_always_down"] = hit_always_down
    metrics["hit_always_up_percentage"] = hit_always_up / len(labels)
    metrics["hit_always_down_percentage"] = hit_always_down / len(labels)
    
    rng = np.random.default_rng(42)
    predictions = rng.choice(["up", "down"], size=len(labels))
    hit_random = (predictions == labels["label"]).sum()
    metrics["hit_random"] = hit_random
    metrics["hit_random_percentage"] = hit_random / len(labels)

    metrics["n_samples"] = len(labels)
    metrics["n_up"] = labels["label"].value_counts()["up"]
    metrics["n_down"] = labels["label"].value_counts()["down"]
    return metrics

def main():
    labels = pd.read_parquet(BASE_DIR / "data" / "processed" / "labels.parquet")
    metrics = eval_baselines(labels)
    logger.info("Metrics: %s", metrics)

if __name__ == "__main__":
    main()