# Stock Intelligence Agent

A system to synthesize and evaluate financial information with LLMs, RAG, and relationship graphs, backed by a rigorous evaluation framework (point-in-time, baselines, forward test).

> **Disclaimer:** this is a demonstration project, not financial advice.

## Goal

- Collect news and structured data for US companies.
- Combine **metrics** (prices, fundamentals) with **RAG context** (news, filings).
- An **analyst agent** produces a structured forecast (direction, confidence, rationale, sources).
- Evaluate forecast quality honestly against baselines.

**Forecast target (to be locked in):** 30-day return direction vs a benchmark (e.g. SPY).

**Framing:** a system to synthesize and evaluate financial information with LLMs — not a stock predictor.

## Architecture

```
Sources (yfinance, EDGAR, GDELT, Finnhub, FRED)
        │
        ▼
 Ingestion service ──► Queue (RabbitMQ/Kafka)
                                  │
                                  ▼
                         Worker: dedup (Redis) → embedding → indexing
                                  │
              ┌───────────────────┼────────────────────┐
              ▼                   ▼                    ▼
       DuckDB/Parquet        Vector store           Neo4j (graph)
        (metrics)          (news + filings)      (company relations)
              └───────────────────┼────────────────────┘
                                  ▼
                     Analyst agent (LangGraph)
              retrieve → analyze → critique → decide
                                  │
                                  ▼
                  Structured forecast + cited sources
                                  │
                                  ▼
            Evaluation / forward test / Streamlit dashboard
```

**Golden rule:** every retrieval query filters `document_date < forecast_date`.

## Planned stack

| Layer | Choice |
|---|---|
| Language / data layer | Python, Parquet + DuckDB |
| ETL orchestration | Prefect or scheduled scripts |
| Embeddings | sentence-transformers (e.g. `bge-small`) |
| Vector store | LanceDB or Chroma |
| LLM | Gemini/Groq free tier or local Ollama |
| Agent | LangGraph + Pydantic output |
| Graph | Neo4j |
| Cache / dedup | Redis |
| Queue | RabbitMQ (or Kafka) |
| Demo | Streamlit |
| Infra | Docker Compose, GitHub Actions |

## Data sources (US market, free tier)

| Type | Source |
|---|---|
| Prices | yfinance (or Tiingo/Stooq) |
| Fundamentals / filings | SEC EDGAR |
| News | GDELT + Finnhub |
| Macro | FRED / ALFRED |

Everything is archived locally from day one (see `.gitignore` for excluded paths).

## Roadmap

The full plan (phases, priorities, risks, portfolio checklist) is in [`roadmap_stock_intelligence.md`](./roadmap_stock_intelligence.md).

**Priorities:**

1. **Core:** point-in-time data, baselines, RAG, agent, evaluation, tests, Docker
2. **Production:** queue + worker, experiments, observability, CI
3. **Differentiator:** Neo4j and GraphRAG
4. **Bonus:** sentiment fine-tuning, optionally GNN

## Status

The repository is in early setup: documentation and roadmap are in place; code will follow the phased plan.

## License

[GPL-3.0](./LICENSE)
