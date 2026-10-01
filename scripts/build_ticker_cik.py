from pathlib import Path
import os
import logging

import requests
import yaml
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
UNIVERSE_FILE = BASE_DIR / "config" / "universe.yaml"
OUT_FILE = BASE_DIR / "config" / "ticker_cik.yaml"
LOG_DIR = BASE_DIR / "logs"
LOG_FILE = LOG_DIR / "build_ticker_cik.log"
URL = "https://www.sec.gov/files/company_tickers.json"

LOG_DIR.mkdir(parents=True, exist_ok=True)
logging.basicConfig(
    filename=LOG_FILE,
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

load_dotenv(BASE_DIR / ".env")

user_agent = os.getenv("SEC_USER_AGENT")
if not user_agent:
    raise SystemExit("Set SEC_USER_AGENT in .env")
HEADERS = {"User-Agent": user_agent}

with open(UNIVERSE_FILE) as f:
    universe = yaml.safe_load(f)
tickers = universe["tickers"]  # equity only; SPY stays in benchmark


def main() -> None:
    r = requests.get(URL, headers=HEADERS, timeout=30)
    r.raise_for_status()
    data = r.json()

    by_ticker = {
        row["ticker"].upper(): row["cik_str"]
        for row in data.values()
    }

    mapping: dict[str, str] = {}
    for ticker in tickers:
        key = ticker.upper()
        if key not in by_ticker:
            raise KeyError(f"Ticker {ticker} not found in SEC company_tickers.json")
        mapping[ticker] = f"{int(by_ticker[key]):010d}"
        logger.info("Mapped %s -> %s", ticker, mapping[ticker])

    with open(OUT_FILE, "w") as f:
        yaml.safe_dump(mapping, f, sort_keys=False)

    logger.info("Wrote %s (%d tickers)", OUT_FILE, len(mapping))
    print(f"Wrote {OUT_FILE} ({len(mapping)} tickers)")


if __name__ == "__main__":
    main()
