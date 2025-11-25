# ================================
# Makefile
# Development automation
# ================================
.PHONY: setup test clean run docker-build docker-run deploy

# Setup development environment
setup:
	python -m venv trading_env
	. trading_env/bin/activate && pip install -r requirements.txt
	. trading_env/bin/activate && pip install -r requirements-dev.txt
	mkdir -p data logs backups cache
	python -c "from config.database import DatabaseConfig; DatabaseConfig('data/market_data.db').init_database()"

# Run tests
test:
	python -m pytest tests/ -v

test-cov:
	python -m pytest tests/ --cov=app --cov-report=html

# Health checks
health:
	python scripts/health_check.py

health-api:
	python scripts/health_check.py --api

validate:
	python scripts/data_validator.py

# Development server
run:
	python main.py

# Populate sample data
sample-data:
	python utils/dev_tools.py --populate

# Quick test
quick-test:
	python utils/dev_tools.py --test

# Code quality
lint:
	flake8 app/ tests/ scripts/
	black --check app/ tests/ scripts/

format:
	black app/ tests/ scripts/

# Docker
docker-build:
	docker build -t traderrr .

docker-run:
	docker run -p 8080:8080 traderrr

# Backtest
backtest:
	python scripts/backtest.py --tickers AAPL MSFT GOOGL --capital 10000

# Clean up
clean:
	rm -rf __pycache__ .pytest_cache htmlcov
	find . -type f -name "*.pyc" -delete
	find . -type d -name "__pycache__" -delete

# Deploy to IBM Cloud
deploy:
	python scripts/deploy.py --registry-namespace your-namespace

# Full development workflow
dev-setup: setup sample-data test health
	@echo "🚀 Development environment ready!"
	@echo "Run 'make run' to start the application"