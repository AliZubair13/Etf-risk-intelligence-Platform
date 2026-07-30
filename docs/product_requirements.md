# ETF Risk Intelligence — Product Requirements (v1)

**Owner:** Zubair Ali  
**Status:** Locked for MVP build  
**Last updated:** 2026-07-30

---

## 1. Problem statement

When an ETF experiences an unusually large price movement, analysts spend hours
manually collecting holdings data, prices, filings, macro releases, and news to
determine what caused it. This platform automates that investigation while
keeping the analyst in the loop for review and correction.

The platform answers a single primary question:

> **Why did this ETF move unusually on this date?**

---

## 2. In-scope ETFs

| Ticker | Name                         | Category       | Benchmark  |
|--------|------------------------------|----------------|------------|
| SPY    | SPDR S&P 500 ETF Trust       | Broad market   | (baseline) |
| QQQ    | Invesco QQQ Trust            | Tech-heavy     | SPY        |
| SMH    | VanEck Semiconductor ETF     | Semiconductors | QQQ        |

Rationale: nested benchmarks give hierarchical factor attribution
(market → tech → semis).

---

## 3. Supported dates and data frequency

- **Historical data range:** 2022-01-03 to T-1
- **Investigable dates:** 2022-02-01 onward
- **Excluded:** weekends, US market holidays
- **Price frequency:** daily end-of-day, adjusted close
- **Holdings frequency:** weekly current, quarterly historical
- **Macro:** as released
- **Filings:** ingested daily

No intraday, no tick data, no real-time.

---

## 4. Holdings scope

- **Top N per ETF:** 20
- **Coverage tracking:** covered_weight = sum(top_20_weights), never normalized to 100%
- **Missing holding on a date:** logged and included in reconciliation error

---

## 5. Anomaly definition

An investigation is warranted when EITHER condition is met:

**Condition A — Statistical z-score:**
- |z_score| >= 2.0
- z_score = (daily_return - rolling_mean_60d) / rolling_std_60d

**Condition B — Benchmark-adjusted return exceeds threshold:**

| ETF  | Threshold |
|------|-----------|
| SPY  | 1.5%      |
| QQQ  | 2.0%      |
| SMH  | 2.5%      |

Rolling window: 60 trading days, minimum 40 observations.

---

## 6. Event types (v1)

- SEC 8-K filings (primary source)
- SEC 10-K, 10-Q (context)
- FOMC decisions (FRED)
- CPI, PPI, unemployment, nonfarm payroll (FRED)
- Earnings announcements (from 8-K Item 2.02)

News/general articles: deferred to v2.

---

## 7. Dashboard panels

1. ETF Overview
2. Holding Attribution
3. Risk Decomposition
4. Event Timeline
5. Evidence-Backed Explanation
6. Analyst Review

Out of scope for v1: live-risk view, portfolio rollup, alerts, auth, deployment.

---

## 8. Attribution methodology

- contribution_i = weight_i(t-1) x return_i(t)
- explained_return = sum(contribution_i)
- residual = ETF_return - explained_return
- reconciliation_error = |residual|

Risk decomposition via rolling 60-day regression:
- ETF_return = alpha + beta_market * market_return + beta_sector * sector_excess + epsilon
- Coefficients refit daily using data through t-1 (no look-ahead bias)

---

## 9. Event ranking formula

- EventScore = 0.30 * semantic_relevance
             + 0.20 * time_proximity
             + 0.20 * affected_etf_weight
             + 0.15 * price_reaction_strength
             + 0.10 * source_reliability
             + 0.05 * sentiment_alignment

Weights are v1 defaults, tuned via analyst feedback in Phase 17.

---

## 10. Confidence score

- confidence = 0.30 * attribution_coverage
             + 0.25 * top_event_score
             + 0.15 * source_agreement
             + 0.15 * time_alignment
             + 0.15 * data_completeness

Displayed as percentage. Labeled as system confidence score, not causal probability.

---

## 11. Evaluation targets

| Metric                        | Target  |
|-------------------------------|---------|
| Reconciliation error (median) | 25 bps  |
| Attribution top-3 accuracy    | 75%     |
| Anomaly precision             | 85%     |
| Anomaly false-alert rate      | 15%     |
| Event Precision@3             | 70%     |
| Event Recall@5                | 80%     |
| Claim support rate            | 90%     |
| Confidence Brier score        | 0.20    |

Measured on 20-30 hand-labeled historical cases.

---

## 12. Tech stack

- Backend: FastAPI + SQLAlchemy + Alembic + Pydantic
- Database: PostgreSQL 16 (Docker Compose)
- Data: yfinance, FRED API, SEC EDGAR
- ML/NLP: scikit-learn, sentence-transformers, FinBERT, Isolation Forest
- LLM: Groq (Llama 3.3 70B) primary, Anthropic Claude fallback
- Frontend: Streamlit + Plotly
- Testing: pytest
- Deployment: Docker Compose (local)

---

## 13. Out-of-scope for v1

- Real-time or intraday data
- Options, futures, derivatives
- Automatic trading or rebalancing
- Personalized financial advice
- News scraping beyond SEC/FRED
- Cloud deployment
- User authentication
- Live risk view

---

## 14. Disclaimer

This project is an educational analytical tool. It does not provide investment
advice or execute financial transactions. Event associations are evidence-based
hypotheses and should not be interpreted as proven causal relationships.
