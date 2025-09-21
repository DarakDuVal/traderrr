"""
Testing Framework and Configuration Management
"""

import unittest
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import tempfile
import os
import json
from unittest.mock import patch, MagicMock
import sqlite3

# Import our modules (assuming they're in the same directory)
from data_manager import DataManager
from indicators import TechnicalIndicators, MarketRegimeDetector
from signal_generator import SignalGenerator, SignalType, MarketRegime
from portfolio_analyzer import PortfolioAnalyzer

class TestDataManager(unittest.TestCase):
    """Test cases for DataManager"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.temp_db = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
        self.temp_db.close()
        self.dm = DataManager(db_path=self.temp_db.name)
        
        # Create sample data
        self.sample_dates = pd.date_range('2023-01-01', periods=100, freq='D')
        self.sample_prices = 100 + np.cumsum(np.random.normal(0.1, 2, 100))
        self.sample_data = pd.DataFrame({
            'Open': self.sample_prices * 0.99,
            'High': self.sample_prices * 1.02,
            'Low': self.sample_prices * 0.98,
            'Close': self.sample_prices,
            'Volume': np.random.randint(1000000, 5000000, 100),
            'Dividends': np.zeros(100),
            'Stock Splits': np.zeros(100)
        }, index=self.sample_dates)
    
    def tearDown(self):
        """Clean up test fixtures"""
        self.dm.close()
        os.unlink(self.temp_db.name)
    
    def test_database_creation(self):
        """Test database table creation"""
        conn = sqlite3.connect(self.temp_db.name)
        cursor = conn.cursor()
        
        # Check if tables exist
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [row[0] for row in cursor.fetchall()]
        
        expected_tables = ['daily_data', 'intraday_data', 'metadata', 'signal_history']
        for table in expected_tables:
            self.assertIn(table, tables)
        
        conn.close()
    
    def test_data_storage_and_retrieval(self):
        """Test storing and retrieving data"""
        # Store sample data
        self.dm._store_data('TEST', self.sample_data, '1d')
        
        # Retrieve data
        retrieved_data = self.dm._get_cached_data('TEST', '1d')
        
        self.assertIsNotNone(retrieved_data)
        self.assertEqual(len(retrieved_data), len(self.sample_data))
        self.assertAlmostEqual(
            retrieved_data['Close'].iloc[-1], 
            self.sample_data['Close'].iloc[-1], 
            places=2
        )
    
    def test_data_cleaning(self):
        """Test data cleaning functionality"""
        # Create dirty data with NaN and outliers
        dirty_data = self.sample_data.copy()
        dirty_data.loc[dirty_data.index[10], 'Close'] = np.nan
        dirty_data.loc[dirty_data.index[20], 'Close'] = 1000000  # Outlier
        
        cleaned_data = self.dm._clean_data(dirty_data)
        
        # Check that NaN values are handled
        self.assertFalse(cleaned_data['Close'].isna().all())
        
        # Check that outliers are removed
        self.assertLess(len(cleaned_data), len(dirty_data))
    
    @patch('yfinance.Ticker')
    def test_get_stock_data_with_mock(self, mock_ticker):
        """Test getting stock data with mocked yfinance"""
        # Mock yfinance response
        mock_stock = MagicMock()
        mock_stock.history.return_value = self.sample_data
        mock_stock.info = {'longName': 'Test Company', 'sector': 'Technology'}
        mock_ticker.return_value = mock_stock
        
        # Test data retrieval
        data = self.dm.get_stock_data('TEST', period="1y", force_update=True)
        
        self.assertFalse(data.empty)
        self.assertEqual(len(data), len(self.sample_data))
        mock_ticker.assert_called_once_with('TEST')
    
    def test_data_quality_report(self):
        """Test data quality reporting"""
        # Store some test data
        self.dm._store_data('TEST1', self.sample_data, '1d')
        self.dm._store_data('TEST2', self.sample_data.iloc[:50], '1d')  # Partial data
        
        # Generate quality report
        report = self.dm.get_data_quality_report(['TEST1', 'TEST2', 'MISSING'])
        
        self.assertEqual(report['tickers_checked'], 3)
        self.assertGreaterEqual(report['successful_downloads'], 2)
        self.assertIn('MISSING', report['missing_data'])


class TestTechnicalIndicators(unittest.TestCase):
    """Test cases for TechnicalIndicators"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.ti = TechnicalIndicators()
        
        # Create trending sample data
        dates = pd.date_range('2023-01-01', periods=100, freq='D')
        trend = np.linspace(100, 150, 100)
        noise = np.random.normal(0, 2, 100)
        self.trending_prices = pd.Series(trend + noise, index=dates)
        
        # Create mean-reverting sample data
        mean_reverting = 100 + np.sin(np.linspace(0, 4*np.pi, 100)) * 10 + noise
        self.mean_reverting_prices = pd.Series(mean_reverting, index=dates)
        
        # OHLC data
        self.ohlc_data = pd.DataFrame({
            'Open': self.trending_prices * 0.99,
            'High': self.trending_prices * 1.02,
            'Low': self.trending_prices * 0.98,
            'Close': self.trending_prices,
            'Volume': np.random.randint(1000000, 5000000, 100)
        })
    
    def test_rsi_calculation(self):
        """Test RSI calculation"""
        rsi = self.ti.rsi(self.trending_prices, period=14)
        
        # RSI should be between 0 and 100
        self.assertTrue((rsi >= 0).all())
        self.assertTrue((rsi <= 100).all())
        
        # For trending data, RSI should generally be above 50
        recent_rsi = rsi.tail(20).mean()
        self.assertGreater(recent_rsi, 45)  # Allow some tolerance
    
    def test_macd_calculation(self):
        """Test MACD calculation"""
        macd_line, signal_line, histogram = self.ti.macd(self.trending_prices)
        
        # Check that all series have same length (excluding NaN)
        self.assertEqual(len(macd_line.dropna()), len(signal_line.dropna()))
        self.assertEqual(len(signal_line.dropna()), len(histogram.dropna()))
        
        # For trending data, MACD should eventually turn positive
        self.assertGreater(macd_line.iloc[-1], macd_line.iloc[-50])
    
    def test_bollinger_bands(self):
        """Test Bollinger Bands calculation"""
        upper, middle, lower = self.ti.bollinger_bands(self.trending_prices)
        
        # Upper band should be above middle, middle above lower
        self.assertTrue((upper > middle).all())
        self.assertTrue((middle > lower).all())
        
        # Most prices should be within bands
        within_bands = ((self.trending_prices >= lower) & 
                       (self.trending_prices <= upper))
        self.assertGreater(within_bands.sum() / len(within_bands), 0.8)
    
    def test_atr_calculation(self):
        """Test Average True Range calculation"""
        atr = self.ti.atr(
            self.ohlc_data['High'], 
            self.ohlc_data['Low'], 
            self.ohlc_data['Close']
        )
        
        # ATR should be positive
        self.assertTrue((atr > 0).all())
        
        # ATR should have no NaN in the calculated period
        self.assertFalse(atr.iloc[14:].isna().any())


class TestMarketRegimeDetector(unittest.TestCase):
    """Test cases for MarketRegimeDetector"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.detector = MarketRegimeDetector()
        
        # Create different regime data
        dates = pd.date_range('2023-01-01', periods=100, freq='D')
        
        # Trending data
        trend = np.linspace(100, 150, 100)
        noise = np.random.normal(0, 1, 100)
        self.trending_data = pd.Series(trend + noise, index=dates)
        
        # Mean-reverting data
        mean_rev = 100 + np.sin(np.linspace(0, 8*np.pi, 100)) * 5 + noise
        self.mean_reverting_data = pd.Series(mean_rev, index=dates)
        
        # Random walk data
        random_walk = 100 + np.cumsum(np.random.normal(0, 1, 100))
        self.random_data = pd.Series(random_walk, index=dates)
    
    def test_hurst_exponent_trending(self):
        """Test Hurst exponent for trending data"""
        hurst = self.detector.hurst_exponent(self.trending_data)
        
        # Trending data should have Hurst > 0.5
        self.assertGreater(hurst, 0.5)
        self.assertLess(hurst, 1.0)
    
    def test_hurst_exponent_mean_reverting(self):
        """Test Hurst exponent for mean-reverting data"""
        hurst = self.detector.hurst_exponent(self.mean_reverting_data)
        
        # Mean-reverting data should have Hurst < 0.5
        self.assertLess(hurst, 0.5)
        self.assertGreater(hurst, 0.0)
    
    def test_trend_strength(self):
        """Test trend strength calculation"""
        trending_strength = self.detector.trend_strength(self.trending_data)
        random_strength = self.detector.trend_strength(self.random_data)
        
        # Trending data should have higher trend strength
        self.assertGreater(trending_strength, random_strength)
        self.assertLessEqual(trending_strength, 1.0)
        self.assertGreaterEqual(trending_strength, 0.0)
    
    def test_volatility_regime(self):
        """Test volatility regime detection"""
        # Create high volatility data
        high_vol_data = self.trending_data + np.random.normal(0, 10, 100)
        
        vol_regime = self.detector.volatility_regime(high_vol_data)
        self.assertIn(vol_regime, ['low', 'normal', 'high'])


class TestSignalGenerator(unittest.TestCase):
    """Test cases for SignalGenerator"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.signal_gen = SignalGenerator(min_confidence=0.5)
        
        # Create sample OHLCV data
        dates = pd.date_range('2023-01-01', periods=100, freq='D')
        base_prices = 100 + np.cumsum(np.random.normal(0.1, 2, 100))
        
        self.sample_data = pd.DataFrame({
            'Open': base_prices * 0.99,
            'High': base_prices * 1.02,
            'Low': base_prices * 0.98,
            'Close': base_prices,
            'Volume': np.random.randint(1000000, 5000000, 100)
        }, index=dates)
        
        # Create bullish data (strong uptrend)
        bullish_trend = np.linspace(100, 150, 100)
        self.bullish_data = pd.DataFrame({
            'Open': bullish_trend * 0.99,
            'High': bullish_trend * 1.02,
            'Low': bullish_trend * 0.98,
            'Close': bullish_trend,
            'Volume': np.random.randint(1000000, 5000000, 100)
        }, index=dates)
    
    def test_signal_generation(self):
        """Test basic signal generation"""
        signal = self.signal_gen.generate_signal('TEST', self.sample_data)
        
        # Signal might be None if no clear signal detected
        if signal is not None:
            self.assertIn(signal.signal_type, [
                SignalType.BUY, SignalType.SELL, SignalType.STRONG_BUY, 
                SignalType.STRONG_SELL, SignalType.HOLD
            ])
            self.assertGreaterEqual(signal.confidence, 0.5)
            self.assertGreater(signal.entry_price, 0)
            self.assertIsInstance(signal.reasons, list)
            self.assertGreater(len(signal.reasons), 0)
    
    def test_bullish_signal_detection(self):
        """Test detection of bullish signals in trending data"""
        signal = self.signal_gen.generate_signal('BULLISH_TEST', self.bullish_data)
        
        # Should generate some kind of signal for strong trend
        self.assertIsNotNone(signal)
        
        # In a strong uptrend, should be more likely to generate buy signal
        if signal.signal_type in [SignalType.BUY, SignalType.STRONG_BUY]:
            self.assertGreater(signal.confidence, 0.5)
    
    def test_portfolio_signals(self):
        """Test portfolio signal generation"""
        portfolio_data = {
            'TEST1': self.sample_data,
            'TEST2': self.bullish_data,
            'TEST3': self.sample_data.copy()
        }
        
        signals = self.signal_gen.generate_portfolio_signals(portfolio_data)
        
        # Should return a list
        self.assertIsInstance(signals, list)
        
        # Signals should be sorted by confidence (highest first)
        if len(signals) > 1:
            for i in range(len(signals) - 1):
                self.assertGreaterEqual(signals[i].confidence, signals[i+1].confidence)
    
    def test_signal_summary(self):
        """Test signal summary generation"""
        portfolio_data = {
            'TEST1': self.sample_data,
            'TEST2': self.bullish_data
        }
        
        signals = self.signal_gen.generate_portfolio_signals(portfolio_data)
        summary = self.signal_gen.get_signal_summary(signals)
        
        # Check summary structure
        required_keys = ['total_signals', 'buy_signals', 'sell_signals', 
                        'average_confidence', 'top_picks']
        for key in required_keys:
            self.assertIn(key, summary)
        
        # Check data consistency
        self.assertEqual(summary['total_signals'], len(signals))
        self.assertEqual(
            summary['buy_signals'] + summary['sell_signals'], 
            len([s for s in signals if s.signal_type != SignalType.HOLD])
        )


class TestPortfolioAnalyzer(unittest.TestCase):
    """Test cases for PortfolioAnalyzer"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.analyzer = PortfolioAnalyzer()
        
        # Create sample portfolio data
        dates = pd.date_range('2023-01-01', periods=252, freq='D')  # 1 year
        
        # Different asset types
        tech_stock = 100 + np.cumsum(np.random.normal(0.08/252, 0.25/np.sqrt(252), 252))
        financial_stock = 100 + np.cumsum(np.random.normal(0.06/252, 0.20/np.sqrt(252), 252))
        bond_etf = 100 + np.cumsum(np.random.normal(0.03/252, 0.05/np.sqrt(252), 252))
        
        self.portfolio_data = {
            'TECH': pd.DataFrame({
                'Open': tech_stock * 0.99,
                'High': tech_stock * 1.02,
                'Low': tech_stock * 0.98,
                'Close': tech_stock,
                'Volume': np.random.randint(1000000, 5000000, 252)
            }, index=dates),
            'FINANCIAL': pd.DataFrame({
                'Open': financial_stock * 0.99,
                'High': financial_stock * 1.02,
                'Low': financial_stock * 0.98,
                'Close': financial_stock,
                'Volume': np.random.randint(1000000, 5000000, 252)
            }, index=dates),
            'BOND': pd.DataFrame({
                'Open': bond_etf * 0.999,
                'High': bond_etf * 1.005,
                'Low': bond_etf * 0.995,
                'Close': bond_etf,
                'Volume': np.random.randint(1000000, 5000000, 252)
            }, index=dates)
        }
        
        self.portfolio_weights = {'TECH': 0.5, 'FINANCIAL': 0.3, 'BOND': 0.2}
    
    def test_portfolio_analysis(self):
        """Test portfolio metrics calculation"""
        metrics = self.analyzer.analyze_portfolio(
            self.portfolio_data, 
            self.portfolio_weights
        )
        
        # Check that metrics are reasonable
        self.assertIsInstance(metrics.volatility, float)
        self.assertGreater(metrics.volatility, 0)
        self.assertLess(metrics.volatility, 1.0)  # Should be less than 100%
        
        self.assertIsInstance(metrics.sharpe_ratio, float)
        self.assertIsInstance(metrics.max_drawdown, float)
        self.assertLess(metrics.max_drawdown, 0)  # Should be negative
        
        self.assertIsInstance(metrics.value_at_risk, float)
        self.assertLess(metrics.value_at_risk, 0)  # Should be negative
    
    def test_position_risk_calculation(self):
        """Test position risk metrics"""
        position_risks = self.analyzer.calculate_position_risks(
            self.portfolio_data,
            self.portfolio_weights,
            100000  # $100k portfolio
        )
        
        self.assertEqual(len(position_risks), len(self.portfolio_weights))
        
        for pos_risk in position_risks:
            self.assertGreater(pos_risk.position_size, 0)
            self.assertGreaterEqual(pos_risk.liquidity_score, 0)
            self.assertLessEqual(pos_risk.liquidity_score, 1)
            self.assertGreaterEqual(pos_risk.concentration_risk, 0)
            self.assertLessEqual(pos_risk.concentration_risk, 1)
    
    def test_correlation_matrix(self):
        """Test correlation matrix calculation"""
        corr_matrix = self.analyzer.calculate_correlation_matrix(self.portfolio_data)
        
        self.assertFalse(corr_matrix.empty)
        self.assertEqual(corr_matrix.shape[0], len(self.portfolio_data))
        self.assertEqual(corr_matrix.shape[1], len(self.portfolio_data))
        
        # Diagonal should be 1 (perfect self-correlation)
        np.testing.assert_array_almost_equal(np.diag(corr_matrix), 1.0)
    
    def test_portfolio_optimization(self):
        """Test portfolio optimization"""
        optimized_weights = self.analyzer.optimize_portfolio(
            self.portfolio_data,
            self.portfolio_weights,
            risk_tolerance=0.15
        )
        
        # Should return a dictionary
        self.assertIsInstance(optimized_weights, dict)
        
        # Weights should sum to approximately 1
        total_weight = sum(optimized_weights.values())
        self.assertAlmostEqual(total_weight, 1.0, places=2)
        
        # All weights should be non-negative
        for weight in optimized_weights.values():
            self.assertGreaterEqual(weight, 0)
    
    def test_risk_report_generation(self):
        """Test comprehensive risk report"""
        risk_report = self.analyzer.generate_risk_report(
            self.portfolio_data,
            self.portfolio_weights,
            100000
        )
        
        # Check report structure
        required_sections = [
            'timestamp', 'portfolio_metrics', 'position_risks',
            'correlation_summary', 'sector_concentration', 
            'stress_scenarios', 'recommendations'
        ]
        
        for section in required_sections:
            self.assertIn(section, risk_report)
        
        # Check that recommendations is a list
        self.assertIsInstance(risk_report['recommendations'], list)
        self.assertGreater(len(risk_report['recommendations']), 0)


class ConfigManager:
    """Configuration management for the trading system"""
    
    def __init__(self, config_path: str = "config.json"):
        self.config_path = config_path
        self.config = self._load_config()
    
    def _load_config(self) -> dict:
        """Load configuration from file"""
        default_config = {
            "portfolio": {
                "tickers": [
                    "AAPL", "META", "MSFT", "NVDA", "GOOGL",
                    "JPM", "BAC", "PG", "JNJ", "KO",
                    "VTI", "SPY", "SIEGY", "VWAGY", "SYIEY"
                ],
                "weights": {
                    "AAPL": 0.15, "META": 0.10, "MSFT": 0.10,
                    "NVDA": 0.05, "GOOGL": 0.05, "JPM": 0.10,
                    "BAC": 0.05, "PG": 0.05, "JNJ": 0.05,
                    "KO": 0.05, "VTI": 0.15, "SPY": 0.05,
                    "SIEGY": 0.05, "VWAGY": 0.03, "SYIEY": 0.02
                },
                "total_value": 50000,
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
                "database_path": "market_data.db",
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
        
        try:
            if os.path.exists(self.config_path):
                with open(self.config_path, 'r') as f:
                    loaded_config = json.load(f)
                # Merge with defaults
                self._deep_merge(default_config, loaded_config)
            
            return default_config
            
        except Exception as e:
            print(f"Error loading config: {e}. Using defaults.")
            return default_config
    
    def _deep_merge(self, base: dict, overlay: dict):
        """Deep merge overlay into base dictionary"""
        for key, value in overlay.items():
            if key in base and isinstance(base[key], dict) and isinstance(value, dict):
                self._deep_merge(base[key], value)
            else:
                base[key] = value
    
    def save_config(self):
        """Save current configuration to file"""
        try:
            with open(self.config_path, 'w') as f:
                json.dump(self.config, f, indent=2)
        except Exception as e:
            print(f"Error saving config: {e}")
    
    def get(self, path: str, default=None):
        """Get configuration value by dot-separated path"""
        keys = path.split('.')
        value = self.config
        
        for key in keys:
            if isinstance(value, dict) and key in value:
                value = value[key]
            else:
                return default
        
        return value
    
    def set(self, path: str, value):
        """Set configuration value by dot-separated path"""
        keys = path.split('.')
        config = self.config
        
        for key in keys[:-1]:
            if key not in config:
                config[key] = {}
            config = config[key]
        
        config[keys[-1]] = value
    
    def validate_config(self) -> List[str]:
        """Validate configuration and return list of issues"""
        issues = []
        
        # Validate portfolio weights sum to 1
        weights = self.get('portfolio.weights', {})
        total_weight = sum(weights.values())
        if abs(total_weight - 1.0) > 0.01:
            issues.append(f"Portfolio weights sum to {total_weight:.3f}, not 1.0")
        
        # Validate tickers match weights
        tickers = set(self.get('portfolio.tickers', []))
        weight_tickers = set(weights.keys())
        if tickers != weight_tickers:
            issues.append("Portfolio tickers don't match weight keys")
        
        # Validate risk parameters
        max_position = self.get('risk.max_position_size', 0.2)
        if max_position <= 0 or max_position > 1:
            issues.append("Invalid max_position_size")
        
        # Validate signal parameters
        min_confidence = self.get('signals.min_confidence', 0.6)
        if min_confidence <= 0 or min_confidence > 1:
            issues.append("Invalid min_confidence")
        
        return issues


# Performance benchmarking
class PerformanceBenchmark:
    """Benchmark system performance"""
    
    @staticmethod
    def benchmark_data_manager():
        """Benchmark data manager operations"""
        import time
        
        print("Benchmarking DataManager...")
        
        # Setup
        temp_db = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
        temp_db.close()
        dm = DataManager(db_path=temp_db.name)
        
        # Create sample data
        dates = pd.date_range('2023-01-01', periods=1000, freq='D')
        sample_data = pd.DataFrame({
            'Open': np.random.normal(100, 10, 1000),
            'High': np.random.normal(105, 10, 1000),
            'Low': np.random.normal(95, 10, 1000),
            'Close': np.random.normal(100, 10, 1000),
            'Volume': np.random.randint(1000000, 5000000, 1000),
            'Dividends': np.zeros(1000),
            'Stock Splits': np.zeros(1000)
        }, index=dates)
        
        # Benchmark storage
        start_time = time.time()
        for i in range(10):
            dm._store_data(f'TEST{i}', sample_data, '1d')
        storage_time = time.time() - start_time
        
        # Benchmark retrieval
        start_time = time.time()
        for i in range(10):
            dm._get_cached_data(f'TEST{i}', '1d')
        retrieval_time = time.time() - start_time
        
        # Cleanup
        dm.close()
        os.unlink(temp_db.name)
        
        print(f"Storage: {storage_time:.3f}s for 10 stocks x 1000 days")
        print(f"Retrieval: {retrieval_time:.3f}s for 10 stocks")
        print(f"Storage rate: {10000/storage_time:.0f} records/second")
    
    @staticmethod
    def benchmark_indicators():
        """Benchmark technical indicators"""
        import time
        
        print("\nBenchmarking Technical Indicators...")
        
        ti = TechnicalIndicators()
        
        # Create large dataset
        prices = pd.Series(np.random.normal(100, 10, 10000))
        high = prices * 1.02
        low = prices * 0.98
        close = prices
        
        indicators = [
            ('RSI', lambda: ti.rsi(prices)),
            ('MACD', lambda: ti.macd(prices)),
            ('Bollinger Bands', lambda: ti.bollinger_bands(prices)),
            ('ATR', lambda: ti.atr(high, low, close)),
            ('Stochastic', lambda: ti.stochastic(high, low, close))
        ]
        
        for name, func in indicators:
            start_time = time.time()
            for _ in range(100):  # Run 100 times
                result = func()
            execution_time = time.time() - start_time
            print(f"{name}: {execution_time:.3f}s for 100 runs on 10k points")


if __name__ == "__main__":
    # Run tests
    print("Running Trading System Tests...")
    print("=" * 50)
    
    # Test configuration
    config = ConfigManager()
    issues = config.validate_config()
    if issues:
        print("Configuration issues found:")
        for issue in issues:
            print(f"  • {issue}")
    else:
        print("✓ Configuration is valid")
    
    # Run unit tests
    test_loader = unittest.TestLoader()
    test_suite = unittest.TestSuite()
    
    # Add test classes
    test_classes = [
        TestDataManager,
        TestTechnicalIndicators,
        TestMarketRegimeDetector,
        TestSignalGenerator,
        TestPortfolioAnalyzer
    ]
    
    for test_class in test_classes:
        tests = test_loader.loadTestsFromTestCase(test_class)
        test_suite.addTests(tests)
    
    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(test_suite)
    
    # Performance benchmarks
    print("\n" + "=" * 50)
    print("Performance Benchmarks:")
    PerformanceBenchmark.benchmark_data_manager()
    PerformanceBenchmark.benchmark_indicators()
    
    # Summary
    print("\n" + "=" * 50)
    print("Test Summary:")
    print(f"Tests run: {result.testsRun}")
    print(f"Failures: {len(result.failures)}")
    print(f"Errors: {len(result.errors)}")
    
    if result.failures:
        print("\nFailures:")
        for test, traceback in result.failures:
            print(f"  {test}: {traceback}")
    
    if result.errors:
        print("\nErrors:")
        for test, traceback in result.errors:
            print(f"  {test}: {traceback}")
    
    success_rate = (result.testsRun - len(result.failures) - len(result.errors)) / result.testsRun * 100
    print(f"\nSuccess rate: {success_rate:.1f}%")
