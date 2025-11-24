"""
config/settings.py - Configuration management
"""

import os
import json
from typing import Dict, List


class Config:
    """Base configuration class"""

    # Load from environment or config file
    _config_data = None

    @classmethod
    def _load_config(cls):
        """Load configuration from file"""
        if cls._config_data is None:
            config_path = os.getenv('CONFIG_PATH', 'config.json')
            try:
                with open(config_path, 'r') as f:
                    cls._config_data = json.load(f)
            except FileNotFoundError:
                cls._config_data = cls._get_default_config()
        return cls._config_data

    @classmethod
    def _get_default_config(cls) -> Dict:
        """Default configuration"""
        return {
            "portfolio": {
                "tickers": [
                    "AAPL", "META", "MSFT", "NVDA", "GOOGL",
                    "JPM", "BAC", "PG", "JNJ", "VTI", "SPY",
                    "SIEGY", "VWAGY", "SYIEY", "QTUM", "QBTS"
                ],
                "weights": {
                    "AAPL": 0.145, "META": 0.026, "MSFT": 0.020, "NVDA": 0.013,
                    "JPM": 0.077, "BAC": 0.026, "PG": 0.081, "JNJ": 0.018,
                    "VTI": 0.062, "SPY": 0.024, "SIEGY": 0.167, "VWAGY": 0.108,
                    "SYIEY": 0.069, "QTUM": 0.062, "QBTS": 0.062, "GOOGL": 0.022
                },
                "total_value": 19500,
                "rebalance_threshold": 0.05
            },
            "signals": {
                "min_confidence": 0.6,
                "momentum_threshold": 60.0,
                "mean_reversion_threshold": 70.0,
                "update_interval_minutes": 30
            },
            "risk": {
                "max_position_size": 0.20,
                "max_sector_concentration": 0.40,
                "var_confidence": 0.95,
                "max_correlation": 0.70,
                "volatility_limit": 0.25
            },
            "data": {
                "database_path": "data/market_data.db",
                "backup_enabled": True,
                "backup_interval_hours": 24,
                "data_retention_days": 730,
                "cache_enabled": True
            },
            "notifications": {
                "email_enabled": False,
                "email_address": "",
                "slack_enabled": False,
                "slack_webhook": "",
                "alert_threshold": 0.8
            },
            "api": {
                "host": "0.0.0.0",
                "port": 5000,
                "debug": False,
                "cors_enabled": True
            }
        }

    # Configuration properties as class methods
    @classmethod
    def PORTFOLIO_TICKERS(cls) -> List[str]:
        return cls._load_config()["portfolio"]["tickers"]

    @classmethod
    def PORTFOLIO_WEIGHTS(cls) -> Dict[str, float]:
        return cls._load_config()["portfolio"]["weights"]

    @classmethod
    def PORTFOLIO_VALUE(cls) -> float:
        return cls._load_config()["portfolio"]["total_value"]

    @classmethod
    def MIN_CONFIDENCE(cls) -> float:
        return cls._load_config()["signals"]["min_confidence"]

    @classmethod
    def DATABASE_PATH(cls) -> str:
        return os.getenv('DATABASE_PATH', cls._load_config()["data"]["database_path"])

    @classmethod
    def UPDATE_INTERVAL(cls) -> int:
        return cls._load_config()["signals"]["update_interval_minutes"]

    @classmethod
    def MOMENTUM_THRESHOLD(cls) -> float:
        return cls._load_config()["signals"]["momentum_threshold"]

    @classmethod
    def MEAN_REVERSION_THRESHOLD(cls) -> float:
        return cls._load_config()["signals"]["mean_reversion_threshold"]

    @classmethod
    def MAX_POSITION_SIZE(cls) -> float:
        return cls._load_config()["risk"]["max_position_size"]

    @classmethod
    def VOLATILITY_LIMIT(cls) -> float:
        return cls._load_config()["risk"]["volatility_limit"]

    @classmethod
    def BACKUP_ENABLED(cls) -> bool:
        return cls._load_config()["data"]["backup_enabled"]

    @classmethod
    def API_HOST(cls) -> str:
        return os.getenv('HOST', cls._load_config()["api"]["host"])

    @classmethod
    def API_PORT(cls) -> int:
        return int(os.getenv('PORT', cls._load_config()["api"]["port"]))

    @classmethod
    def get(cls, path: str, default=None):
        """Get configuration value by dot-separated path"""
        keys = path.split('.')
        value = cls._load_config()

        for key in keys:
            if isinstance(value, dict) and key in value:
                value = value[key]
            else:
                return default

        return value

    @classmethod
    def validate_config(cls) -> List[str]:
        """Validate configuration and return list of issues"""
        issues = []
        config = cls._load_config()

        # Validate portfolio weights sum to 1
        weights = config.get('portfolio', {}).get('weights', {})
        total_weight = sum(weights.values())
        if abs(total_weight - 1.0) > 0.01:
            issues.append(f"Portfolio weights sum to {total_weight:.3f}, not 1.0")

        # Validate tickers match weights
        tickers = set(config.get('portfolio', {}).get('tickers', []))
        weight_tickers = set(weights.keys())
        if tickers != weight_tickers:
            issues.append("Portfolio tickers don't match weight keys")

        # Validate risk parameters
        max_position = config.get('risk', {}).get('max_position_size', 0.2)
        if max_position <= 0 or max_position > 1:
            issues.append("Invalid max_position_size")

        # Validate signal parameters
        min_confidence = config.get('signals', {}).get('min_confidence', 0.6)
        if min_confidence <= 0 or min_confidence > 1:
            issues.append("Invalid min_confidence")

        return issues


# Environment-specific configurations
class DevelopmentConfig(Config):
    """Development configuration"""
    DEBUG = True
    TESTING = False

    @classmethod
    def DATABASE_PATH(cls) -> str:
        return "data/dev_market_data.db"

    @classmethod
    def API_PORT(cls) -> int:
        return 5000


class ProductionConfig(Config):
    """Production configuration"""
    DEBUG = False
    TESTING = False

    @classmethod
    def API_PORT(cls) -> int:
        return int(os.getenv('PORT', 8080))


class TestingConfig(Config):
    """Testing configuration"""
    DEBUG = True
    TESTING = True

    @classmethod
    def DATABASE_PATH(cls) -> str:
        return "data/test_market_data.db"

    @classmethod
    def MIN_CONFIDENCE(cls) -> float:
        return 0.3  # Lower threshold for testing


def get_config():
    """Get configuration based on environment"""
    env = os.getenv('FLASK_ENV', 'production')

    if env == 'development':
        return DevelopmentConfig
    elif env == 'testing':
        return TestingConfig
    else:
        return ProductionConfig