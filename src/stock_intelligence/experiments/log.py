"""Minimal experiment registry (CSV append). No MLflow required."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

import pandas as pd

DEFAULT_REGISTRY = (
    Path(__file__).resolve().parents[3] / "data" / "sample" / "experiments.csv"
)


def new_run_id() -> str:
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    return f"{stamp}_{uuid4().hex[:8]}"


def log_experiment(
    *,
    run_id: str,
    kind: str,
    n: int,
    metrics: dict[str, float],
    sample_path: str,
    preds_path: str | None = None,
    notes: str = "",
    extra: dict | None = None,
    registry_path: Path | str = DEFAULT_REGISTRY,
) -> Path:
    """Append one experiment row to the CSV registry."""
    path = Path(registry_path)
    path.parent.mkdir(parents=True, exist_ok=True)

    row = {
        "run_id": run_id,
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "kind": kind,
        "n": n,
        "sample_path": sample_path,
        "preds_path": preds_path or "",
        "notes": notes,
    }
    for key, value in metrics.items():
        row[f"hit_{key}"] = value
    if extra:
        for key, value in extra.items():
            row[key] = value

    new_df = pd.DataFrame([row])
    if path.exists():
        old = pd.read_csv(path)
        out = pd.concat([old, new_df], ignore_index=True)
    else:
        out = new_df
    out.to_csv(path, index=False)
    return path
