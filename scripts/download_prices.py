import yfinance as yf
import pandas as pd
from datetime import datetime
from dateutil.relativedelta import relativedelta
from pathlib import Path
import logging 
import yaml




BASE_DIR = Path(__file__).resolve().parent.parent
PRICES_DIR = BASE_DIR / "data" / "raw" / "prices"
LOG_DIR = BASE_DIR / "logs"
LOG_FILE = LOG_DIR / "download_prices.log"
PRICES_DIR.mkdir(parents=True, exist_ok=True)
LOG_DIR.mkdir(parents=True, exist_ok=True)

with open(BASE_DIR / "config" / "universe.yaml", "r") as f:
    UNIVERSE = yaml.safe_load(f)

BENCHMARK = UNIVERSE["benchmark"]
TICKERS = UNIVERSE["tickers"]

SYMBOLS = [BENCHMARK] + TICKERS

logging.basicConfig(filename=LOG_FILE, level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def download_prices(ticker: str, years: int = 10, interval: str = "1d") -> pd.DataFrame:
    end = datetime.now()
    start = end - relativedelta(years=years)
    df = yf.download(ticker, start=start, end=end, interval=interval, auto_adjust=True, progress=False)
    
    if df.empty:
        raise ValueError(f"No data found for {ticker}")
    
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    
    return df

def download_prices_for_universe(universe: list[str], years: int = 10, interval: str = "1d") -> pd.DataFrame:
    for ticker in universe:
        df = download_prices(ticker, years, interval)
        df.to_parquet(PRICES_DIR / f"{ticker}.parquet")
        logger.info(f"Downloaded prices for {ticker}")

if __name__ == "__main__":
    download_prices_for_universe(SYMBOLS, years=10, interval="1d")
