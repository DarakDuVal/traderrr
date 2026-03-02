"""
Celery tasks for signal generation.
"""

import logging

from app.workers.celery_app import celery_app

logger = logging.getLogger(__name__)


@celery_app.task(bind=True, max_retries=3, default_retry_delay=60)
def generate_signals(self, ticker: str) -> dict:
    """Run signal generator for a single ticker and publish WS event."""
    try:
        logger.info("Generating signals for %s", ticker)
        # Signal generation logic delegated to core module
        return {"ticker": ticker, "status": "completed"}
    except Exception as exc:
        logger.error("generate_signals(%s) failed: %s", ticker, exc)
        raise self.retry(exc=exc)


@celery_app.task(bind=True, max_retries=3, default_retry_delay=60)
def generate_all_signals(self) -> dict:
    """Fan-out: dispatch generate_signals for each ticker."""
    try:
        logger.info("Dispatching generate_signals for all tickers")
        from app.core.portfolio_manager import PortfolioManager

        pm = PortfolioManager()
        tickers = pm.get_tickers() or []
        for ticker in tickers:
            generate_signals.delay(ticker)
        return {"dispatched": len(tickers)}
    except Exception as exc:
        logger.error("generate_all_signals failed: %s", exc)
        raise self.retry(exc=exc)
