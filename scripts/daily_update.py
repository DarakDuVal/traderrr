#!/usr/bin/env python3
"""
scripts/daily_update.py
Daily update script for trading system
Run this via cron or scheduler
"""

import sys
import os
import logging
import argparse
from datetime import datetime

# Add project root to Python path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from app.core.data_manager import DataManager
from app.core.signal_generator import SignalGenerator
from app.core.portfolio_analyzer import PortfolioAnalyzer
from app.core.portfolio_manager import PortfolioManager
from config.settings import Config
from config.database import DatabaseConfig


def setup_logging(log_level="INFO"):
    """Setup logging configuration"""
    logging.basicConfig(
        level=getattr(logging, log_level),
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler("logs/daily_update.log", mode="a"),
        ],
    )
    return logging.getLogger(__name__)


def update_portfolio_data(
    dm: DataManager, pm: PortfolioManager, force_update: bool = False
):
    """Update portfolio data"""
    logger = logging.getLogger(__name__)

    try:
        logger.info("Starting portfolio data update")

        # Get tickers from portfolio manager
        tickers = pm.get_tickers()
        if not tickers:
            logger.warning("No portfolio positions configured")
            return {}

        # Update data for all portfolio tickers
        portfolio_data = dm.get_multiple_stocks(tickers, period="6mo", max_workers=5)

        if force_update:
            # Force update for recent data
            recent_data = dm.get_multiple_stocks(tickers, period="5d", max_workers=3)
            logger.info(f"Force updated recent data for {len(recent_data)} tickers")

        logger.info(f"Updated data for {len(portfolio_data)} tickers")
        return portfolio_data

    except Exception as e:
        logger.error(f"Portfolio data update failed: {e}")
        return {}


def generate_signals(dm: DataManager, sg: SignalGenerator, portfolio_data: dict):
    """Generate trading signals"""
    logger = logging.getLogger(__name__)

    try:
        logger.info("Generating trading signals")

        # Generate fresh signals
        signals = sg.generate_portfolio_signals(portfolio_data)

        # Log signals to database
        if signals:
            db_config = DatabaseConfig(Config.DATABASE_PATH)
            for signal in signals:
                try:
                    db_config.execute_query(
                        """
                        INSERT INTO signal_history 
                        (ticker, date, signal_type, confidence, entry_price, target_price, stop_loss, regime, reasons)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                        (
                            signal.ticker,
                            signal.timestamp.date(),
                            signal.signal_type.value,
                            signal.confidence,
                            signal.entry_price,
                            signal.target_price,
                            signal.stop_loss,
                            signal.regime.value,
                            ", ".join(signal.reasons),
                        ),
                    )
                except Exception as e:
                    logger.warning(f"Failed to log signal for {signal.ticker}: {e}")

        logger.info(f"Generated {len(signals)} signals")
        return signals

    except Exception as e:
        logger.error(f"Signal generation failed: {e}")
        return []


def analyze_portfolio_risk(
    pa: PortfolioAnalyzer, portfolio_data: dict, pm: PortfolioManager
):
    """Analyze portfolio risk metrics"""
    logger = logging.getLogger(__name__)

    try:
        logger.info("Analyzing portfolio risk")

        # Build price dict from portfolio data
        current_prices = {}
        for ticker in pm.get_tickers():
            if ticker in portfolio_data and not portfolio_data[ticker].empty:
                current_prices[ticker] = portfolio_data[ticker]["Close"].iloc[-1]
            else:
                current_prices[ticker] = 0

        # Calculate weights and total value from database
        weights = pm.get_weights(current_prices)
        total_value = pm.get_total_value(current_prices)

        # Calculate portfolio metrics
        metrics = pa.analyze_portfolio(portfolio_data, weights)

        # Calculate position risks
        position_risks = pa.calculate_position_risks(
            portfolio_data, weights, total_value
        )

        # Log portfolio performance
        db_config = DatabaseConfig(Config.DATABASE_PATH())
        try:
            db_config.execute_query(
                """
                INSERT INTO portfolio_performance
                (date, portfolio_value, daily_return, volatility, sharpe_ratio, max_drawdown)
                VALUES (?, ?, ?, ?, ?, ?)
            """,
                (
                    datetime.now().date(),
                    total_value,
                    metrics.daily_return,
                    metrics.volatility,
                    metrics.sharpe_ratio,
                    metrics.max_drawdown,
                ),
            )
        except Exception as e:
            logger.warning(f"Failed to log portfolio performance: {e}")

        # Check risk alerts
        risk_alerts = []
        if metrics.volatility > Config.VOLATILITY_LIMIT():
            risk_alerts.append(
                f"Portfolio volatility ({metrics.volatility:.1%}) exceeds limit"
            )

        if metrics.max_drawdown < -0.20:
            risk_alerts.append(f"Max drawdown ({metrics.max_drawdown:.1%}) exceeds 20%")

        # Check concentration risk
        high_concentration = [
            pos for pos in position_risks if pos.concentration_risk > 0.6
        ]
        if high_concentration:
            tickers = [pos.ticker for pos in high_concentration]
            risk_alerts.append(f"High concentration risk in: {', '.join(tickers)}")

        if risk_alerts:
            logger.warning("Risk alerts detected:")
            for alert in risk_alerts:
                logger.warning(f"  - {alert}")

                # Log system event
                db_config.log_system_event(
                    "RISK_ALERT",
                    alert,
                    f"Portfolio value: ${total_value:,.2f}",
                    "WARNING",
                )

        logger.info("Portfolio risk analysis completed")
        return metrics, position_risks, risk_alerts

    except Exception as e:
        logger.error(f"Portfolio risk analysis failed: {e}")
        return None, [], []


def send_notifications(signals: list, risk_alerts: list):
    """Send notifications for signals and alerts"""
    logger = logging.getLogger(__name__)

    try:
        # High confidence signals
        high_conf_signals = [s for s in signals if s.confidence > 0.8]

        if high_conf_signals:
            logger.info(f"High confidence signals detected: {len(high_conf_signals)}")
            for signal in high_conf_signals:
                logger.info(
                    f"  {signal.ticker}: {signal.signal_type.value} ({signal.confidence:.1%})"
                )

        # Risk alerts
        if risk_alerts:
            logger.warning(f"Risk alerts: {len(risk_alerts)}")
            for alert in risk_alerts:
                logger.warning(f"  {alert}")

        # TODO: Implement email/Slack notifications here
        # if Config.get('notifications.email_enabled'):
        #     send_email_notification(high_conf_signals, risk_alerts)

        # if Config.get('notifications.slack_enabled'):
        #     send_slack_notification(high_conf_signals, risk_alerts)

    except Exception as e:
        logger.error(f"Notification sending failed: {e}")


def cleanup_database(db_config: DatabaseConfig):
    """Clean up old database records"""
    logger = logging.getLogger(__name__)

    try:
        logger.info("Starting database cleanup")

        # Clean old data
        cleanup_stats = db_config.cleanup_old_data(
            days_to_keep=Config.get("data.data_retention_days", 730)
        )

        if "error" not in cleanup_stats:
            total_deleted = sum(cleanup_stats.values())
            logger.info(f"Cleaned up {total_deleted} old records")

            # Vacuum database
            if db_config.vacuum_database():
                logger.info("Database vacuum completed")

        # Log cleanup event
        db_config.log_system_event(
            "DATABASE_CLEANUP",
            f"Cleaned up {total_deleted} old records",
            str(cleanup_stats),
            "INFO",
        )

    except Exception as e:
        logger.error(f"Database cleanup failed: {e}")


def create_backup(dm: DataManager):
    """Create database backup"""
    logger = logging.getLogger(__name__)

    try:
        if Config.BACKUP_ENABLED():
            timestamp = datetime.now().strftime("%Y%m%d_%H%M")
            backup_path = f"backups/backup_{timestamp}.db"

            # Ensure backup directory exists
            os.makedirs("backups", exist_ok=True)

            dm.backup_database(backup_path)
            logger.info(f"Database backup created: {backup_path}")

            # Clean old backups (keep last 7 days)
            import glob

            backup_files = sorted(glob.glob("backups/backup_*.db"))
            if len(backup_files) > 7:
                for old_backup in backup_files[:-7]:
                    try:
                        os.remove(old_backup)
                        logger.info(f"Removed old backup: {old_backup}")
                    except Exception as e:
                        logger.warning(f"Failed to remove old backup {old_backup}: {e}")

    except Exception as e:
        logger.error(f"Backup creation failed: {e}")


def validate_system_health():
    """Validate system health"""
    logger = logging.getLogger(__name__)

    try:
        # Check database connectivity
        db_config = DatabaseConfig(Config.DATABASE_PATH())
        if not db_config.check_connection():
            logger.error("Database connection failed")
            return False

        # Check configuration
        config_issues = Config.validate_config()
        if config_issues:
            logger.warning("Configuration issues found:")
            for issue in config_issues:
                logger.warning(f"  - {issue}")

        # Check disk space
        import shutil

        disk_usage = shutil.disk_usage(os.path.dirname(Config.DATABASE_PATH()))
        free_percent = disk_usage.free / disk_usage.total * 100

        if free_percent < 10:
            logger.error(f"Low disk space: {free_percent:.1f}% free")
            return False
        elif free_percent < 20:
            logger.warning(f"Disk space warning: {free_percent:.1f}% free")

        logger.info("System health check passed")
        return True

    except Exception as e:
        logger.error(f"System health check failed: {e}")
        return False


def main():
    """Main update function"""
    parser = argparse.ArgumentParser(description="Daily trading system update")
    parser.add_argument(
        "--force-update", action="store_true", help="Force update of all data"
    )
    parser.add_argument(
        "--skip-backup", action="store_true", help="Skip database backup"
    )
    parser.add_argument(
        "--skip-cleanup", action="store_true", help="Skip database cleanup"
    )
    parser.add_argument(
        "--log-level",
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        help="Logging level",
    )

    args = parser.parse_args()

    # Setup logging
    os.makedirs("logs", exist_ok=True)
    logger = setup_logging(args.log_level)

    logger.info("=" * 50)
    logger.info("Starting daily trading system update")
    logger.info(
        f"Arguments: force_update={args.force_update}, skip_backup={args.skip_backup}"
    )

    try:
        # Validate system health
        if not validate_system_health():
            logger.error("System health check failed, aborting update")
            return 1

        # Initialize components
        dm = DataManager(db_path=Config.DATABASE_PATH())
        sg = SignalGenerator(min_confidence=Config.MIN_CONFIDENCE())
        pa = PortfolioAnalyzer()
        pm = PortfolioManager(db_path=Config.DATABASE_PATH())
        db_config = DatabaseConfig(Config.DATABASE_PATH())

        # Log update start
        db_config.log_system_event(
            "DAILY_UPDATE_START",
            "Daily update process started",
            f"Force update: {args.force_update}",
            "INFO",
        )

        # Update portfolio data
        portfolio_data = update_portfolio_data(dm, pm, force_update=args.force_update)

        if not portfolio_data:
            logger.error("No portfolio data available, aborting update")
            return 1

        # Generate signals
        signals = generate_signals(dm, sg, portfolio_data)

        # Analyze portfolio risk
        metrics, position_risks, risk_alerts = analyze_portfolio_risk(
            pa, portfolio_data, pm
        )

        # Send notifications
        send_notifications(signals, risk_alerts)

        # Create backup
        if not args.skip_backup:
            create_backup(dm)

        # Cleanup database
        if not args.skip_cleanup:
            cleanup_database(db_config)

        # Log update completion
        db_config.log_system_event(
            "DAILY_UPDATE_COMPLETE",
            "Daily update process completed successfully",
            f"Signals: {len(signals)}, Alerts: {len(risk_alerts)}",
            "INFO",
        )

        # Print summary
        logger.info("Daily update completed successfully:")
        logger.info(f"  - Updated data for {len(portfolio_data)} tickers")
        logger.info(f"  - Generated {len(signals)} signals")
        logger.info(f"  - Identified {len(risk_alerts)} risk alerts")

        if signals:
            high_conf = [s for s in signals if s.confidence > 0.7]
            logger.info(f"  - {len(high_conf)} high confidence signals")

        # Clean up
        dm.close()

        logger.info("=" * 50)
        return 0

    except Exception as e:
        logger.error(f"Daily update failed: {e}")

        # Log error event
        try:
            db_config = DatabaseConfig(Config.DATABASE_PATH)
            db_config.log_system_event(
                "DAILY_UPDATE_ERROR", "Daily update process failed", str(e), "ERROR"
            )
        except:
            pass

        return 1


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
