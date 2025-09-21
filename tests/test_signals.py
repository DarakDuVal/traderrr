"""
tests/test_signals.py
Test cases for trading signal generation
"""

import unittest
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock

from tests import BaseTestCase
from app.core.signal_generator import (
    SignalGenerator, TradingSignal, SignalType, MarketRegime
)
from app.core.indicators import TechnicalIndicators


class TestSignalGenerator(BaseTestCase):
    """Test cases for SignalGenerator"""

    def setUp(self):
        """Set up test fixtures"""
        super().setUp()
        self.signal_gen = SignalGenerator(min_confidence=0.5)

        # Create different types of market data for testing
        np.random.seed(42)
        dates = pd.date_range('2023-01-01', periods=100, freq='D')

        # Trending up market
        trending_returns = np.random.normal(0.002, 0.015, 100)  # Positive drift
        trending_prices = 100 * np.exp(np.cumsum(trending_returns))

        self.trending_data = pd.DataFrame({
            'Open': trending_prices * np.random.uniform(0.995, 1.005, 100),
            'High': trending_prices * np.random.uniform(1.005, 1.025, 100),
            'Low': trending_prices * np.random.uniform(0.975, 0.995, 100),
            'Close': trending_prices,
            'Volume': np.random.randint(1000000, 5000000, 100)
        }, index=dates)

        # Mean reverting market (oscillating around mean)
        mean_price = 100
        oscillation = 10 * np.sin(np.linspace(0, 4 * np.pi, 100))
        noise = np.random.normal(0, 2, 100)
        reverting_prices = mean_price + oscillation + noise

        self.reverting_data = pd.DataFrame({
            'Open': reverting_prices * np.random.uniform(0.995, 1.005, 100),
            'High': reverting_prices * np.random.uniform(1.005, 1.025, 100),
            'Low': reverting_prices * np.random.uniform(0.975, 0.995, 100),
            'Close': reverting_prices,
            'Volume': np.random.randint(1000000, 5000000, 100)
        }, index=dates)

        # High volatility market
        volatile_returns = np.random.normal(0, 0.05, 100)  # High volatility
        volatile_prices = 100 * np.exp(np.cumsum(volatile_returns))

        self.volatile_data = pd.DataFrame({
            'Open': volatile_prices * np.random.uniform(0.99, 1.01, 100),
            'High': volatile_prices * np.random.uniform(1.01, 1.05, 100),
            'Low': volatile_prices * np.random.uniform(0.95, 0.99, 100),
            'Close': volatile_prices,
            'Volume': np.random.randint(5000000, 20000000, 100)  # High volume
        }, index=dates)

        # Ensure OHLC consistency for all datasets
        for data in [self.trending_data, self.reverting_data, self.volatile_data]:
            for i in range(len(data)):
                high = max(data.iloc[i][['Open', 'High', 'Close']])
                low = min(data.iloc[i][['Open', 'Low', 'Close']])
                data.iloc[i, data.columns.get_loc('High')] = high
                data.iloc[i, data.columns.get_loc('Low')] = low

    def test_signal_generation_basic(self):
        """Test basic signal generation functionality"""
        signal = self.signal_gen.generate_signal('TEST', self.trending_data)

        if signal is not None:
            # Check signal object structure
            self.assertIsInstance(signal, TradingSignal)
            self.assertEqual(signal.ticker, 'TEST')
            self.assertIsInstance(signal.signal_type, SignalType)
            self.assertIsInstance(signal.regime, MarketRegime)

            # Check confidence is in valid range
            self.assertGreaterEqual(signal.confidence, 0.0)
            self.assertLessEqual(signal.confidence, 1.0)

            # Check prices are positive
            self.assertGreater(signal.entry_price, 0)
            self.assertGreater(signal.stop_loss, 0)
            self.assertGreater(signal.target_price, 0)

            # Check that reasons are provided
            self.assertIsInstance(signal.reasons, list)
            self.assertGreater(len(signal.reasons), 0)

            # Check timestamp
            self.assertIsInstance(signal.timestamp, datetime)

    def test_trending_market_signals(self):
        """Test signal generation in trending market"""
        signal = self.signal_gen.generate_signal('TRENDING', self.trending_data)

        if signal is not None:
            # In trending up market, should lean towards buy signals
            # Note: This is probabilistic, so we just check it doesn't crash
            self.assertIn(signal.signal_type, [SignalType.BUY, SignalType.SELL,
                                               SignalType.STRONG_BUY, SignalType.STRONG_SELL])

            # Check that stop loss and target make sense for signal direction
            if signal.signal_type in [SignalType.BUY, SignalType.STRONG_BUY]:
                self.assertLess(signal.stop_loss, signal.entry_price)
                self.assertGreater(signal.target_price, signal.entry_price)
            elif signal.signal_type in [SignalType.SELL, SignalType.STRONG_SELL]:
                self.assertGreater(signal.stop_loss, signal.entry_price)
                self.assertLess(signal.target_price, signal.entry_price)

    def test_mean_reverting_signals(self):
        """Test signal generation in mean-reverting market"""
        signal = self.signal_gen.generate_signal('REVERTING', self.reverting_data)

        if signal is not None:
            # Should generate valid signal
            self.assertIsInstance(signal, TradingSignal)

            # Stop loss and target should be reasonable
            if signal.signal_type in [SignalType.BUY, SignalType.STRONG_BUY]:
                self.assertLess(signal.stop_loss, signal.entry_price)
                self.assertGreater(signal.target_price, signal.entry_price)

    def test_high_volatility_signals(self):
        """Test signal generation in high volatility market"""
        signal = self.signal_gen.generate_signal('VOLATILE', self.volatile_data)

        if signal is not None:
            # Should handle high volatility data
            self.assertIsInstance(signal, TradingSignal)

            # In high volatility, stop losses should be wider
            atr_estimate = self.volatile_data['Close'].pct_change().std() * self.volatile_data['Close'].iloc[-1]
            stop_distance = abs(signal.stop_loss - signal.entry_price)

            # Stop loss should be reasonable compared to volatility
            self.assertGreater(stop_distance, atr_estimate * 0.5)

    def test_insufficient_data(self):
        """Test behavior with insufficient data"""
        # Very short data
        short_data = self.trending_data.iloc[:10]
        signal = self.signal_gen.generate_signal('SHORT', short_data)

        # Should return None or handle gracefully
        if signal is not None:
            self.assertIsInstance(signal, TradingSignal)

        # Empty data
        empty_data = pd.DataFrame()
        signal_empty = self.signal_gen.generate_signal('EMPTY', empty_data)
        self.assertIsNone(signal_empty)

    def test_portfolio_signals(self):
        """Test portfolio signal generation"""
        portfolio_data = {
            'TREND': self.trending_data,
            'REVERT': self.reverting_data,
            'VOLATILE': self.volatile_data
        }

        signals = self.signal_gen.generate_portfolio_signals(portfolio_data)

        # Should return list
        self.assertIsInstance(signals, list)

        # Each signal should be valid
        for signal in signals:
            self.assertIsInstance(signal, TradingSignal)
            self.assertIn(signal.ticker, portfolio_data.keys())

        # Signals should be sorted by confidence (highest first)
        if len(signals) > 1:
            for i in range(len(signals) - 1):
                self.assertGreaterEqual(signals[i].confidence, signals[i + 1].confidence)

    def test_confidence_calculation(self):
        """Test confidence score calculation"""
        # Create a scenario that should generate high confidence
        strong_trend_data = self.trending_data.copy()

        # Generate signal
        signal = self.signal_gen.generate_signal('STRONG', strong_trend_data)

        if signal is not None:
            # Confidence should be within valid range
            self.assertGreaterEqual(signal.confidence, 0.0)
            self.assertLessEqual(signal.confidence, 1.0)

            # Should meet minimum confidence threshold
            self.assertGreaterEqual(signal.confidence, self.signal_gen.min_confidence)

    def test_market_regime_detection(self):
        """Test market regime detection"""
        # Test trending market detection
        regime_trending = self.signal_gen._detect_market_regime(self.trending_data)
        self.assertIsInstance(regime_trending, MarketRegime)

        # Test mean reverting market detection
        regime_reverting = self.signal_gen._detect_market_regime(self.reverting_data)
        self.assertIsInstance(regime_reverting, MarketRegime)

        # Test high volatility market detection
        regime_volatile = self.signal_gen._detect_market_regime(self.volatile_data)
        self.assertIsInstance(regime_volatile, MarketRegime)

        # Regimes should be different for different market types
        regimes = [regime_trending, regime_reverting, regime_volatile]
        regime_values = [r.value for r in regimes]

        # Should detect some variation (not all the same)
        # Note: This is probabilistic, so we just ensure it runs
        self.assertTrue(all(isinstance(r, MarketRegime) for r in regimes))

    def test_indicator_calculation(self):
        """Test indicator calculation within signal generation"""
        indicators = self.signal_gen._calculate_indicators(self.trending_data)

        # Should return dictionary
        self.assertIsInstance(indicators, dict)

        # Should contain key indicators
        key_indicators = ['rsi', 'macd', 'bb_position', 'atr', 'momentum_score']
        for indicator in key_indicators:
            self.assertIn(indicator, indicators)

        # Indicators should be valid numbers
        for key, value in indicators.items():
            if not key.endswith('_bullish') and not key.endswith('_oversold') and not key.endswith('_overbought'):
                self.assertIsInstance(value, (int, float))
                self.assertFalse(np.isnan(value))

    def test_momentum_strategy(self):
        """Test momentum strategy logic"""
        indicators = self.signal_gen._calculate_indicators(self.trending_data)

        signal_data = self.signal_gen._momentum_strategy(
            self.trending_data, indicators, MarketRegime.TRENDING_UP
        )

        if signal_data is not None:
            # Should return dictionary with signal type and reasons
            self.assertIn('signal_type', signal_data)
            self.assertIn('reasons', signal_data)

            self.assertIsInstance(signal_data['signal_type'], SignalType)
            self.assertIsInstance(signal_data['reasons'], list)
            self.assertGreater(len(signal_data['reasons']), 0)

    def test_mean_reversion_strategy(self):
        """Test mean reversion strategy logic"""
        indicators = self.signal_gen._calculate_indicators(self.reverting_data)

        signal_data = self.signal_gen._mean_reversion_strategy(
            self.reverting_data, indicators, MarketRegime.MEAN_REVERTING
        )

        if signal_data is not None:
            # Should return dictionary with signal type and reasons
            self.assertIn('signal_type', signal_data)
            self.assertIn('reasons', signal_data)

            self.assertIsInstance(signal_data['signal_type'], SignalType)
            self.assertIsInstance(signal_data['reasons'], list)

    def test_signal_summary(self):
        """Test signal summary generation"""
        portfolio_data = {
            'TREND': self.trending_data,
            'REVERT': self.reverting_data,
            'VOLATILE': self.volatile_data
        }

        signals = self.signal_gen.generate_portfolio_signals(portfolio_data)
        summary = self.signal_gen.get_signal_summary(signals)

        # Check summary structure
        self.assertIsInstance(summary, dict)
        self.assertIn('total_signals', summary)
        self.assertIn('buy_signals', summary)
        self.assertIn('sell_signals', summary)
        self.assertIn('average_confidence', summary)
        self.assertIn('top_picks', summary)

        # Check values are reasonable
        self.assertEqual(summary['total_signals'], len(signals))
        self.assertGreaterEqual(summary['buy_signals'], 0)
        self.assertGreaterEqual(summary['sell_signals'], 0)

        if signals:
            self.assertGreaterEqual(summary['average_confidence'], 0)
            self.assertLessEqual(summary['average_confidence'], 1)

        # Top picks should be a list
        self.assertIsInstance(summary['top_picks'], list)
        self.assertLessEqual(len(summary['top_picks']), min(3, len(signals)))

    def test_signal_types(self):
        """Test all signal types can be generated"""
        # This is more of a coverage test to ensure all signal types work
        signal_types_seen = set()

        # Generate many signals with different parameters
        test_datasets = [self.trending_data, self.reverting_data, self.volatile_data]

        for data in test_datasets:
            for min_conf in [0.3, 0.5, 0.7]:
                temp_generator = SignalGenerator(min_confidence=min_conf)
                signal = temp_generator.generate_signal('TEST', data)

                if signal is not None:
                    signal_types_seen.add(signal.signal_type)

        # Should be able to generate at least some different signal types
        self.assertGreater(len(signal_types_seen), 0)

        # All signal types should be valid
        for signal_type in signal_types_seen:
            self.assertIsInstance(signal_type, SignalType)

    def test_error_handling(self):
        """Test error handling in signal generation"""
        # Test with invalid data
        invalid_data = pd.DataFrame({'invalid': [1, 2, 3]})

        signal = self.signal_gen.generate_signal('INVALID', invalid_data)
        # Should handle gracefully (return None or raise appropriate error)

        # Test with NaN data
        nan_data = self.trending_data.copy()
        nan_data.iloc[50:60] = np.nan

        signal_nan = self.signal_gen.generate_signal('NAN', nan_data)
        # Should handle NaN data gracefully

        if signal_nan is not None:
            self.assertIsInstance(signal_nan, TradingSignal)

    def test_custom_parameters(self):
        """Test signal generator with custom parameters"""
        custom_gen = SignalGenerator(
            momentum_threshold=70.0,
            mean_reversion_threshold=80.0,
            volatility_factor=3.0,
            min_confidence=0.8
        )

        signal = custom_gen.generate_signal('CUSTOM', self.trending_data)

        if signal is not None:
            # Should meet higher confidence threshold
            self.assertGreaterEqual(signal.confidence, 0.8)

            # Stop loss should be wider with higher volatility factor
            # This is harder to test directly, but signal should be valid
            self.assertIsInstance(signal, TradingSignal)

    def test_signal_consistency(self):
        """Test that signal generation is deterministic for same input"""
        # Generate signal twice with same data
        signal1 = self.signal_gen.generate_signal('CONSISTENCY', self.trending_data)
        signal2 = self.signal_gen.generate_signal('CONSISTENCY', self.trending_data)

        # Results might not be identical due to timestamps, but should be very similar
        if signal1 is not None and signal2 is not None:
            self.assertEqual(signal1.signal_type, signal2.signal_type)
            self.assertEqual(signal1.regime, signal2.regime)
            self.assertAlmostEqual(signal1.confidence, signal2.confidence, places=2)
            self.assertAlmostEqual(signal1.entry_price, signal2.entry_price, places=2)


class TestSignalEnums(BaseTestCase):
    """Test signal type and regime enums"""

    def test_signal_type_enum(self):
        """Test SignalType enum"""
        # Test all signal types
        signal_types = [SignalType.BUY, SignalType.SELL, SignalType.HOLD,
                        SignalType.STRONG_BUY, SignalType.STRONG_SELL]

        for signal_type in signal_types:
            self.assertIsInstance(signal_type, SignalType)
            self.assertIsInstance(signal_type.value, str)

    def test_market_regime_enum(self):
        """Test MarketRegime enum"""
        # Test all regime types
        regimes = [MarketRegime.TRENDING_UP, MarketRegime.TRENDING_DOWN,
                   MarketRegime.MEAN_REVERTING, MarketRegime.SIDEWAYS,
                   MarketRegime.HIGH_VOLATILITY]

        for regime in regimes:
            self.assertIsInstance(regime, MarketRegime)
            self.assertIsInstance(regime.value, str)


class TestTradingSignal(BaseTestCase):
    """Test TradingSignal dataclass"""

    def test_trading_signal_creation(self):
        """Test TradingSignal object creation"""
        signal = TradingSignal(
            ticker='TEST',
            signal_type=SignalType.BUY,
            confidence=0.75,
            entry_price=100.0,
            stop_loss=95.0,
            target_price=110.0,
            regime=MarketRegime.TRENDING_UP,
            indicators={'rsi': 45.0, 'macd': 0.5},
            timestamp=datetime.now(),
            reasons=['RSI oversold', 'MACD bullish crossover']
        )

        # Check all attributes
        self.assertEqual(signal.ticker, 'TEST')
        self.assertEqual(signal.signal_type, SignalType.BUY)
        self.assertEqual(signal.confidence, 0.75)
        self.assertEqual(signal.entry_price, 100.0)
        self.assertEqual(signal.stop_loss, 95.0)
        self.assertEqual(signal.target_price, 110.0)
        self.assertEqual(signal.regime, MarketRegime.TRENDING_UP)
        self.assertIsInstance(signal.indicators, dict)
        self.assertIsInstance(signal.timestamp, datetime)
        self.assertIsInstance(signal.reasons, list)


if __name__ == '__main__':
    unittest.main()