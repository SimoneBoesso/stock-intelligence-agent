# Stock Intelligence Agent

A system to synthesize and evaluate financial information with LLMs, RAG, and relationship graphs, backed by a rigorous evaluation framework (point-in-time, baselines, forward test).

> **Disclaimer:** this is a demonstration project, not financial advice.

## Goal

- Collect news and structured data for US companies.
- Combine **metrics** (prices, fundamentals) with **RAG context** (news, filings).
- An **analyst agent** produces a structured forecast (direction, confidence, rationale, sources).
- Evaluate forecast quality honestly against baselines.

**Forecast target (locked):** 30-day excess return direction vs SPY — labels: `up` / `down`.

**Framing:** a system to synthesize and evaluate financial information with LLMs — not a stock predictor.

## Status (current)

Working local pipeline on **20 US large caps** (`config/universe.yaml`, benchmark SPY):

| Area | State |
|---|---|
| **Data** | Prices (yfinance), EDGAR metadata/filings, Finnhub + GDELT news → Parquet |
| **Baselines** | Features + logistic regression metrics-only; naive eval scripts |
| **RAG** | LanceDB + `BAAI/bge-small-en-v1.5`; retrieval filters `published_at < forecast_date` |
| **Agent** | Plain Python: prompt → Groq LLM → Pydantic `Forecast` (direction, confidence, rationale, sources) |
| **Eval** | Smoke eval (`eval_smoke.py`) vs baselines; PIT unit tests |
| **Forward test** | Daily job: refresh news/index + prices/labels → resolve → log forecasts → hit-rate report |

**Not built yet:** queue/worker, Neo4j/GraphRAG, Streamlit, Docker Compose, FRED, LangGraph multi-step.

**Golden rule:** every retrieval query filters `document_date < forecast_date`.

## Architecture (target)

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

Today the same ideas run as **scheduled scripts** (Parquet + LanceDB + Groq), without queue/graph/UI.

## Stack in use

| Layer | Choice |
|---|---|
| Language / data | Python ≥3.11, Parquet + DuckDB |
| Embeddings / vector | sentence-transformers (`bge-small`), LanceDB |
| LLM | Groq (`openai/gpt-oss-20b` via OpenAI-compatible client) |
| Agent output | Pydantic |
| Eval / baselines | pandas, scikit-learn |
| Orchestration | scripts + optional cron (`docs/forward_cron.md`) |

Planned later: Neo4j, Redis, RabbitMQ, LangGraph, Streamlit, Docker Compose — see roadmap.

## Data sources (US market, free tier)

| Type | Source | In repo |
|---|---|---|
| Prices | yfinance | yes |
| Fundamentals / filings | SEC EDGAR | yes (meta + transform) |
| News | GDELT + Finnhub | yes |
| Macro | FRED / ALFRED | not yet |

Everything is archived locally from day one (see `.gitignore` for excluded paths).

## Setup

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
cp .env.example .env   # set GROQ_API_KEY, FINNHUB_API_KEY, SEC_USER_AGENT
```

Forward-test daily job (Finnhub + GDELT → news index → prices/labels → resolve → log → report):

```bash
.venv/bin/python scripts/forward_daily.py --tickers AAPL,MSFT,PG
```

Cron setup: [`docs/forward_cron.md`](./docs/forward_cron.md).

Registry: `data/processed/forward_forecasts.parquet` (labels filled after ~30 trading days via `forward_resolve`).

## Roadmap

Full plan (phases, priorities, risks, portfolio checklist): [`roadmap_stock_intelligence.md`](./roadmap_stock_intelligence.md).

**Priorities:**

1. **Core:** point-in-time data, baselines, RAG, agent, evaluation, tests, Docker
2. **Production:** queue + worker, experiments, observability, CI
3. **Differentiator:** Neo4j and GraphRAG
4. **Bonus:** sentiment fine-tuning, optionally GNN

## License

[GPL-3.0](./LICENSE)
