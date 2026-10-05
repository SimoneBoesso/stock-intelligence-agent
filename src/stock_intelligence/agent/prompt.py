

import pandas as pd
from sentence_transformers import SentenceTransformer
from stock_intelligence.rag.retrieve_news import retrieve_news

def build_forecast_prompt(
    ticker: str,
    forecast_date: str,
    news_df: pd.DataFrame,
    metrics: dict | None = None,
) -> str:

    news_lines = []
    for i, row in news_df.iterrows():
        news_lines.append(
            f"- [{row.get('published_at')}] {row.get('text', '')[:500]}\n"
            f"  source: {row.get('source', '')} | url: {row.get('url', '')}"
        )
    news_block = "\n".join(news_lines) if news_lines else "No news available before forecast_date."

    if metrics:
        metrics_block = "\n".join(f"- {k}: {v}" for k, v in metrics.items())
    else:
        metrics_block = "No metrics provided."

    prompt = f"""You are a financial research assistant for a demo system (not financial advice).

    Task: forecast the 30-day excess return direction of {ticker} vs SPY as of {forecast_date}.
    Labels: "up" (beats SPY) or "down" (lags SPY).

    METRICS:
    {metrics_block}

    NEWS (already filtered to published_at < {forecast_date}; use ONLY these):
    {news_block}

    Rules:
    - Use only the news/metrics above. Do not invent facts or sources.
    - sources must be URLs (or ids) taken from the NEWS section.
    - Respond with ONLY a JSON object with these fields:
    ticker, forecast_date, direction, confidence, rationale, sources
    - direction must be "up" or "down"
    - confidence must be a number between 0 and 1
    """
    return prompt
    




if __name__ == "__main__":
    

    ticker = "AAPL"
    forecast_date = "2026-09-28"
    model = SentenceTransformer("BAAI/bge-small-en-v1.5")

    news_df = retrieve_news(
        model=model,
        ticker=ticker,
        query=f"{ticker} company news earnings",
        current_date=forecast_date,
        top_k=5,
    )
    prompt = build_forecast_prompt(ticker, forecast_date, news_df, None)
    print(prompt)