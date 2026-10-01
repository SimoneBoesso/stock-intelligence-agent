"""Train a metrics-only logistic baseline and report test hit rate."""

from __future__ import annotations

import logging
import sys
from pathlib import Path

from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

SCRIPTS_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPTS_DIR))

from load_dataset import DEFAULT_SPLIT_DATE, load_dataset, split_dataset  # noqa: E402

BASE_DIR = Path(__file__).resolve().parent.parent
LOG_DIR = BASE_DIR / "logs"
LOG_FILE = LOG_DIR / "train_metrics_baseline.log"
FEATURE_COLS = ["ret_1d", "ret_5d", "ret_21d", "vol_21d"]

LOG_DIR.mkdir(parents=True, exist_ok=True)
logging.basicConfig(
    filename=LOG_FILE,
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


def hit_rate(y_true, y_pred) -> float:
    return float((y_pred == y_true).mean())


def main() -> None:
    dataset = load_dataset()
    train, test = split_dataset(dataset, DEFAULT_SPLIT_DATE)

    X_train = train[FEATURE_COLS]
    y_train = train["label"]
    X_test = test[FEATURE_COLS]
    y_test = test["label"]

    pipe = Pipeline(
        [
            ("scaler", StandardScaler()),
            ("clf", LogisticRegression(max_iter=1000)),
        ]
    )
    pipe.fit(X_train, y_train)
    pred = pipe.predict(X_test)
    hr = hit_rate(y_test.to_numpy(), pred)

    # Naive references on the same test fold
    always_up = float((y_test == "up").mean())
    always_down = float((y_test == "down").mean())

    msg = (
        f"split={DEFAULT_SPLIT_DATE} test_n={len(test)} "
        f"metrics_logreg_hit={hr:.4f} "
        f"always_up={always_up:.4f} always_down={always_down:.4f}"
    )
    logger.info(msg)
    print(msg)


if __name__ == "__main__":
    main()
