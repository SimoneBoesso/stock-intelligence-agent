import duckdb
from pathlib import Path
import pandas as pd

BASE_DIR = Path(__file__).resolve().parent.parent
TRANSFORMED_DIR = BASE_DIR / "data" / "processed"
TRANSFORMED_FILE = TRANSFORMED_DIR / "prices.parquet"

conn = duckdb.connect()

DEFAULT_QUERY = f"""SELECT
  ticker,
  COUNT(*) AS n_rows,
  MIN(date) AS min_date,
  MAX(date) AS max_date
FROM read_parquet('{TRANSFORMED_FILE.as_posix()}')
GROUP BY ticker
ORDER BY ticker;
"""


def query_prices(query: str = DEFAULT_QUERY) -> pd.DataFrame:
    return conn.execute(query).fetch_df()

if __name__ == "__main__":
    print(query_prices())