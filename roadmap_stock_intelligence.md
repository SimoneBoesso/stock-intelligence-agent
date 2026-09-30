# Stock Intelligence Agent: Roadmap

A system to synthesize and evaluate financial information with LLMs, RAG, and relationship graphs, backed by a rigorous evaluation framework (point-in-time, baselines, forward test).

> **Disclaimer:** this is a demonstration project, not financial advice.

---

## 1. Goal

- Collect news and structured data for US companies.
- Combine **metrics** (prices, fundamentals) with **RAG context** (news, filings).
- An **analyst agent** produces a structured forecast (direction, confidence, rationale, sources).
- Evaluate forecast quality honestly against baselines.

**Forecast target (to be locked in):** 30-day return direction vs a benchmark (e.g. SPY).

**Framing:** "a system to synthesize and evaluate financial information with LLMs", not "a stock predictor".

---

## 2. Data sources (free, US market)

| Type | Source | Notes |
|---|---|---|
| Prices | yfinance (or Tiingo/Stooq) | Unofficial: store everything locally |
| Fundamentals / filings | SEC EDGAR | 10-K, 10-Q, 8-K with filing date (point-in-time) |
| News | GDELT + Finnhub (free tier) | GDELT is noisy but has history; Finnhub history is limited |
| Macro | FRED / ALFRED | ALFRED for historical vintages |

Notes:
- Free NewsAPI is unsuitable for backtesting (delay and short history).
- Check free-tier limits on official documentation.
- **Archive everything locally from day one.**

---

## 3. Stack

| Layer | Choice |
|---|---|
| Language / data layer | Python, Parquet + DuckDB |
| ETL orchestration | Prefect or scheduled scripts |
| Embeddings | sentence-transformers (e.g. `bge-small`) |
| Vector store | LanceDB or Chroma (with `published_at` metadata) |
| LLM | Gemini/Groq free tier or local Ollama |
| Structured output | Pydantic |
| Agent | Plain Python; LangGraph for the multi-step flow |
| Graph | Neo4j |
| Cache / dedup | Redis |
| Raw documents | MongoDB (optional) |
| Message queue | RabbitMQ (simpler) or Kafka |
| Evaluation | pandas + scikit-learn, reports in Quarto/notebooks |
| Experiments | MLflow or Weights & Biases |
| Observability | Langfuse or LangSmith |
| Demo | Streamlit |
| Infra / CI | Docker Compose, GitHub Actions |

---

## 4. Architecture

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

---

## 5. Phased roadmap

### Phase 1: Data
- 15–20 US large caps.
- Prices + EDGAR filings + news in DuckDB/Parquet.
- Data model with publication timestamps everywhere.

### Phase 2: Baseline without LLM
- Metrics-only model (returns, volatility, fundamentals).
- Naive baselines: buy & hold, random forecast.

### Phase 3: RAG and agent
- Index news/filings with a strict temporal filter.
- Agent with structured output (direction, confidence, rationale, sources).
- Unit tests for the point-in-time filter (**the most important test in the project**).

### Phase 4: Evaluation
Compare:
1. Buy & hold / random
2. Metrics-only
3. LLM without retrieval
4. LLM + RAG
5. LLM + GraphRAG (after phase 7)

Metrics: hit rate, information coefficient, Sharpe of a simple strategy, confidence calibration.

### Phase 5: Production level
- Queue + worker with retry and idempotency.
- Docker Compose for the full stack.
- MLflow/W&B for experiments, Langfuse for agent tracing.
- CI with lint, tests, and type checks.
- LLM guardrails: output validation, retry, fallback, mandatory source citations.

### Phase 6: Forward test + UI
- Automatic daily/weekly forecasts, logged with timestamps.
- 30-day evaluation: a track record that grows over time.
- Streamlit dashboard.

### Phase 7: Graph (differentiator)
- Neo4j: nodes `Company`, `Sector`, `Person`, `Event`.
- Edges: `COMPETITOR_OF`, `SUPPLIER_OF`, `MENTIONED_WITH`.
- Relations from EDGAR filings and entity extraction from news.
- **GraphRAG:** also retrieve news from graph neighbors.

### Phase 8: Bonus
- PyTorch fine-tuning of a small model (FinBERT/DeBERTa) for sentiment.
- GNN with PyG, compared against the no-graph baseline.
- Realistic continuous learning: a periodic job that compares forecasts vs outcomes, measures calibration, and recalibrates confidences.

### Phase 9: Polish
- README with architecture, charts, baseline comparison, honest limitations, and disclaimer.

---

## 6. Priorities (to avoid scope creep)

1. **Core (required):** point-in-time data, baselines, RAG, agent, evaluation, tests, Docker.
2. **Production level:** queue + worker, experiment tracking, observability, CI.
3. **Differentiator:** Neo4j and GraphRAG.
4. **Bonus:** PyTorch fine-tuning, then optionally GNN.

Better a solid core with items 2 and 3 done well than everything half-finished.

---

## 7. Main risks

| Risk | Mitigation |
|---|---|
| **Data leakage** (LLM already knows the outcome) | Test on post-model-cutoff periods + forward test + point-in-time retrieval |
| Vague forecast target | Define it first: direction vs benchmark at 30 days |
| No baselines | Mandatory baselines (phases 2 and 4) |
| Statistical noise | More companies and time windows, metrics beyond accuracy |
| Excessive scope | Follow the priority order in section 6 |
| Dependency on unofficial sources | Local archival from day one |

---

## 8. Mapping to the job posting

| Requirement | Coverage in the project | Level |
|---|---|---|
| LLM, Transformers, agents | Analyst agent with tools and structured output | Strong |
| LangChain/LangGraph | Orchestration retrieve → analyze → critique → decide | Strong |
| Kafka/RabbitMQ | Queue for ingestion and async jobs | Strong (if justified) |
| PyTorch / Deep Learning | Sentiment fine-tuning, temporal model | Medium |
| GNN / knowledge graph | Neo4j + GraphRAG, then PyG | Medium (differentiator) |
| Neo4j, Redis, MongoDB | Graph, cache/dedup, raw documents | Medium |
| Continuous learning | Recalibration based on the forward test | Medium |
| Computer Vision, Spatial Reasoning | No natural fit | Weak: cover with a separate project |

---

## 9. Final portfolio checklist

- [ ] README with architecture and rationale for each tech choice
- [ ] Charts comparing baselines, LLM, RAG, and GraphRAG
- [ ] Tests for the point-in-time filter
- [ ] `docker compose up` starts the full stack
- [ ] Forward-test track record visible
- [ ] Honest "Limitations" section (including negative results)
- [ ] Disclaimer: not financial advice
