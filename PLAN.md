# Traderrr — Architecture Rebuild Plan

> **Status**: Approved
> **Date**: 2026-03-01
> **Reference**: [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)

---

## Decisions Made

| # | Topic | Decision |
|---|-------|----------|
| 1 | Frontend framework | **React + Next.js 14** (App Router) |
| 2 | Repository structure | **Monorepo** (pnpm workspaces + Turborepo) |
| 3 | Backend framework | **FastAPI** — clean rebuild, no incremental Flask migration |
| 4 | Production database | **PostgreSQL via Supabase** |
| 5 | Real-time transport | **WebSocket from day one** (no SSE phase) |
| 6 | Background jobs | **Celery + Redis from day one** (no APScheduler phase) |
| 7 | Mobile strategy | **React Native (Expo) from day one** |

---

## Target Stack

### Backend (`backend/`)
| Layer | Technology |
|-------|-----------|
| Framework | FastAPI (async, auto-OpenAPI, Pydantic) |
| ORM | SQLAlchemy 2.0 (preserved from current codebase) |
| Migrations | Alembic (preserved) |
| Auth | `python-jose` + `passlib[bcrypt]` |
| Database | PostgreSQL — Supabase in production, local Postgres in dev |
| Real-time | WebSocket (FastAPI native) |
| Task queue | Celery + Redis (worker + Beat scheduler) |
| Market data | yfinance + TA-Lib + pandas/numpy (preserved) |
| ASGI server | Uvicorn + Gunicorn |

### Frontend (`frontend/`)
| Layer | Technology |
|-------|-----------|
| Framework | Next.js 14+ (App Router, TypeScript) |
| Styling | Tailwind CSS + shadcn/ui |
| Data fetching | TanStack Query |
| API client | Auto-generated from FastAPI OpenAPI spec |
| Charts | TradingView Lightweight Charts + Recharts |
| Real-time | Native WebSocket hook |
| State | Zustand (global) + TanStack Query (server state) |

### Mobile (`mobile/`)
| Layer | Technology |
|-------|-----------|
| Framework | React Native (Expo) |
| Shared code | `packages/types`, `packages/api-client` |
| Auth | Expo SecureStore for token storage |
| Real-time | WebSocket (same backend endpoint as web) |

### Infrastructure
| Layer | Technology |
|-------|-----------|
| Containers | Docker + Docker Compose |
| Queue/cache | Redis |
| CI/CD | GitHub Actions (backend, frontend, mobile workflows) |
| Hosting (prod) | Cloud-agnostic (Docker-based; Supabase for DB) |

---

## Monorepo Structure

```
traderrr/
├── backend/                     # FastAPI backend
│   ├── app/
│   │   ├── main.py              # FastAPI app factory
│   │   ├── api/
│   │   │   ├── deps.py          # Shared dependencies (auth, db session)
│   │   │   └── routes/
│   │   │       ├── auth.py
│   │   │       ├── signals.py
│   │   │       ├── portfolio.py
│   │   │       ├── risk.py
│   │   │       └── admin.py
│   │   ├── core/                # Business logic — PRESERVED
│   │   │   ├── indicators.py
│   │   │   ├── signal_generator.py
│   │   │   ├── portfolio_manager.py
│   │   │   ├── portfolio_analyzer.py
│   │   │   └── data_manager.py
│   │   ├── models/              # SQLAlchemy models — PRESERVED
│   │   ├── schemas/             # Pydantic request/response schemas
│   │   ├── auth/                # JWT auth logic
│   │   ├── workers/             # Celery tasks
│   │   │   ├── celery_app.py
│   │   │   ├── market_data.py   # Replaces schedule thread
│   │   │   └── signals.py
│   │   └── ws/                  # WebSocket handlers
│   │       └── router.py
│   ├── config/
│   │   └── settings.py          # Pydantic BaseSettings
│   ├── migrations/              # Alembic — PRESERVED
│   ├── tests/                   # pytest — adapted for FastAPI
│   ├── bdd/                     # Behave BDD — PRESERVED
│   ├── Dockerfile
│   ├── Dockerfile.worker
│   └── pyproject.toml
│
├── frontend/                    # Next.js web app
│   ├── src/
│   │   ├── app/                 # App Router pages
│   │   │   ├── layout.tsx
│   │   │   ├── page.tsx         # Dashboard
│   │   │   ├── signals/page.tsx
│   │   │   ├── portfolio/page.tsx
│   │   │   ├── risk/page.tsx
│   │   │   └── login/page.tsx
│   │   ├── components/
│   │   │   ├── ui/              # shadcn/ui base components
│   │   │   ├── charts/          # Candlestick, portfolio, heatmap
│   │   │   ├── signals/         # SignalCard, SignalTable, SignalBadge
│   │   │   ├── portfolio/       # PositionList, AddPositionDialog
│   │   │   ├── risk/            # RiskMetricsCard, StressTestResults
│   │   │   └── layout/          # Sidebar, Header, ThemeToggle
│   │   ├── lib/
│   │   │   ├── api/             # Auto-generated OpenAPI client
│   │   │   ├── hooks/           # useWebSocket, useSignals, etc.
│   │   │   └── store/           # Zustand stores
│   │   └── styles/globals.css
│   ├── package.json
│   ├── tsconfig.json
│   ├── tailwind.config.ts
│   └── Dockerfile
│
├── mobile/                      # React Native (Expo)
│   ├── src/
│   │   ├── app/                 # Expo Router pages
│   │   │   ├── (auth)/login.tsx
│   │   │   ├── (tabs)/index.tsx      # Dashboard
│   │   │   ├── (tabs)/signals.tsx
│   │   │   └── (tabs)/portfolio.tsx
│   │   ├── components/
│   │   ├── hooks/
│   │   └── lib/
│   ├── app.json
│   └── package.json
│
├── packages/                    # Shared code (monorepo packages)
│   ├── types/                   # Shared TypeScript types
│   │   ├── src/index.ts
│   │   └── package.json
│   └── api-client/              # Generated API client (shared)
│       ├── src/
│       └── package.json
│
├── docker-compose.yml           # Full local dev stack
├── docker-compose.prod.yml
├── Makefile                     # Root orchestration
├── pnpm-workspace.yaml
├── turbo.json
├── .github/workflows/
│   ├── backend-ci.yml
│   ├── frontend-ci.yml
│   ├── mobile-ci.yml
│   └── deploy.yml
└── README.md
```

---

## Phases & Milestones

### Phase 0 — Monorepo Foundation
> Goal: Restructure repo, set up tooling, Docker stack — nothing breaks.

- [ ] Create monorepo structure (pnpm workspaces + Turborepo)
- [ ] Move existing backend code into `backend/`; update imports & CI paths
- [ ] Create `docker-compose.yml` (FastAPI + PostgreSQL + Redis + Celery worker + Celery Beat)
- [ ] Update GitHub Actions workflows for monorepo
- [ ] Create root `Makefile` (dev, test, build, lint targets)

### Phase 1 — FastAPI Backend
> Goal: Full backend rebuilt on FastAPI with WebSocket, Celery, Supabase.

- [ ] Scaffold FastAPI app structure with Pydantic BaseSettings
- [ ] Configure Supabase PostgreSQL (prod) + local Postgres (dev)
- [ ] Rebuild auth layer (JWT with python-jose / passlib)
- [ ] Port all API route handlers (signals, portfolio, risk, admin)
- [ ] Implement WebSocket endpoint (`/ws`) for real-time signal/price feed
- [ ] Set up Celery app + Redis; define tasks (market data fetch, signal generation)
- [ ] Migrate scheduled jobs from `schedule` thread → Celery Beat
- [ ] Update pytest suite for FastAPI `TestClient` + PostgreSQL fixture

### Phase 2 — Next.js Frontend
> Goal: Full web dashboard with real-time WebSocket updates.

- [ ] Scaffold Next.js 14 App Router (TypeScript, Tailwind, shadcn/ui)
- [ ] Auto-generate TypeScript API client from FastAPI OpenAPI spec
- [ ] Implement JWT auth flow (login, silent refresh, Next.js middleware)
- [ ] Build `useWebSocket` hook for real-time data
- [ ] Build Dashboard page (portfolio summary, top signals, key metrics)
- [ ] Build Signals page (live feed via WebSocket, filter, detail view)
- [ ] Build Portfolio page (positions list, add/edit/remove)
- [ ] Build Risk Analysis page (correlation heatmap, VaR gauge)
- [ ] Integrate TradingView Lightweight Charts (candlestick + signal overlay)
- [ ] Frontend CI (ESLint, TypeScript strict, Vitest, build check)

### Phase 3 — React Native App
> Goal: Mobile companion with feature parity on core screens.

- [ ] Scaffold Expo app in `mobile/`; configure Expo Router
- [ ] Extract shared `packages/types` and `packages/api-client` packages
- [ ] Implement auth (Expo SecureStore for JWT tokens)
- [ ] Build Dashboard screen (portfolio overview, top signals)
- [ ] Build Signals screen (real-time WebSocket feed)
- [ ] Build Portfolio screen (positions, add/remove)
- [ ] Mobile CI (Expo type check, lint, EAS build check)

### Phase 4 — Polish & Production
> Goal: Production-ready deployment, advanced features.

- [ ] Multi-stage production Docker images (minimal, hardened)
- [ ] Supabase production environment setup and migration
- [ ] Playwright E2E tests (web)
- [ ] Dark/light theme
- [ ] Notification system (in-app + push via Expo)
- [ ] Portfolio optimization UI (risk/return sliders)
- [ ] Backtesting UI (visual configuration + results)
- [ ] Production deploy pipeline (staging → production)

---

## Core Domain Logic — Preserved As-Is

These modules contain the trading logic and require no changes during the rebuild:

| Module | Purpose |
|--------|---------|
| `app/core/indicators.py` | 15+ technical indicators |
| `app/core/signal_generator.py` | Multi-strategy signal generation |
| `app/core/portfolio_analyzer.py` | Risk metrics (VaR, Sharpe, drawdown) |
| `app/core/portfolio_manager.py` | Position management |
| `app/core/data_manager.py` | Market data fetching (yfinance) |
| `app/models/*.py` | SQLAlchemy 2.0 models |
| `migrations/` | Alembic migration history |

---

## GitHub Issues Tracking

All implementation work is tracked as GitHub issues.
Phases are labeled `phase-0` through `phase-3`.
Areas are labeled `backend`, `frontend`, `mobile`, `infrastructure`.

See: [Open Issues](../../issues?q=is%3Aopen)
