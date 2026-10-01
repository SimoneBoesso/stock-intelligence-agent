from datetime import datetime, timezone
from pathlib import Path
import json
import logging

import pandas as pd

BASE_DIR = Path(__file__).resolve().parent.parent
LOG_DIR = BASE_DIR / "logs"
LOG_FILE = LOG_DIR / "transform_filings.log"
EDGAR_DIR = BASE_DIR / "data" / "raw" / "edgar"
OUT_FILE = BASE_DIR / "data" / "processed" / "filings.parquet"
ALLOWED_FORMS = {"10-K", "10-Q", "8-K"}

LOG_DIR.mkdir(parents=True, exist_ok=True)
OUT_FILE.parent.mkdir(parents=True, exist_ok=True)

logging.basicConfig(
    filename=LOG_FILE,
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


def main() -> None:
    rows: list[dict] = []

    for path in EDGAR_DIR.glob("*.json"):
        ticker = path.stem
        data = json.loads(path.read_text())
        recent = data["filings"]["recent"]
        cik = f"{int(data['cik']):010d}"

        for i in range(len(recent["form"])):
            form = recent["form"][i]
            if form not in ALLOWED_FORMS:
                continue
            rows.append(
                {
                    "ticker": ticker,
                    "cik": cik,
                    "form": form,
                    "filed_at": recent["filingDate"][i],
                    "accession_number": recent["accessionNumber"][i],
                    "primary_document": recent["primaryDocument"][i],
                }
            )

    df = pd.DataFrame(rows)
    df = df.drop_duplicates(subset=["ticker", "accession_number"])
    df["ingested_at"] = datetime.now(timezone.utc)
    df.to_parquet(OUT_FILE, index=False)

    logger.info("Saved %s filings to %s", len(df), OUT_FILE)
    print(f"Saved {len(df)} filings to {OUT_FILE}")


if __name__ == "__main__":
    main()
