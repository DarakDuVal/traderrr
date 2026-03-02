"""
Celery tasks for market data fetching.
"""

import logging

from app.workers.celery_app import celery_app

logger = logging.getLogger(__name__)


@celery_app.task(bind=True, max_retries=3, default_retry_delay=60)
def fetch_market_data(self, ticker: str) -> dict:
    """Fetch and store OHLCV data for a single ticker."""
    try:
        logger.info("Fetching market data for %s", ticker)
        from app.core.data_manager import DataManager
        from config.settings import get_settings

        settings = get_settings()
        # DataManager uses synchronous DB operations; fine for Celery workers
        dm = DataManager()
        data = dm.get_stock_data(ticker, period="1mo")
        dm.close()
        return {"ticker": ticker, "rows": len(data) if data is not None else 0}
    except Exception as exc:
        logger.error("fetch_market_data(%s) failed: %s", ticker, exc)
        raise self.retry(exc=exc)


@celery_app.task(bind=True, max_retries=3, default_retry_delay=60)
def fetch_all_tickers(self) -> dict:
    """Fan-out: dispatch fetch_market_data for each ticker."""
    try:
        logger.info("Dispatching fetch_market_data for all tickers")
        from app.core.portfolio_manager import PortfolioManager

        pm = PortfolioManager()
        tickers = pm.get_tickers() or []
        for ticker in tickers:
            fetch_market_data.delay(ticker)
        return {"dispatched": len(tickers)}
    except Exception as exc:
        logger.error("fetch_all_tickers failed: %s", exc)
        raise self.retry(exc=exc)


@celery_app.task
def cleanup_old_data() -> dict:
    """Daily data cleanup task."""
    logger.info("Running daily data cleanup")
    return {"status": "completed"}
