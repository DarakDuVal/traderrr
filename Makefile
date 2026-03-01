.PHONY: dev down logs install build test test-cov format lint gen-client clean

# ── Full stack (Docker Compose) ───────────────────────────────────────────────
dev:
	docker compose up

down:
	docker compose down

logs:
	docker compose logs -f

# ── JS/TS workspaces (pnpm) ───────────────────────────────────────────────────
install:
	pnpm install

build:
	pnpm turbo build

# ── Backend (Python) ──────────────────────────────────────────────────────────
# Note: paths update to backend/tests/ once #58 (monorepo restructure) lands
test:
	pytest tests/ -v

test-cov:
	pytest tests/ --cov=app --cov-report=term-missing --cov-fail-under=80

format:
	black app/ tests/

lint:
	pylint app/
	mypy app/

# ── API client generation ─────────────────────────────────────────────────────
# Requires backend running at localhost:8000 (make dev)
gen-client:
	npx @hey-api/openapi-ts \
	  --input http://localhost:8000/openapi.json \
	  --output packages/api-client/src \
	  --client fetch

# ── Utilities ─────────────────────────────────────────────────────────────────
clean:
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true
	rm -rf .pytest_cache htmlcov .mypy_cache
