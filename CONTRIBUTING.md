# Contributing to Traderrr

Thank you for contributing. This document covers the development workflow for our monorepo.

---

## Repository Structure

```
traderrr/
├── backend/      Python (FastAPI, Celery, SQLAlchemy)
├── frontend/     TypeScript (Next.js 16 App Router)
├── mobile/       TypeScript (React Native / Expo)
├── packages/
│   ├── types/    Shared TypeScript interfaces
│   └── api-client/  Auto-generated from FastAPI OpenAPI spec
├── pnpm-workspace.yaml
└── turbo.json
```

When opening a PR, indicate which workspace(s) it touches in the description.

---

## Development Setup

### Prerequisites

- Python 3.11+
- Node.js 20+ and pnpm (`npm install -g pnpm`)
- Docker + Docker Compose (for the full local stack)

### Full stack (recommended)

```bash
cp .env.example .env    # fill in required values
docker compose up
```

### Backend only

```bash
cd backend
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements-dev.txt
pytest tests/ -v
```

### Frontend / Mobile

```bash
pnpm install            # installs all workspaces from repo root
pnpm --filter frontend dev
pnpm --filter mobile start
```

---

## Branching Strategy

We follow Simplified Git Flow:

```
main        Production-ready (protected)
  ↑
develop     Integration / staging (protected)
  ↑
feature/*   New features
bugfix/*    Bug fixes
hotfix/*    Critical production fixes (branch from main)
```

### Branch naming

- `feature/short-description` — e.g. `feature/websocket-endpoint`
- `bugfix/issue-name` — e.g. `bugfix/jwt-refresh-cookie`
- `hotfix/critical-issue` — e.g. `hotfix/cors-misconfiguration`

---

## Contributing Process

### New feature or non-critical fix

```bash
git checkout develop && git pull origin develop
git checkout -b feature/your-feature-name
# make changes
git push origin feature/your-feature-name
# open PR targeting develop
```

### Critical hotfix

```bash
git checkout main && git pull origin main
git checkout -b hotfix/critical-issue
# fix, test
# PR to main, then back-merge to develop
```

---

## Commit Messages

Format: `<type>: <description> (closes #<issue>)`

| Type | Use |
|------|-----|
| `feat` | New feature |
| `fix` | Bug fix |
| `refactor` | Code restructuring without behaviour change |
| `test` | Adding or updating tests |
| `docs` | Documentation only |
| `chore` | Build, CI, dependency updates |

**Good**: `feat: add WebSocket broadcast on signal generation (closes #64)`
**Bad**: `updated stuff`

---

## Code Quality Standards

### Backend (`backend/`)

```bash
make test        # pytest
make format      # black
make lint        # pylint + mypy
make test-cov    # pytest with coverage (target ≥ 80%)
```

Requirements:
- All tests pass
- `black --check` passes
- `mypy` in strict mode passes
- Pylint score ≥ 8.0
- Coverage ≥ 80% on `app/api/routes/`

### Frontend (`frontend/`) and Mobile (`mobile/`)

```bash
pnpm --filter <workspace> lint         # ESLint
pnpm --filter <workspace> type-check   # tsc --noEmit
pnpm --filter <workspace> test         # Vitest / Jest
pnpm --filter <workspace> build        # production build check
```

Requirements:
- ESLint passes with 0 errors
- TypeScript strict mode passes
- All tests pass

---

## Pull Request Guidelines

1. **Title**: `<type>: <short description> (closes #<issue>)` — max 70 chars
2. **Description** must include:
   - Which workspace(s) this touches
   - What problem it solves
   - How to test it
   - Any breaking changes
3. **Link issues**: use `Closes #123` to auto-close
4. All CI checks must pass before merge
5. At least one review approval required

---

## Useful Make Commands

```bash
make dev          # docker compose up (full stack)
make down         # docker compose down
make logs         # follow all service logs
make test         # pytest (backend)
make format       # black (backend)
make lint         # pylint + mypy (backend)
make gen-client   # regenerate TypeScript API client from FastAPI OpenAPI spec
```

---

## Questions

- Check existing issues before opening a new one
- Use GitHub Discussions for design questions or RFCs
- Review [PLAN.md](PLAN.md) for architecture context
