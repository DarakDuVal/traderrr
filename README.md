# Traderrr

An algorithmic trading platform with regime-adaptive signal generation, portfolio management, and risk analysis.

[![CodeQL](https://github.com/DarakDuVal/traderrr/actions/workflows/github-code-scanning/codeql/badge.svg)](https://github.com/DarakDuVal/traderrr/actions/workflows/github-code-scanning/codeql)
[![Tests & Coverage](https://github.com/DarakDuVal/traderrr/actions/workflows/tests.yml/badge.svg)](https://github.com/DarakDuVal/traderrr/actions/workflows/tests.yml)
[![Code Quality](https://github.com/DarakDuVal/traderrr/actions/workflows/code-quality.yml/badge.svg)](https://github.com/DarakDuVal/traderrr/actions/workflows/code-quality.yml)

---

## Status: Backend + Frontend Complete

The backend (FastAPI) and frontend (Next.js) are implemented. The backend trading engine is well-tested and the web dashboard includes real-time WebSocket updates, JWT authentication, and full CRUD for portfolio management. See [PLAN.md](PLAN.md) for the full roadmap.

**Completed**: Phase 0 (monorepo) · Phase 1 (FastAPI backend) · Phase 2 (Next.js frontend)
**In progress**: Phase 3 (React Native) · Phase 4 (production polish)

**Stack**: FastAPI · Next.js 14 · React Native (Expo) · PostgreSQL (Supabase) · WebSocket · Celery + Redis · Docker · pnpm monorepo

---

## What It Does

Traderrr generates trading signals by analysing market data across two complementary strategies that adapt to the current market regime:

- **Momentum strategy** — for trending markets: requires 4+ aligned indicators (MACD crossover, RSI in range, moving average alignment, ADX trend strength, volume surge)
- **Mean reversion strategy** — for ranging/volatile markets: requires 3+ aligned indicators (RSI extremes, Bollinger Band extremes, Stochastic, Williams %R)

Signals carry a confidence score (0.0–1.0) derived from indicator alignment, regime fit, and volume confirmation. Only signals above the configured threshold (default 0.6) are surfaced.

On top of signal generation, the platform provides:

- **Portfolio management** — track positions, shares, average cost, and P&L
- **Risk analysis** — VaR (95%/99%), Sharpe ratio, Sortino ratio, max drawdown, correlation matrix, stress testing
- **Portfolio optimisation** — mean-variance optimisation with ATR-based position sizing

See [docs/SIGNALS.md](docs/SIGNALS.md) for the complete signal decision pipeline with code references.

---

## Architecture

```
backend/          FastAPI + SQLAlchemy 2.0 + Alembic + Celery + Redis
frontend/         Next.js 14 (App Router) + TypeScript + Tailwind + shadcn/ui
mobile/           React Native (Expo) + Expo Router
packages/
  types/          Shared TypeScript type definitions
  api-client/     Auto-generated from FastAPI OpenAPI spec
```

Full architecture rationale: [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)

---

## Core Domain (Preserved)

The following modules contain the trading intelligence and are carried forward unchanged into the new architecture:

| Module | Description |
|--------|-------------|
| `app/core/indicators.py` | 15+ technical indicators + market regime detection (Hurst, ADX, RSI, MACD, Bollinger, Stochastic, Williams %R, ATR) |
| `app/core/signal_generator.py` | Regime-adaptive dual-strategy signal generation with confidence scoring |
| `app/core/portfolio_analyzer.py` | Risk metrics: VaR, Sharpe, Sortino, max drawdown, correlation |
| `app/core/portfolio_manager.py` | Position management and portfolio operations |
| `app/core/data_manager.py` | Yahoo Finance data fetching with caching |
| `app/models/` | SQLAlchemy 2.0 models for all entities |
| `migrations/` | Alembic migration history |

---

## Signal Logic

### Market Regime Detection

The system classifies current market conditions before selecting a strategy:

| Condition | Regime | Strategy |
|-----------|--------|----------|
| High volatility | `HIGH_VOLATILITY` | Mean reversion |
| Hurst > 0.55 AND trend strength > 0.7 AND SMA20 > SMA50 | `TRENDING_UP` | Momentum |
| Hurst > 0.55 AND trend strength > 0.7 AND SMA20 < SMA50 | `TRENDING_DOWN` | Momentum |
| Hurst < 0.45 | `MEAN_REVERTING` | Mean reversion |
| Otherwise | `SIDEWAYS` | Mean reversion |

### Confidence Scoring

Base score: 0.5. Bonuses applied for:
- Regime alignment with signal direction: +20%
- Strong trend confirmation (ADX > 25): +10%
- Volume surge (> 1.5× average): +10%
- Indicator extremes (RSI > 75 or < 25): +10%

### Risk Management

- Position sizing: ATR-based (stop loss = 2× ATR, target = 4× ATR)
- Maximum position: 20% of portfolio per ticker
- Sector concentration limit: 40%

---

## Development Setup

### With Docker

```bash
cp .env.example .env          # fill in DATABASE_URL, REDIS_URL, SECRET_KEY
docker compose up
```

Services: FastAPI on `:8000`, Next.js on `:3000`, PostgreSQL on `:5432`, Redis on `:6379`, Celery worker + Beat, Flower on `:5555`.

### Backend only

```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements-dev.txt
pytest tests/ -v
uvicorn app.main:app --reload
```

### Frontend only

```bash
pnpm install
pnpm --filter @traderrr/frontend dev    # starts Next.js at localhost:3000
pnpm --filter @traderrr/frontend lint   # ESLint
pnpm --filter @traderrr/frontend type-check  # TypeScript strict
pnpm --filter @traderrr/frontend build  # production build
```

### Environment variables

```bash
DATABASE_URL=postgresql+asyncpg://user:pass@localhost:5432/traderrr
REDIS_URL=redis://localhost:6379/0
SECRET_KEY=<32-char random string>
ACCESS_TOKEN_EXPIRE_MINUTES=15
REFRESH_TOKEN_EXPIRE_DAYS=7
LOG_LEVEL=INFO
ENVIRONMENT=development
NEXT_PUBLIC_API_URL=http://localhost:8000
```

---

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md). Quick reference:

1. Branch from `develop`: `feature/your-feature`, `bugfix/issue-name`, `hotfix/critical`
2. Make changes in the relevant workspace (`backend/`, `frontend/`, `mobile/`, `packages/`)
3. Quality gates: `make lint && make test` (backend), `pnpm lint && pnpm type-check` (frontend/mobile)
4. Open PR to `develop`; link the relevant issue

---

## Documentation

| Document | Contents |
|----------|---------|
| [PLAN.md](PLAN.md) | Architecture rebuild plan, phases, decisions |
| [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) | Tech stack decisions, trade-offs, repo structure |
| [docs/SIGNALS.md](docs/SIGNALS.md) | Signal generation algorithm deep-dive |
| [CONTRIBUTING.md](CONTRIBUTING.md) | Contribution workflow |
| [SECURITY.md](SECURITY.md) | Security policy and vulnerability reporting |

---

## License

[MIT](LICENSE.md) — Educational and personal use. Not financial advice.
