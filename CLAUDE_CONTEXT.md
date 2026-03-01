# Traderrr — Context for Claude Code

## Project

Algorithmic trading platform with regime-adaptive signal generation, portfolio management, and risk analysis. Currently being rebuilt into a full-stack monorepo. See [PLAN.md](PLAN.md) for the approved architecture.

## Target Tech Stack

- **Backend**: FastAPI, SQLAlchemy 2.0, Alembic, Celery + Redis, python-jose, passlib
- **Database**: PostgreSQL via Supabase (production); local Postgres (dev); SQLite (CI only)
- **Real-time**: WebSocket (FastAPI native)
- **Frontend**: Next.js 14 App Router, TypeScript strict, Tailwind CSS, shadcn/ui, TanStack Query
- **Mobile**: React Native (Expo), Expo Router
- **Shared packages**: `packages/types` (TS interfaces), `packages/api-client` (generated from FastAPI OpenAPI)
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

App is Flask-based (not yet in production). A clean FastAPI rebuild is in progress — no incremental migration needed. Existing 67+ unit tests and BDD scenarios will be adapted for FastAPI TestClient + PostgreSQL in #66.

## Active GitHub Issues

- Phase 0 (monorepo foundation): #57–#60
- Phase 1 (FastAPI backend): #61–#66
- Phase 2 (Next.js frontend): #67–#72
- Phase 3 (React Native): #73–#74
- Phase 4 (production): #75

## Key Conventions

- Python: Black (line length 100), Mypy strict, Pylint ≥ 8.0, pytest
- TypeScript: ESLint strict, Prettier, `tsc --strict`
- Commits: `<type>: <description> (closes #<issue>)`
- PRs target `develop`; hotfixes target `main`
- No Flask, SQLite (production), IBM Cloud, Jinja2, or Flasgger references in new code
