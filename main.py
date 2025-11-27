#!/usr/bin/env python3
"""
main.py - Main application entry point
Updated for structured project layout
"""

import os
import sys
import logging
import threading
import schedule
import time
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Add project root to Python path
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)

from app import create_app
from config.settings import get_config, Config
from config.database import DatabaseConfig


def setup_logging():
    """Setup application logging"""
    # Create logs directory
    os.makedirs("logs", exist_ok=True)

    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler("logs/trading_system.log", mode="a"),
        ],
    )

    return logging.getLogger(__name__)


def initialize_database():
    """Initialize database"""
    logger = logging.getLogger(__name__)

    try:
        db_config = DatabaseConfig(Config.DATABASE_PATH())

        if not db_config.init_database():
            logger.error("Database initialization failed")
            return False

        logger.info("Database initialized successfully")
        return True

    except Exception as e:
        logger.error(f"Database initialization error: {e}")
        return False


def initialize_data():
    """Initialize system with portfolio data"""
    logger = logging.getLogger(__name__)

    try:
        from app.core.data_manager import DataManager
        from app.core.signal_generator import SignalGenerator
        from app.core.portfolio_manager import PortfolioManager

        logger.info("Initializing system data...")

        # Initialize components
        dm = DataManager(db_path=Config.DATABASE_PATH())
        sg = SignalGenerator(min_confidence=Config.MIN_CONFIDENCE())
        pm = PortfolioManager(db_path=Config.DATABASE_PATH())

        # Get initial data for a subset of tickers (faster startup)
        all_tickers = pm.get_tickers()
        if not all_tickers:
            all_tickers = Config.PORTFOLIO_TICKERS()[:5]  # Fallback to config
        initial_tickers = all_tickers[:5]
        logger.info(f"Loading initial data for {len(initial_tickers)} tickers")

        portfolio_data = dm.get_multiple_stocks(initial_tickers, period="3mo")

        if portfolio_data:
            # Generate initial signals
            signals = sg.generate_portfolio_signals(portfolio_data)
            logger.info(f"Generated {len(signals)} initial signals")
        else:
            logger.warning("No initial portfolio data loaded")

        dm.close()
        logger.info("System data initialization completed")

    except Exception as e:
        logger.error(f"Data initialization error: {e}")


def run_scheduled_tasks():
    """Run scheduled background tasks"""
    logger = logging.getLogger(__name__)

    def update_portfolio_data():
        """Update portfolio data"""
        try:
            logger.info("Running scheduled portfolio data update")
            from scripts.daily_update import update_portfolio_data, generate_signals
            from app.core.data_manager import DataManager
            from app.core.signal_generator import SignalGenerator

            dm = DataManager(db_path=Config.DATABASE_PATH())
            sg = SignalGenerator(min_confidence=Config.MIN_CONFIDENCE())

            portfolio_data = update_portfolio_data(dm, force_update=False)
            signals = generate_signals(dm, sg, portfolio_data)

            dm.close()
            logger.info(f"Scheduled update completed: {len(signals)} signals")

        except Exception as e:
            logger.error(f"Scheduled update failed: {e}")

    def cleanup_task():
        """Daily cleanup task"""
        try:
            logger.info("Running daily cleanup")
            from scripts.daily_update import cleanup_database, create_backup
            from app.core.data_manager import DataManager

            db_config = DatabaseConfig(Config.DATABASE_PATH())
            dm = DataManager(db_path=Config.DATABASE_PATH())

            cleanup_database(db_config)
            create_backup(dm)

            dm.close()
            logger.info("Daily cleanup completed")

        except Exception as e:
            logger.error(f"Daily cleanup failed: {e}")

    # Schedule tasks
    schedule.every(Config.UPDATE_INTERVAL()).minutes.do(update_portfolio_data)
    schedule.every().day.at("02:00").do(cleanup_task)  # 2 AM daily cleanup
    schedule.every().day.at("09:00").do(update_portfolio_data)  # Market open
    schedule.every().day.at("15:30").do(update_portfolio_data)  # Before market close

    # Run scheduler
    while True:
        schedule.run_pending()
        time.sleep(60)


def start_scheduler():
    """Start background scheduler"""
    logger = logging.getLogger(__name__)

    try:
        logger.info("Starting background scheduler")
        scheduler_thread = threading.Thread(target=run_scheduled_tasks, daemon=True)
        scheduler_thread.start()
        logger.info("Background scheduler started")

    except Exception as e:
        logger.error(f"Failed to start scheduler: {e}")


def check_environment():
    """Check environment and dependencies"""
    logger = logging.getLogger(__name__)

    try:
        # Check Python version
        if sys.version_info < (3, 8):
            logger.error("Python 3.8 or higher required")
            return False

        # Check required directories
        required_dirs = ["data", "logs", "backups"]
        for directory in required_dirs:
            os.makedirs(directory, exist_ok=True)

        # Validate configuration
        config_issues = Config.validate_config()
        if config_issues:
            logger.warning("Configuration issues found:")
            for issue in config_issues:
                logger.warning(f"  - {issue}")

        # Check disk space
        import shutil

        disk_usage = shutil.disk_usage(".")
        free_gb = disk_usage.free / (1024**3)

        if free_gb < 1:
            logger.error(f"Insufficient disk space: {free_gb:.1f}GB free")
            return False
        elif free_gb < 5:
            logger.warning(f"Low disk space: {free_gb:.1f}GB free")

        logger.info("Environment check passed")
        return True

    except Exception as e:
        logger.error(f"Environment check failed: {e}")
        return False


def print_startup_info():
    """Print startup information"""
    from app.core.portfolio_manager import PortfolioManager

    logger = logging.getLogger(__name__)

    config_name = get_config().__name__.split(".")[-1]

    # Get portfolio info from database if available
    try:
        pm = PortfolioManager(db_path=Config.DATABASE_PATH())
        portfolio_tickers_count = len(pm.get_tickers())
        portfolio_source = "database"
    except:
        portfolio_tickers_count = len(Config.PORTFOLIO_TICKERS())
        portfolio_source = "config"

    startup_info = f"""
{'=' * 60}
>> Trading Signals System Starting
{'=' * 60}
Configuration: {config_name}
Database: {Config.DATABASE_PATH()}
Portfolio Tickers: {portfolio_tickers_count} ({portfolio_source})
Portfolio Value: Calculated dynamically from positions
Min Confidence: {Config.MIN_CONFIDENCE():.1%}
Update Interval: {Config.UPDATE_INTERVAL()} minutes
Host: {Config.API_HOST()}:{Config.API_PORT()}
{'=' * 60}
    """

    print(startup_info)
    logger.info("Trading system startup initiated")


def main():
    """Main application function"""
    # Setup logging first
    logger = setup_logging()

    try:
        # Print startup information
        print_startup_info()

        # Check environment
        if not check_environment():
            logger.error("Environment check failed, aborting startup")
            return 1

        # Initialize database
        if not initialize_database():
            logger.error("Database initialization failed, aborting startup")
            return 1

        # Initialize data (non-blocking)
        threading.Thread(target=initialize_data, daemon=True).start()

        # Get configuration
        config_class = get_config()

        # Create Flask app
        app = create_app()
        app.config.from_object(config_class)

        # Log system startup
        db_config = DatabaseConfig(Config.DATABASE_PATH())
        db_config.log_system_event(
            "SYSTEM_STARTUP",
            "Trading system started",
            f"Configuration: {config_class.__name__}",
            "INFO",
        )

        # Start background scheduler
        start_scheduler()

        # Start Flask application
        if os.getenv("FLASK_ENV") == "development":
            # Development mode - restrict to localhost for security
            # Using 127.0.0.1 instead of 0.0.0.0 prevents remote access to the
            # debug server and Werkzeug debugger (CWE-215, CWE-489)
            dev_host = "127.0.0.1"
            dev_port = Config.API_PORT()
            logger.info(
                f"Starting Flask development server on {dev_host}:{dev_port} "
                "(localhost only - for security)"
            )
            app.run(
                host=dev_host,  # Restrict to localhost only
                port=dev_port,
                debug=True,
                use_reloader=False,  # Disable reloader to avoid scheduler conflicts
            )
        else:
            # Production mode
            logger.info(f"Starting Flask application on {Config.API_HOST()}:{Config.API_PORT()}")
            try:
                import gunicorn

                logger.info("Starting with Gunicorn in production mode")

                # For production, we'll let gunicorn handle the startup
                # This main.py serves as the WSGI entry point
                return app

            except ImportError:
                logger.warning("Gunicorn not available, running with Flask development server")
                # Even in fallback, restrict to localhost for development
                app.run(host="127.0.0.1", port=Config.API_PORT(), debug=False)

        return 0

    except KeyboardInterrupt:
        logger.info("Shutdown requested by user")
        return 0

    except Exception as e:
        logger.error(f"Application startup failed: {e}")
        return 1


def create_wsgi_app():
    """Create WSGI application for Gunicorn"""
    logger = setup_logging()

    try:
        # Quick environment check
        if not check_environment():
            raise RuntimeError("Environment check failed")

        # Initialize database
        if not initialize_database():
            raise RuntimeError("Database initialization failed")

        # Get configuration
        config_class = get_config()

        # Create Flask app
        app = create_app()
        app.config.from_object(config_class)

        # Start background tasks
        start_scheduler()

        logger.info("WSGI application created successfully")
        return app

    except Exception as e:
        logger.error(f"WSGI application creation failed: {e}")
        raise


# WSGI entry point for Gunicorn
application = None


def get_wsgi_application():
    """Get WSGI application instance"""
    global application
    if application is None:
        application = create_wsgi_app()
    return application


if __name__ == "__main__":
    # Check if running under Gunicorn
    if "gunicorn" in os.environ.get("SERVER_SOFTWARE", ""):
        # Running under Gunicorn
        application = get_wsgi_application()
    else:
        # Running directly
        exit_code = main()
        if isinstance(exit_code, int):
            sys.exit(exit_code)
        else:
            # Return Flask app for development
            pass
