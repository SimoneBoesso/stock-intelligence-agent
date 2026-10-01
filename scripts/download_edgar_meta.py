from dotenv import load_dotenv
import os 
import requests
import yaml
import logging
from pathlib import Path
import time

BASE_DIR = Path(__file__).resolve().parent.parent
LOG_DIR = BASE_DIR / "logs"
LOG_FILE = LOG_DIR / "download_edgar_meta.log"
LOG_DIR.mkdir(parents=True, exist_ok=True)
logging.basicConfig(
    filename=LOG_FILE,
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent
EDGAR_DIR = BASE_DIR / "data" / "raw" / "edgar"
EDGAR_DIR.mkdir(parents=True, exist_ok=True)


SEC_USER_AGENT = os.getenv("SEC_USER_AGENT")
TICKER_CIK_MAP = yaml.safe_load(open(BASE_DIR / "config" / "ticker_cik.yaml"))

def main():
    for ticker, cik in TICKER_CIK_MAP.items():
        cik10 = f"{int(cik):010d}"

        url = f"https://data.sec.gov/submissions/CIK{cik10}.json"
        try:
            response = requests.get(url, headers={"User-Agent": SEC_USER_AGENT}, timeout=30)

            response.raise_for_status()
            with open(EDGAR_DIR / f"{ticker}.json", "w") as f:
                f.write(response.text)
        except requests.exceptions.RequestException as e:
            logger.error(f"Error downloading {url}: {e}")
            continue
        time.sleep(0.2)

if __name__ == "__main__":
    main()