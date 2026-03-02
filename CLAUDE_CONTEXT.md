# Traderrr — Context for Claude Code

## Project

Algorithmic trading platform with regime-adaptive signal generation, portfolio management, and risk analysis. Rebuilt as a full-stack monorepo. See [PLAN.md](PLAN.md) for the approved architecture.

## Tech Stack

- **Backend**: FastAPI, SQLAlchemy 2.0, Alembic, Celery + Redis, python-jose, passlib
- **Database**: PostgreSQL via Supabase (production); local Postgres (dev); SQLite (CI only)
- **Real-time**: WebSocket (FastAPI native)
- **Frontend**: Next.js 14 App Router, TypeScript strict, Tailwind CSS v4, shadcn/ui-style components, TanStack Query, Zustand, Recharts
- **Mobile**: React Native (Expo), Expo Router
- **Shared packages**: `packages/types` (TS interfaces), `packages/api-client` (typed fetch client)
- **Monorepo tooling**: pnpm workspaces + Turborepo
- **CI/CD**: GitHub Actions (backend-ci, frontend-ci, mobile-ci, deploy)

## Core Domain (Preserved — Do Not Rewrite)

These modules contain the trading logic and must be carried into `backend/app/core/` unchanged:

- `app/core/indicators.py` — 15+ technical indicators + market regime detection
- `app/core/signal_generator.py` — regime-adaptive dual-strategy signal generation
- `app/core/portfolio_analyzer.py` — VaR, Sharpe, Sortino, drawdown, correlation
- `app/core/portfolio_manager.py` — position management
- `app/core/data_manager.py` — yfinance data fetching
- `app/models/` — SQLAlchemy 2.0 models
- `migrations/` — Alembic history

## Current State

Phase 0 (monorepo), Phase 1 (FastAPI backend), and Phase 2 (Next.js frontend) are complete. The backend provides REST APIs + WebSocket, and the frontend has a full dashboard with real-time updates, JWT auth, and portfolio management.

### Frontend Architecture (`frontend/src/`)

- **Pages**: Dashboard (`/`), Signals (`/signals`), Portfolio (`/portfolio`), Risk (`/risk`), Login (`/login`), Settings (`/settings`)
- **State**: Zustand for auth (`lib/store/auth.ts`), TanStack Query for server state
- **API**: Typed client in `packages/api-client`, singleton in `lib/api.ts`
- **Real-time**: WebSocket hook (`lib/hooks/useWebSocket.ts`) with signal/price stream hooks
- **Auth**: JWT flow — login page, Zustand store, silent refresh, Next.js middleware route protection
- **Components**: shadcn/ui-style in `components/ui/`, domain components in `components/{signals,portfolio,risk,dashboard,charts,shared}/`

## Active GitHub Issues

- Phase 0 (monorepo foundation): #57–#60 ✅
- Phase 1 (FastAPI backend): #61–#66 ✅
- Phase 2 (Next.js frontend): #67–#72 ✅
- Phase 3 (React Native): #73–#74
- Phase 4 (production): #75

## Key Conventions

- Python: Black (line length 100), Mypy strict, Pylint ≥ 8.0, pytest
- TypeScript: ESLint strict, `tsc --strict`, Tailwind CSS v4 with `@custom-variant dark`
- Commits: `<type>: <description> (closes #<issue>)`
- PRs target `develop`; hotfixes target `main`
- No Flask, SQLite (production), IBM Cloud, Jinja2, or Flasgger references in new code
