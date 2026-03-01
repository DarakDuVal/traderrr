# Architecture Analysis & Restructuring Plan

> **Status**: Decisions finalised — see summary table at the end of this document
> **Date**: 2026-03-01
> **Branch**: develop

---

## Table of Contents

1. [Current State Analysis](#1-current-state-analysis)
2. [Decision Points](#2-decision-points)
3. [Recommended Tech Stack](#3-recommended-tech-stack)
4. [Repository Organization](#4-repository-organization)
5. [Backend Restructuring](#5-backend-restructuring)
6. [Frontend Architecture](#6-frontend-architecture)
7. [API Layer Design](#7-api-layer-design)
8. [Database Strategy](#8-database-strategy)
9. [Deployment & CI/CD Evolution](#9-deployment--cicd-evolution)
10. [Roadmap](#10-roadmap)

---

## 1. Current State Analysis

### 1.1 What We Have

Traderrr is a **production-grade algorithmic trading platform** with:

| Area | Technology | Maturity |
|------|-----------|----------|
| **Web framework** | Flask 3.0 + Flasgger (OpenAPI) | ✅ Solid |
| **ORM / DB** | SQLAlchemy 2.0 + Alembic migrations | ✅ Solid |
| **Auth** | Flask-JWT-Extended + bcrypt + RBAC | ✅ Solid |
| **Market data** | yfinance + TA-Lib + pandas/numpy | ✅ Solid |
| **Analytics** | Custom signal generator, regime detection, portfolio optimizer | ✅ Solid |
| **Testing** | pytest (67+ unit tests) + behave BDD | ✅ Good |
| **CI/CD** | GitHub Actions (tests, Black, Mypy, Pylint, CodeQL) | ✅ Good |
| **Deployment** | Docker + Gunicorn + IBM Cloud | ✅ Good |
| **Frontend** | Flask templates (minimal dashboard) + Swagger UI | ⚠️ Minimal |

### 1.2 Strengths to Preserve

- **Well-structured backend**: Clean separation into `core/`, `models/`, `api/`, `auth/` modules.
- **Rich domain logic**: 15+ technical indicators, regime-adaptive strategies, risk analysis, portfolio optimization — all in Python.
- **API-first design**: 20+ RESTful endpoints already documented with OpenAPI.
- **Mature CI/CD**: Multi-tool quality gate (Black, Mypy, Pylint, CodeQL).
- **Security posture**: JWT auth, RBAC, bcrypt, CORS, CWE-215/489 fixes documented.

### 1.3 Gaps to Address

| Gap | Impact |
|-----|--------|
| No real frontend — only Swagger UI and basic Flask templates | Blocks user adoption |
| Monolithic Flask app (API + web + scheduling in one process) | Limits scalability |
| SQLite as default database | Not suitable for multi-user production |
| No WebSocket / real-time push | Users can't see live updates |
| Scheduling runs in-process (`schedule` library in a thread) | Fragile, not scalable |
| No state management or caching layer | Redundant computations |
| IBM Cloud–specific deployment | Limits hosting options |

---

## 2. Decision Points

Each subsection below describes a decision that needs to be made, with options and trade-offs.

---

### 2.1 Frontend Framework

> **Decision**: Which JavaScript/TypeScript framework for the web frontend?

| Option | Pros | Cons |
|--------|------|------|
| **React (Next.js)** | Largest ecosystem; abundant charting libs (Recharts, TradingView widget); strong hiring pool; Next.js gives SSR, routing, API routes out of the box | Heavier bundle; more boilerplate; JSX learning curve if team is new |
| **Vue 3 (Nuxt 3)** | Gentle learning curve; excellent docs; Composition API is clean; Nuxt 3 gives SSR + file-based routing | Smaller ecosystem than React; fewer finance-specific component libraries |
| **Svelte (SvelteKit)** | Smallest bundle size; true reactivity; excellent performance for dashboards; SvelteKit gives SSR + routing | Smallest community; fewer charting integrations; less mature tooling |

**Recommendation**: **React with Next.js** — the ecosystem depth matters for a trading dashboard (charting, data tables, real-time updates). TradingView's lightweight charts library, AG Grid, and Recharts all have first-class React support. Next.js provides the best path to a companion app later (via React Native / Expo shared logic).

**If team prefers simplicity**: Vue 3 + Nuxt 3 is the pragmatic second choice.

---

### 2.2 Repository Organization

> **Decision**: How to organize frontend and backend code?

| Option | Pros | Cons |
|--------|------|------|
| **Monorepo** (single repo, `backend/` + `frontend/` dirs) | Single PR for full-stack changes; shared CI config; simpler dependency management | Larger repo; mixed language tooling; Git history less focused |
| **Polyrepo** (separate repos for backend and frontend) | Clean separation of concerns; independent deploy cycles; teams can work in isolation | Cross-repo PRs for full-stack features; harder to keep API contracts in sync; more DevOps overhead |

**Recommendation**: **Monorepo** — for a small-to-medium team, a monorepo keeps the API contract between backend and frontend tightly coupled. We can use a workspace structure that keeps tooling separate while sharing CI. As the team grows, a polyrepo split is straightforward since the API layer is already well-defined.

---

### 2.3 Backend Framework

> **Decision**: Keep Flask or migrate to a more modern Python framework?

| Option | Pros | Cons |
|--------|------|------|
| **Keep Flask** (current) | Zero migration cost; all existing code works; team knows it | No native async; no built-in WebSocket; manual OpenAPI (Flasgger) |
| **Migrate to FastAPI** | Native async/await; auto OpenAPI from type hints; Pydantic validation; WebSocket support built-in; better performance for I/O-bound workloads | Migration effort (routes, auth, middleware); some learning curve; less battle-tested for large apps |
| **Migrate to Django + DRF** | Batteries-included (admin, ORM, auth); proven at scale | Heavy migration; different ORM (Django ORM vs SQLAlchemy); overkill for API-focused app |

**Recommendation**: **Migrate to FastAPI** — the existing codebase is already well-typed (Mypy enforced) and uses SQLAlchemy 2.0, which both align perfectly with FastAPI. The migration path is incremental: FastAPI can mount Flask apps during transition. Native async support is valuable for real-time market data streaming. Auto-generated OpenAPI docs eliminate the need for Flasgger.

**If migration risk is too high**: Keep Flask and add `flask-socketio` for real-time, but accept the ongoing maintenance cost.

---

### 2.4 Database

> **Decision**: Which production database?

| Option | Pros | Cons |
|--------|------|------|
| **PostgreSQL** | Best for time-series queries (window functions, CTEs); `psycopg2` already in deps; excellent with SQLAlchemy; free; TimescaleDB extension for time-series | Requires hosted instance; more ops than SQLite |
| **PostgreSQL + TimescaleDB** | Hypertables for OHLCV data; automatic partitioning; continuous aggregates; compression | Additional extension to manage; learning curve |
| **MySQL** | `PyMySQL` already in deps; widely available | Worse window function support; less ideal for analytics workloads |
| **Keep SQLite** (dev only) | Zero setup; great for development and testing | Not suitable for concurrent multi-user production access |

**Recommendation**: **PostgreSQL** for production, **SQLite** retained for local development and CI tests. The codebase already has `psycopg2-binary` as a dependency and uses SQLAlchemy, so the switch is configuration-only. Add TimescaleDB later if OHLCV data volume warrants it.

---

### 2.5 Real-Time Communication

> **Decision**: How to push live updates (prices, signals) to the frontend?

| Option | Pros | Cons |
|--------|------|------|
| **WebSockets (via Socket.IO)** | Bidirectional; well-supported in all frameworks; `python-socketio` for backend | Stateful connections; more complex load balancing |
| **Server-Sent Events (SSE)** | Simpler (HTTP-based); auto-reconnect; sufficient for one-way push | One-directional only; no binary support |
| **Polling** | Simplest to implement; stateless | Higher latency; wasted bandwidth; poor UX for real-time data |

**Recommendation**: **Server-Sent Events (SSE)** for v1 (signal alerts, portfolio updates) — simpler to implement with both Flask and FastAPI, and sufficient for one-way push. Upgrade to **WebSockets** later if bidirectional communication (e.g., live order placement) is needed.

---

### 2.6 Task Scheduling / Background Jobs

> **Decision**: How to handle scheduled data updates, cleanup, backtests?

| Option | Pros | Cons |
|--------|------|------|
| **Celery + Redis** | Industry standard; retries, monitoring (Flower); scales horizontally | Heavy infrastructure (Redis + worker processes); complex for small teams |
| **APScheduler** | Lightweight; in-process or persistent (DB-backed); drop-in replacement for `schedule` | Single-process; less robust than Celery |
| **System cron + CLI commands** | No additional deps; reliable; Docker-friendly | No retry logic; harder to monitor; no distributed execution |

**Recommendation**: **APScheduler** for v1 (replaces the current `schedule` + thread approach with a more robust, DB-backed scheduler). Migrate to **Celery + Redis** in v2 if task volume or reliability requirements increase.

---

### 2.7 Companion App Strategy

> **Decision**: How to support a future mobile companion app?

| Option | Pros | Cons |
|--------|------|------|
| **React Native / Expo** (if React frontend) | Shared TypeScript code; shared component patterns; Expo simplifies builds | Performance ceiling for complex charts; native module bridge complexity |
| **Flutter** | Excellent performance; single codebase for iOS + Android; great for charts | Different language (Dart); no code sharing with web frontend |
| **Progressive Web App (PWA)** | Zero additional codebase; works on mobile browsers; push notifications | Limited native API access; no app store presence; less polished feel |

**Recommendation**: Start with a **PWA** — the Next.js frontend can be made installable with minimal effort (`next-pwa`). This gives mobile access immediately with zero extra code. If native features are needed later, **React Native** is the natural path from a React/Next.js frontend.

---

## 3. Recommended Tech Stack

Based on the decisions above, the recommended stack is:

### Backend
| Layer | Technology | Notes |
|-------|-----------|-------|
| **Framework** | FastAPI | Async, auto-OpenAPI, Pydantic, WebSocket-ready |
| **ORM** | SQLAlchemy 2.0 | Already in use — no change |
| **Migrations** | Alembic | Already in use — no change |
| **Auth** | `python-jose` + `passlib[bcrypt]` | FastAPI-native JWT; replaces Flask-JWT-Extended |
| **Database** | PostgreSQL (prod) / SQLite (dev) | Config-only switch via SQLAlchemy |
| **Task scheduling** | APScheduler | Replaces in-process `schedule` thread |
| **Market data** | yfinance + TA-Lib + pandas/numpy | No change — core stays as-is |
| **WSGI/ASGI** | Uvicorn (+ Gunicorn for process management) | Replaces Gunicorn-only setup |
| **Real-time** | SSE (v1) → WebSocket (v2) | Built into FastAPI |

### Frontend
| Layer | Technology | Notes |
|-------|-----------|-------|
| **Framework** | Next.js 14+ (App Router) | React-based; SSR; file-based routing |
| **Language** | TypeScript | Strict mode for type safety |
| **State management** | Zustand or TanStack Query | Lightweight; fits data-fetching patterns |
| **Charts** | Lightweight Charts (TradingView) + Recharts | OHLCV candles + portfolio analytics |
| **UI components** | shadcn/ui (Tailwind-based) | Accessible, customizable, no vendor lock-in |
| **Styling** | Tailwind CSS | Consistent with shadcn/ui |
| **API client** | OpenAPI-generated TypeScript client | Auto-generated from FastAPI's OpenAPI spec |
| **PWA** | `next-pwa` | Installable on mobile, push notifications |

### Infrastructure
| Layer | Technology | Notes |
|-------|-----------|-------|
| **Containerization** | Docker + Docker Compose | Multi-service (backend + frontend + db) |
| **CI/CD** | GitHub Actions | Extended to cover frontend lint/test/build |
| **Hosting** | Cloud-agnostic (Docker-based) | Remove IBM Cloud lock-in |

---

## 4. Repository Organization

### 4.1 Proposed Monorepo Structure

```
traderrr/
├── backend/                          # Python backend (FastAPI)
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py                   # FastAPI app factory
│   │   ├── api/                      # API route handlers
│   │   │   ├── routes/
│   │   │   │   ├── signals.py
│   │   │   │   ├── portfolio.py
│   │   │   │   ├── risk.py
│   │   │   │   ├── auth.py
│   │   │   │   └── admin.py
│   │   │   └── deps.py               # Shared dependencies (auth, db session)
│   │   ├── core/                     # Business logic (PRESERVED)
│   │   │   ├── data_manager.py
│   │   │   ├── signal_generator.py
│   │   │   ├── portfolio_manager.py
│   │   │   ├── portfolio_analyzer.py
│   │   │   └── indicators.py
│   │   ├── models/                   # SQLAlchemy models (PRESERVED)
│   │   │   ├── base.py
│   │   │   ├── user.py
│   │   │   ├── trading.py
│   │   │   ├── portfolio.py
│   │   │   ├── market_data.py
│   │   │   ├── audit.py
│   │   │   └── system.py
│   │   ├── schemas/                  # Pydantic request/response schemas
│   │   │   ├── signals.py
│   │   │   ├── portfolio.py
│   │   │   └── auth.py
│   │   ├── auth/                     # Auth logic (PRESERVED, adapted)
│   │   │   ├── service.py
│   │   │   └── middleware.py
│   │   └── db.py                     # Database session management
│   ├── config/
│   │   ├── settings.py               # Pydantic BaseSettings config
│   │   └── database.py
│   ├── migrations/                   # Alembic (PRESERVED)
│   ├── scripts/                      # CLI utilities (PRESERVED)
│   ├── tests/                        # pytest tests (PRESERVED, adapted)
│   ├── bdd/                          # BDD tests (PRESERVED)
│   ├── requirements.txt
│   ├── requirements-dev.txt
│   ├── pyproject.toml
│   ├── Dockerfile
│   └── alembic.ini
│
├── frontend/                         # Next.js frontend
│   ├── src/
│   │   ├── app/                      # Next.js App Router pages
│   │   │   ├── layout.tsx
│   │   │   ├── page.tsx              # Dashboard home
│   │   │   ├── signals/
│   │   │   │   └── page.tsx          # Trading signals view
│   │   │   ├── portfolio/
│   │   │   │   └── page.tsx          # Portfolio management
│   │   │   ├── risk/
│   │   │   │   └── page.tsx          # Risk analysis
│   │   │   └── settings/
│   │   │       └── page.tsx          # User settings
│   │   ├── components/               # Reusable UI components
│   │   │   ├── ui/                   # shadcn/ui base components
│   │   │   ├── charts/               # Chart components
│   │   │   │   ├── CandlestickChart.tsx
│   │   │   │   ├── PortfolioChart.tsx
│   │   │   │   └── CorrelationMatrix.tsx
│   │   │   ├── signals/
│   │   │   │   ├── SignalCard.tsx
│   │   │   │   └── SignalTable.tsx
│   │   │   └── portfolio/
│   │   │       ├── PositionList.tsx
│   │   │       └── RiskMetrics.tsx
│   │   ├── lib/                      # Utilities and API client
│   │   │   ├── api/                  # Auto-generated OpenAPI client
│   │   │   ├── hooks/                # Custom React hooks
│   │   │   └── utils.ts
│   │   └── styles/
│   │       └── globals.css
│   ├── public/
│   ├── package.json
│   ├── tsconfig.json
│   ├── tailwind.config.ts
│   ├── next.config.js
│   └── Dockerfile
│
├── docs/                             # Project documentation
│   ├── ARCHITECTURE.md               # This document
│   ├── API.md
│   ├── CI_CD_STRATEGY.md
│   └── SECURITY_FIXES.md
│
├── docker-compose.yml                # Full-stack local development
├── docker-compose.prod.yml           # Production compose
├── Makefile                          # Root-level orchestration
├── .github/
│   └── workflows/
│       ├── backend-tests.yml
│       ├── backend-quality.yml
│       ├── frontend-ci.yml
│       └── deploy.yml
├── README.md
└── .gitignore
```

### 4.2 Migration Path

The restructuring can happen **incrementally**:

1. **Phase 1**: Move current code into `backend/` (rename, update imports).
2. **Phase 2**: Scaffold `frontend/` with Next.js alongside.
3. **Phase 3**: Add `docker-compose.yml` for local full-stack dev.
4. **Phase 4**: Split CI workflows for backend and frontend.

The current code already has clean module boundaries (`app/core/`, `app/models/`, `app/api/`), so the move into `backend/` is mostly path changes.

---

## 5. Backend Restructuring

### 5.1 What Stays (Reused As-Is)

These modules contain the core domain logic and can be reused with minimal changes:

| Module | Lines | Change Needed |
|--------|-------|---------------|
| `app/core/indicators.py` | ~400 | None — pure calculation functions |
| `app/core/signal_generator.py` | ~500 | None — pure domain logic |
| `app/core/portfolio_analyzer.py` | ~400 | None — pure analysis functions |
| `app/core/portfolio_manager.py` | ~300 | None — pure domain logic |
| `app/core/data_manager.py` | ~400 | Minimal — update DB session handling |
| `app/models/*.py` | ~600 | None — SQLAlchemy 2.0 models work with FastAPI |
| `app/auth/service.py` | ~200 | Adapt JWT library calls |
| `migrations/` | ~300 | None — Alembic works independently |
| `scripts/*.py` | ~500 | None — CLI utilities are framework-agnostic |
| `tests/*.py` | ~1500 | Adapt test fixtures for FastAPI TestClient |

### 5.2 What Changes

| Component | Current | Target | Effort |
|-----------|---------|--------|--------|
| **Route handlers** | Flask `@app.route` + Flasgger docstrings | FastAPI `@router.get` + Pydantic models | Medium |
| **Auth middleware** | Flask-JWT-Extended decorators | FastAPI `Depends()` + `python-jose` | Medium |
| **Request validation** | Manual `request.args.get()` | Pydantic schemas (auto-validated) | Low |
| **App factory** | `create_app()` returning Flask | `create_app()` returning FastAPI | Low |
| **Config** | Custom `Config` class + `json.load` | Pydantic `BaseSettings` (env-aware) | Low |
| **Scheduling** | `schedule` library in a thread | APScheduler (DB-backed) | Low |

### 5.3 Incremental Migration Strategy

Since FastAPI can mount WSGI apps, the migration can be **gradual**:

```python
# Phase 1: FastAPI wraps existing Flask app
from fastapi import FastAPI
from fastapi.middleware.wsgi import WSGIMiddleware
from app import create_app as create_flask_app

app = FastAPI()
flask_app = create_flask_app()

# New endpoints on FastAPI
@app.get("/api/v2/signals")
async def get_signals(): ...

# Old endpoints still served by Flask
app.mount("/api", WSGIMiddleware(flask_app))
```

This means **zero downtime migration**: old endpoints keep working while new ones are added in FastAPI.

---

## 6. Frontend Architecture

### 6.1 Core Pages

| Page | URL | Description |
|------|-----|-------------|
| **Dashboard** | `/` | Overview: portfolio value, top signals, key risk metrics |
| **Signals** | `/signals` | Live signal feed with filters (ticker, type, confidence) |
| **Signal Detail** | `/signals/[ticker]` | Historical signals for a ticker with candlestick chart overlay |
| **Portfolio** | `/portfolio` | Position list, allocation pie chart, P&L table |
| **Risk** | `/risk` | Correlation heatmap, VaR gauge, stress test results |
| **Optimization** | `/optimization` | Portfolio optimizer with risk/return sliders |
| **Settings** | `/settings` | Account, API keys, notification preferences |
| **Login** | `/login` | Authentication page |

### 6.2 Key Frontend Components

```
components/
├── charts/
│   ├── CandlestickChart.tsx       # TradingView Lightweight Charts
│   ├── PortfolioLineChart.tsx     # Recharts — portfolio value over time
│   ├── AllocationPieChart.tsx     # Recharts — sector/ticker allocation
│   ├── CorrelationHeatmap.tsx     # Custom SVG or Recharts
│   └── VaRGauge.tsx              # Risk gauge visualization
├── signals/
│   ├── SignalCard.tsx             # Individual signal with confidence bar
│   ├── SignalTable.tsx            # Sortable/filterable signal list
│   └── SignalBadge.tsx            # BUY/SELL/HOLD badge
├── portfolio/
│   ├── PositionRow.tsx            # Single position with P&L
│   ├── PositionList.tsx           # Portfolio positions table
│   └── AddPositionDialog.tsx      # Modal to add/edit position
├── risk/
│   ├── RiskMetricsCard.tsx        # VaR, Sharpe, Max Drawdown
│   └── StressTestResults.tsx      # Stress test scenario table
└── layout/
    ├── Sidebar.tsx                # Navigation sidebar
    ├── Header.tsx                 # Top bar with user menu
    └── ThemeToggle.tsx            # Dark/light mode
```

### 6.3 Data Fetching Pattern

```typescript
// Use TanStack Query for server state management
// Auto-generated API client from OpenAPI spec

import { useQuery, useMutation } from '@tanstack/react-query';
import { SignalsApi, PortfolioApi } from '@/lib/api';

// Fetch signals with auto-refresh
export function useSignals(filters?: SignalFilters) {
  return useQuery({
    queryKey: ['signals', filters],
    queryFn: () => SignalsApi.getSignals(filters),
    refetchInterval: 30_000, // Auto-refresh every 30s
  });
}

// Add position with optimistic update
export function useAddPosition() {
  return useMutation({
    mutationFn: PortfolioApi.addPosition,
    onSuccess: () => queryClient.invalidateQueries(['portfolio']),
  });
}
```

---

## 7. API Layer Design

### 7.1 Versioning Strategy

Keep the current API as `v1` and introduce `v2` alongside:

```
/api/v1/signals         ← Current Flask routes (preserved during migration)
/api/v2/signals         ← New FastAPI routes (Pydantic schemas, async)
```

Once all consumers have migrated, deprecate and remove `v1`.

### 7.2 OpenAPI Client Generation

FastAPI auto-generates an OpenAPI spec. Use it to auto-generate the TypeScript client:

```bash
# In CI or as a Makefile target
npx openapi-typescript-codegen \
  --input http://localhost:8000/openapi.json \
  --output frontend/src/lib/api \
  --client fetch
```

This ensures the frontend API client is always in sync with the backend schema.

### 7.3 Authentication Flow

```
┌──────────┐     POST /api/v2/auth/login      ┌──────────┐
│ Frontend │  ──────────────────────────────►  │ Backend  │
│ (Next.js)│  ◄──────────────────────────────  │ (FastAPI)│
│          │     { access_token, refresh_token} │          │
│          │                                    │          │
│          │     GET /api/v2/signals            │          │
│          │     Authorization: Bearer <token>  │          │
│          │  ──────────────────────────────►  │          │
│          │  ◄──────────────────────────────  │          │
│          │     { signals: [...] }             │          │
└──────────┘                                    └──────────┘
```

- Access tokens: short-lived (15 min), stored in memory.
- Refresh tokens: longer-lived (7 days), stored in httpOnly cookie.
- Next.js middleware handles token refresh transparently.

---

## 8. Database Strategy

### 8.1 Environment-Based Configuration

```python
# backend/config/settings.py (Pydantic BaseSettings)
class Settings(BaseSettings):
    DATABASE_URL: str = "sqlite:///data/market_data.db"  # Default for dev
    
    class Config:
        env_file = ".env"

# Production .env
DATABASE_URL=postgresql://user:pass@db:5432/traderrr

# Test .env
DATABASE_URL=sqlite:///test.db
```

### 8.2 Schema Overview

The existing SQLAlchemy models already cover:

```
┌─────────────┐     ┌──────────────┐     ┌────────────────┐
│    User      │     │   Signal     │     │   MarketData   │
│─────────────│     │──────────────│     │────────────────│
│ id           │     │ id           │     │ id             │
│ username     │     │ ticker       │     │ ticker         │
│ password_hash│     │ signal_type  │     │ date           │
│ role         │     │ confidence   │     │ open/high/low  │
│ api_key      │     │ entry_price  │     │ close/volume   │
└─────────────┘     │ stop_loss    │     └────────────────┘
                     │ target_price │
                     │ regime       │
                     └──────────────┘
┌─────────────┐     ┌──────────────┐
│  Portfolio   │     │  AuditLog    │
│─────────────│     │──────────────│
│ id           │     │ id           │
│ user_id      │     │ user_id      │
│ ticker       │     │ action       │
│ shares       │     │ details      │
│ avg_price    │     │ timestamp    │
└─────────────┘     └──────────────┘
```

No schema changes needed for the restructuring — only the connection string changes.

---

## 9. Deployment & CI/CD Evolution

### 9.1 Docker Compose (Local Development)

```yaml
# docker-compose.yml
services:
  backend:
    build: ./backend
    ports:
      - "8000:8000"
    environment:
      - DATABASE_URL=postgresql://traderrr:traderrr@db:5432/traderrr
    depends_on:
      - db

  frontend:
    build: ./frontend
    ports:
      - "3000:3000"
    environment:
      - NEXT_PUBLIC_API_URL=http://localhost:8000

  db:
    image: postgres:16
    environment:
      POSTGRES_USER: traderrr
      POSTGRES_PASSWORD: traderrr
      POSTGRES_DB: traderrr
    volumes:
      - pgdata:/var/lib/postgresql/data

volumes:
  pgdata:
```

### 9.2 CI/CD Pipeline Evolution

```
Current:                          Target:
┌──────────────────┐              ┌──────────────────────────────────┐
│ tests.yml        │              │ backend-ci.yml                   │
│ code-quality.yml │    ──►       │   ├─ pytest                     │
│ CodeQL           │              │   ├─ black + mypy + pylint      │
└──────────────────┘              │   └─ CodeQL                     │
                                  │ frontend-ci.yml                  │
                                  │   ├─ eslint + prettier           │
                                  │   ├─ tsc (type check)            │
                                  │   ├─ jest/vitest                  │
                                  │   └─ build                       │
                                  │ e2e.yml                          │
                                  │   └─ Playwright (browser tests)  │
                                  │ deploy.yml                       │
                                  │   ├─ Docker build + push         │
                                  │   └─ Deploy to staging/prod      │
                                  └──────────────────────────────────┘
```

### 9.3 Cloud-Agnostic Deployment

Remove IBM Cloud–specific dependencies and target container-based deployment:

| Platform | Approach |
|----------|----------|
| **AWS** | ECS/Fargate + RDS (PostgreSQL) + CloudFront |
| **GCP** | Cloud Run + Cloud SQL + Cloud CDN |
| **Azure** | Container Apps + Azure Database for PostgreSQL |
| **Self-hosted** | Docker Compose + Nginx reverse proxy |
| **Railway / Render** | Simple container deploy (good for early stages) |

---

## 10. Roadmap

### Phase 0 — Foundation (Weeks 1–2)

> **Goal**: Restructure repo without breaking anything.

- [ ] Move existing code into `backend/` directory
- [ ] Update all import paths and CI workflows
- [ ] Scaffold `frontend/` with Next.js + TypeScript + Tailwind + shadcn/ui
- [ ] Add `docker-compose.yml` for local full-stack dev
- [ ] Update root `Makefile` with full-stack commands
- [ ] Verify all existing tests still pass

### Phase 1 — Frontend MVP (Weeks 3–6)

> **Goal**: A working web dashboard consuming the existing Flask API.

- [ ] Implement login/auth flow (JWT)
- [ ] Build Dashboard page (portfolio summary, top signals)
- [ ] Build Signals page (signal list, filters, signal detail)
- [ ] Build Portfolio page (position list, add/edit/remove)
- [ ] Integrate TradingView Lightweight Charts for candlestick view
- [ ] Add Recharts for portfolio value and allocation charts
- [ ] Auto-generate TypeScript API client from OpenAPI spec
- [ ] Add frontend CI (ESLint, Prettier, TypeScript checks, Vitest)
- [ ] PWA setup (`next-pwa` for mobile installability)

### Phase 2 — Backend Evolution (Weeks 7–10)

> **Goal**: Migrate API layer to FastAPI while preserving all core logic.

- [ ] Set up FastAPI alongside Flask (WSGI mount strategy)
- [ ] Migrate routes one-by-one to FastAPI with Pydantic schemas
- [ ] Replace `schedule` thread with APScheduler
- [ ] Add SSE endpoint for real-time signal/price updates
- [ ] Switch config to Pydantic `BaseSettings`
- [ ] Add PostgreSQL support to `docker-compose.yml`
- [ ] Update tests to use FastAPI `TestClient`
- [ ] Remove Flask once all routes are migrated
- [ ] Update CI for new backend structure

### Phase 3 — Polish & Production (Weeks 11–14)

> **Goal**: Production-ready full-stack deployment.

- [ ] Risk analysis page (correlation heatmap, VaR gauge, stress tests)
- [ ] Portfolio optimization page (interactive risk/return sliders)
- [ ] Dark/light theme
- [ ] Notification system (email alerts, in-app notifications)
- [ ] End-to-end tests with Playwright
- [ ] Production Docker images (multi-stage, minimal)
- [ ] Deploy pipeline (staging → production)
- [ ] Performance optimization (caching, lazy loading, code splitting)
- [ ] Documentation update (user guide, developer guide)

### Phase 4 — Companion App & Advanced Features (Weeks 15+)

> **Goal**: Mobile companion and advanced trading features.

- [ ] React Native companion app (or enhanced PWA)
- [ ] WebSocket upgrade for live order book / price streaming
- [ ] Celery + Redis for scalable background jobs
- [ ] Multi-user portfolio support (user-scoped data)
- [ ] Backtesting UI (visual backtest configuration and results)
- [ ] Alert system (price alerts, signal alerts via push notification)
- [ ] TimescaleDB for time-series data at scale

---

## Summary of Key Decisions — FINALISED 2026-03-01

| # | Decision | **Final choice** |
|---|----------|-----------------|
| 1 | Frontend framework | **React + Next.js 14** (App Router) |
| 2 | Repo structure | **Monorepo** — pnpm workspaces + Turborepo |
| 3 | Backend framework | **FastAPI** — clean rebuild (no Flask migration) |
| 4 | Production database | **PostgreSQL via Supabase** |
| 5 | Real-time transport | **WebSocket from day one** |
| 6 | Task scheduling | **Celery + Redis from day one** |
| 7 | Mobile strategy | **React Native (Expo) from day one** |

Implementation tracked in [PLAN.md](../PLAN.md) and GitHub issues #57–#75.

---

*This document should be reviewed by the team and updated as decisions are finalized. Each phase can be adjusted based on team capacity and priorities.*
