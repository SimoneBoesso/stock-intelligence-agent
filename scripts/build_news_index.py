from pathlib import Path
import logging

import pandas as pd

BASE_DIR = Path(__file__).resolve().parent.parent
NEWS_FILE = BASE_DIR / "data" / "processed" / "news.parquet"
INDEX_DIR = BASE_DIR / "data" / "indexes" / "news_lancedb"
LOG_DIR = BASE_DIR / "logs"
LOG_FILE = LOG_DIR / "build_news_index.log"

LOG_DIR.mkdir(parents=True, exist_ok=True)
logging.basicConfig(
    filename=LOG_FILE,
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


def load_documents() -> pd.DataFrame:
    df = pd.read_parquet(NEWS_FILE)
    df["published_at"] = pd.to_datetime(df["published_at"], utc=True)
    df["summary"] = df["summary"].fillna("")
    df["text"] = df["headline"].fillna("") + "\n" + df["summary"]
    df = df[df["text"].str.strip().astype(bool)].copy()
    logger.info("Loaded %s news documents from %s", len(df), NEWS_FILE)
    return df



from sentence_transformers import SentenceTransformer
import lancedb

MODEL_NAME = "BAAI/bge-small-en-v1.5"
TABLE_NAME = "news"

def build_index(docs: pd.DataFrame) -> None:
    INDEX_DIR.mkdir(parents=True, exist_ok=True)

    model = SentenceTransformer(MODEL_NAME)
    texts = docs["text"].tolist()
    
    vectors = model.encode(texts, show_progress_bar=True, normalize_embeddings=True)

    table_df = pd.DataFrame({
        "vector": list(vectors),
        "text": docs["text"].to_numpy(),
        "ticker": docs["ticker"].to_numpy(),
        "published_at": docs["published_at"].astype(str).to_numpy(),  # ISO string ok per filtri
        "article_id": docs["article_id"].to_numpy(),
        "source": docs["source"].fillna("").to_numpy(),
        "url": docs["url"].fillna("").to_numpy(),
    })

    db = lancedb.connect(INDEX_DIR)
    db.create_table(TABLE_NAME, data=table_df, mode="overwrite")
    logger.info("Wrote LanceDB table '%s' with %s rows → %s", TABLE_NAME, len(table_df), INDEX_DIR)


def main() -> None:
    docs = load_documents()
    build_index(docs)



if __name__ == "__main__":
    main()
