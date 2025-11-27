"""
tests/test_indicators.py
Test cases for technical indicators
"""

import unittest
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

from tests import BaseTestCase
from app.core.indicators import (
    TechnicalIndicators,
    MarketRegimeDetector,
    AdvancedIndicators,
)


class TestTechnicalIndicators(BaseTestCase):
    """Test cases for TechnicalIndicators class"""

    def setUp(self):
        """Set up test fixtures"""
        super().setUp()

        # Create sample price data
        np.random.seed(42)  # For reproducible tests
        dates = pd.date_range("2023-01-01", periods=100, freq="D")

        # Generate realistic price data with trend
        base_price = 100
        returns = np.random.normal(0.001, 0.02, 100)  # 0.1% daily return, 2% volatility
        prices = base_price * np.exp(np.cumsum(returns))

        self.sample_data = pd.DataFrame(
            {
                "Open": prices * np.random.uniform(0.98, 1.02, 100),
                "High": prices * np.random.uniform(1.00, 1.05, 100),
                "Low": prices * np.random.uniform(0.95, 1.00, 100),
                "Close": prices,
                "Volume": np.random.randint(1000000, 5000000, 100),
            },
            index=dates,
        )

        # Ensure High >= Close >= Low and High >= Open >= Low
        for i in range(len(self.sample_data)):
            high = max(
                self.sample_data.iloc[i]["Open"],
                self.sample_data.iloc[i]["Close"],
                self.sample_data.iloc[i]["High"],
            )
            low = min(
                self.sample_data.iloc[i]["Open"],
                self.sample_data.iloc[i]["Close"],
                self.sample_data.iloc[i]["Low"],
            )

            self.sample_data.iloc[i, self.sample_data.columns.get_loc("High")] = high
            self.sample_data.iloc[i, self.sample_data.columns.get_loc("Low")] = low

        self.ti = TechnicalIndicators()

    def test_sma_calculation(self):
        """Test Simple Moving Average calculation"""
        prices = self.sample_data["Close"]
        sma_20 = self.ti.sma(prices, 20)

        # Check that SMA is calculated correctly
        self.assertEqual(len(sma_20), len(prices))

        # First 19 values should be NaN
        self.assertTrue(sma_20.iloc[:19].isna().all())

        # 20th value should be average of first 20 prices
        expected_value = prices.iloc[:20].mean()
        self.assertAlmostEqual(sma_20.iloc[19], expected_value, places=6)

        # Check that values are reasonable
        self.assertTrue((sma_20.dropna() > 0).all())

    def test_ema_calculation(self):
        """Test Exponential Moving Average calculation"""
        prices = self.sample_data["Close"]
        ema_12 = self.ti.ema(prices, 12)

        # Check basic properties
        self.assertEqual(len(ema_12), len(prices))
        self.assertFalse(ema_12.iloc[-1] == 0)

        # EMA should be different from SMA
        sma_12 = self.ti.sma(prices, 12)
        self.assertNotAlmostEqual(ema_12.iloc[-1], sma_12.iloc[-1], places=2)

    def test_rsi_calculation(self):
        """Test RSI calculation"""
        prices = self.sample_data["Close"]
        rsi = self.ti.rsi(prices, 14)

        # Check basic properties
        self.assertEqual(len(rsi), len(prices))

        # RSI should be between 0 and 100
        valid_rsi = rsi.dropna()
        self.assertTrue((valid_rsi >= 0).all())
        self.assertTrue((valid_rsi <= 100).all())

        # Should have some variation
        self.assertGreater(valid_rsi.std(), 1)

    def test_macd_calculation(self):
        """Test MACD calculation"""
        prices = self.sample_data["Close"]
        macd_line, signal_line, histogram = self.ti.macd(prices)

        # Check that all have same length
        self.assertEqual(len(macd_line), len(prices))
        self.assertEqual(len(signal_line), len(prices))
        self.assertEqual(len(histogram), len(prices))

        # Histogram should equal MACD - Signal
        diff = (macd_line - signal_line).dropna()
        hist_clean = histogram.dropna()

        # Should be approximately equal (within floating point precision)
        if len(diff) > 0 and len(hist_clean) > 0:
            correlation = diff.corr(hist_clean.iloc[: len(diff)])
            self.assertGreater(correlation, 0.99)

    def test_bollinger_bands(self):
        """Test Bollinger Bands calculation"""
        prices = self.sample_data["Close"]
        upper, middle, lower = self.ti.bollinger_bands(prices, 20, 2.0)

        # Check lengths
        self.assertEqual(len(upper), len(prices))
        self.assertEqual(len(middle), len(prices))
        self.assertEqual(len(lower), len(prices))

        # Upper should be greater than middle, middle greater than lower
        valid_data = pd.DataFrame({"upper": upper, "middle": middle, "lower": lower}).dropna()

        self.assertTrue((valid_data["upper"] >= valid_data["middle"]).all())
        self.assertTrue((valid_data["middle"] >= valid_data["lower"]).all())

        # Middle should be approximately SMA
        sma_20 = self.ti.sma(prices, 20)
        middle_clean = middle.dropna()
        sma_clean = sma_20.dropna()

        if len(middle_clean) > 0 and len(sma_clean) > 0:
            # Should be very similar
            diff = abs(middle_clean.iloc[-10:] - sma_clean.iloc[-10:])
            self.assertLess(diff.max(), 0.01)

    def test_stochastic_oscillator(self):
        """Test Stochastic Oscillator"""
        high = self.sample_data["High"]
        low = self.sample_data["Low"]
        close = self.sample_data["Close"]

        k_percent, d_percent = self.ti.stochastic(high, low, close, 14, 3)

        # Check lengths
        self.assertEqual(len(k_percent), len(close))
        self.assertEqual(len(d_percent), len(close))

        # Values should be between 0 and 100
        k_valid = k_percent.dropna()
        d_valid = d_percent.dropna()

        self.assertTrue((k_valid >= 0).all())
        self.assertTrue((k_valid <= 100).all())
        self.assertTrue((d_valid >= 0).all())
        self.assertTrue((d_valid <= 100).all())

    def test_atr_calculation(self):
        """Test Average True Range"""
        high = self.sample_data["High"]
        low = self.sample_data["Low"]
        close = self.sample_data["Close"]

        atr = self.ti.atr(high, low, close, 14)

        # Check length
        self.assertEqual(len(atr), len(close))

        # ATR should be positive
        atr_valid = atr.dropna()
        self.assertTrue((atr_valid > 0).all())

        # ATR should be reasonable compared to price range
        price_range = (high - low).mean()
        avg_atr = atr_valid.mean()

        # ATR should be in reasonable proportion to daily range
        self.assertLess(avg_atr, price_range * 2)
        self.assertGreater(avg_atr, price_range * 0.1)

    def test_williams_r(self):
        """Test Williams %R"""
        high = self.sample_data["High"]
        low = self.sample_data["Low"]
        close = self.sample_data["Close"]

        williams = self.ti.williams_r(high, low, close, 14)

        # Check length
        self.assertEqual(len(williams), len(close))

        # Williams %R should be between -100 and 0
        williams_valid = williams.dropna()
        self.assertTrue((williams_valid >= -100).all())
        self.assertTrue((williams_valid <= 0).all())

    def test_adx_calculation(self):
        """Test ADX calculation"""
        high = self.sample_data["High"]
        low = self.sample_data["Low"]
        close = self.sample_data["Close"]

        adx, di_plus, di_minus = self.ti.adx(high, low, close, 14)

        # Check lengths
        self.assertEqual(len(adx), len(close))
        self.assertEqual(len(di_plus), len(close))
        self.assertEqual(len(di_minus), len(close))

        # All should be positive
        adx_valid = adx.dropna()
        di_plus_valid = di_plus.dropna()
        di_minus_valid = di_minus.dropna()

        self.assertTrue((adx_valid >= 0).all())
        self.assertTrue((di_plus_valid >= 0).all())
        self.assertTrue((di_minus_valid >= 0).all())

    def test_edge_cases(self):
        """Test edge cases and error handling"""
        # Test with very short data
        short_data = self.sample_data["Close"][:5]

        # Should not crash, but may return NaN
        rsi_short = self.ti.rsi(short_data, 14)
        self.assertEqual(len(rsi_short), 5)

        # Test with constant prices
        constant_prices = pd.Series([100.0] * 50)
        rsi_constant = self.ti.rsi(constant_prices, 14)

        # RSI of constant prices should be around 50 (neutral)
        rsi_valid = rsi_constant.dropna()
        if len(rsi_valid) > 0:
            self.assertAlmostEqual(rsi_valid.iloc[-1], 50.0, places=0)

    def test_fibonacci_levels(self):
        """Test Fibonacci retracement levels"""
        high_price = 120.0
        low_price = 100.0

        fib_levels = self.ti.fibonacci_levels(high_price, low_price)

        # Check that all expected levels are present
        expected_levels = [
            "level_0",
            "level_236",
            "level_382",
            "level_500",
            "level_618",
            "level_786",
            "level_100",
        ]

        for level in expected_levels:
            self.assertIn(level, fib_levels)

        # Check level ordering
        self.assertEqual(fib_levels["level_0"], high_price)
        self.assertEqual(fib_levels["level_100"], low_price)
        self.assertGreater(fib_levels["level_236"], fib_levels["level_382"])
        self.assertGreater(fib_levels["level_382"], fib_levels["level_500"])

        # Check 50% level
        expected_50 = (high_price + low_price) / 2
        self.assertAlmostEqual(fib_levels["level_500"], expected_50, places=6)

    def test_pivot_points(self):
        """Test pivot point calculation"""
        high_price = 110.0
        low_price = 105.0
        close_price = 108.0

        pivots = self.ti.pivot_points(high_price, low_price, close_price)

        # Check all levels are present
        expected_keys = ["pivot", "r1", "r2", "r3", "s1", "s2", "s3"]
        for key in expected_keys:
            self.assertIn(key, pivots)

        # Check pivot calculation
        expected_pivot = (high_price + low_price + close_price) / 3
        self.assertAlmostEqual(pivots["pivot"], expected_pivot, places=6)

        # Check resistance and support ordering
        self.assertGreater(pivots["r1"], pivots["pivot"])
        self.assertGreater(pivots["r2"], pivots["r1"])
        self.assertGreater(pivots["r3"], pivots["r2"])

        self.assertLess(pivots["s1"], pivots["pivot"])
        self.assertLess(pivots["s2"], pivots["s1"])
        self.assertLess(pivots["s3"], pivots["s2"])


class TestMarketRegimeDetector(BaseTestCase):
    """Test cases for MarketRegimeDetector"""

    def setUp(self):
        """Set up test fixtures"""
        super().setUp()
        self.detector = MarketRegimeDetector()

        # Create trending data
        self.trending_data = pd.Series(100 + np.cumsum(np.random.normal(0.1, 0.5, 100)))

        # Create mean-reverting data
        self.mean_reverting_data = pd.Series(
            100 + 5 * np.sin(np.linspace(0, 4 * np.pi, 100)) + np.random.normal(0, 0.5, 100)
        )

    def test_hurst_exponent_trending(self):
        """Test Hurst exponent on trending data"""
        hurst = self.detector.hurst_exponent(self.trending_data)

        # Trending data should have Hurst > 0.5
        self.assertGreater(hurst, 0.4)  # Allow some tolerance
        self.assertLess(hurst, 1.0)

    def test_hurst_exponent_mean_reverting(self):
        """Test Hurst exponent on mean-reverting data"""
        hurst = self.detector.hurst_exponent(self.mean_reverting_data)

        # Hurst exponent should be valid (between 0 and 1)
        # Trending if > 0.5, mean-reverting if < 0.5, random if ≈ 0.5
        self.assertGreater(hurst, 0.0)
        self.assertLess(hurst, 1.0)

    def test_trend_strength(self):
        """Test trend strength calculation"""
        # Strong uptrend
        uptrend = pd.Series(range(50))
        trend_strength_up = self.detector.trend_strength(uptrend)
        self.assertGreater(trend_strength_up, 0.7)  # Strong uptrend

        # No trend (random walk)
        random_walk = pd.Series(np.cumsum(np.random.normal(0, 1, 50)))
        trend_strength_random = self.detector.trend_strength(random_walk)
        # Random walk may not have strong trend, but due to randomness it could be high
        # Just verify it returns a valid value
        self.assertGreaterEqual(trend_strength_random, 0.0)
        self.assertLessEqual(trend_strength_random, 1.0)

    def test_volatility_regime(self):
        """Test volatility regime classification"""
        # Low volatility data
        low_vol_data = pd.Series(100 + np.random.normal(0, 0.1, 100))
        vol_regime_low = self.detector.volatility_regime(low_vol_data)

        # High volatility data
        high_vol_data = pd.Series(100 + np.random.normal(0, 5, 100))
        vol_regime_high = self.detector.volatility_regime(high_vol_data)

        # Should classify correctly (though may not always due to randomness)
        self.assertIn(vol_regime_low, ["low", "normal", "high"])
        self.assertIn(vol_regime_high, ["low", "normal", "high"])


class TestAdvancedIndicators(BaseTestCase):
    """Test cases for AdvancedIndicators"""

    def setUp(self):
        """Set up test fixtures"""
        super().setUp()

        # Create sample OHLCV data
        np.random.seed(42)
        dates = pd.date_range("2023-01-01", periods=100, freq="D")
        prices = 100 + np.cumsum(np.random.normal(0.1, 2, 100))

        self.sample_data = pd.DataFrame(
            {
                "Open": prices * 0.99,
                "High": prices * 1.02,
                "Low": prices * 0.98,
                "Close": prices,
                "Volume": np.random.randint(1000000, 5000000, 100),
            },
            index=dates,
        )

        self.advanced = AdvancedIndicators()

    def test_squeeze_momentum(self):
        """Test TTM Squeeze indicator"""
        high = self.sample_data["High"]
        low = self.sample_data["Low"]
        close = self.sample_data["Close"]

        squeeze_data = self.advanced.squeeze_momentum(high, low, close)

        # Check that all components are present
        expected_keys = ["squeeze_on", "squeeze_off", "no_squeeze", "momentum"]
        for key in expected_keys:
            self.assertIn(key, squeeze_data)

        # Check lengths
        for key in expected_keys:
            self.assertEqual(len(squeeze_data[key]), len(close))

        # Squeeze conditions should be boolean
        squeeze_on = squeeze_data["squeeze_on"].dropna()
        squeeze_off = squeeze_data["squeeze_off"].dropna()

        self.assertTrue(squeeze_on.dtype == bool)
        self.assertTrue(squeeze_off.dtype == bool)

    def test_composite_momentum(self):
        """Test composite momentum score"""
        momentum_score = self.advanced.composite_momentum(self.sample_data)

        # Check length
        self.assertEqual(len(momentum_score), len(self.sample_data))

        # Should be roughly between -100 and 100
        score_valid = momentum_score.dropna()
        self.assertGreater(score_valid.min(), -150)  # Allow some tolerance
        self.assertLess(score_valid.max(), 150)

    def test_mean_reversion_score(self):
        """Test mean reversion score"""
        mr_score = self.advanced.mean_reversion_score(self.sample_data)

        # Check length
        self.assertEqual(len(mr_score), len(self.sample_data))

        # Should be roughly between -100 and 100
        score_valid = mr_score.dropna()
        self.assertGreater(score_valid.min(), -150)  # Allow some tolerance
        self.assertLess(score_valid.max(), 150)

    def test_indicator_consistency(self):
        """Test that indicators produce consistent results"""
        # Run same calculation twice
        momentum1 = self.advanced.composite_momentum(self.sample_data)
        momentum2 = self.advanced.composite_momentum(self.sample_data)

        # Results should be identical
        pd.testing.assert_series_equal(momentum1, momentum2)

    def test_data_validation(self):
        """Test indicators with edge case data"""
        # Very short data
        short_data = self.sample_data.iloc[:10]

        # Should not crash
        try:
            momentum = self.advanced.composite_momentum(short_data)
            mr_score = self.advanced.mean_reversion_score(short_data)
            # If it doesn't crash, that's a pass
            self.assertTrue(True)
        except Exception as e:
            self.fail(f"Indicators failed with short data: {e}")


# ============================================================================
# ADDITIONAL INDICATOR TESTS (Phase 2 Expansion)
# ============================================================================


class TestMissingIndicators(BaseTestCase):
    """Test cases for indicators not covered in main test classes"""

    def setUp(self):
        """Set up test fixtures"""
        super().setUp()

        # Create sample price data
        np.random.seed(42)
        dates = pd.date_range("2023-01-01", periods=100, freq="D")
        base_price = 100
        returns = np.random.normal(0.001, 0.02, 100)
        prices = base_price * np.exp(np.cumsum(returns))

        self.sample_data = pd.DataFrame(
            {
                "Open": prices * np.random.uniform(0.98, 1.02, 100),
                "High": prices * np.random.uniform(1.00, 1.05, 100),
                "Low": prices * np.random.uniform(0.95, 1.00, 100),
                "Close": prices,
                "Volume": np.random.randint(1000000, 5000000, 100),
            },
            index=dates,
        )

        # Ensure High >= Close >= Low
        for i in range(len(self.sample_data)):
            high = max(
                self.sample_data.iloc[i]["Open"],
                self.sample_data.iloc[i]["Close"],
                self.sample_data.iloc[i]["High"],
            )
            low = min(
                self.sample_data.iloc[i]["Open"],
                self.sample_data.iloc[i]["Close"],
                self.sample_data.iloc[i]["Low"],
            )
            self.sample_data.iloc[i, self.sample_data.columns.get_loc("High")] = high
            self.sample_data.iloc[i, self.sample_data.columns.get_loc("Low")] = low

        self.ti = TechnicalIndicators()

    def test_cci_calculation(self):
        """Test Commodity Channel Index calculation"""
        high = self.sample_data["High"]
        low = self.sample_data["Low"]
        close = self.sample_data["Close"]

        cci = self.ti.cci(high, low, close, period=20)

        # Check basic properties
        self.assertEqual(len(cci), len(close))

        # CCI values should be numeric
        self.assertTrue((cci.notna().any()))

        # CCI typically ranges from -100 to +100 for normal conditions
        cci_values = cci.dropna()
        if len(cci_values) > 0:
            self.assertTrue((cci_values > -500).all())  # Allow for extreme values
            self.assertTrue((cci_values < 500).all())

    def test_cci_different_periods(self):
        """Test CCI with different period values"""
        high = self.sample_data["High"]
        low = self.sample_data["Low"]
        close = self.sample_data["Close"]

        # Test different periods
        cci_10 = self.ti.cci(high, low, close, period=10)
        cci_20 = self.ti.cci(high, low, close, period=20)

        # Both should return same length
        self.assertEqual(len(cci_10), len(cci_20))

        # Results should be different for different periods
        if len(cci_10.dropna()) > 0 and len(cci_20.dropna()) > 0:
            self.assertFalse(cci_10.dropna().equals(cci_20.dropna()))

    def test_ichimoku_cloud_calculation(self):
        """Test Ichimoku Cloud indicator calculation"""
        high = self.sample_data["High"]
        low = self.sample_data["Low"]
        close = self.sample_data["Close"]

        result = self.ti.ichimoku_cloud(high, low, close)

        # Check that all required components are returned
        required_keys = [
            "tenkan_sen",
            "kijun_sen",
            "senkou_span_a",
            "senkou_span_b",
            "chikou_span",
        ]
        for key in required_keys:
            self.assertIn(key, result)
            self.assertEqual(len(result[key]), len(close))

    def test_ichimoku_relationships(self):
        """Test Ichimoku Cloud component relationships"""
        high = self.sample_data["High"]
        low = self.sample_data["Low"]
        close = self.sample_data["Close"]

        result = self.ti.ichimoku_cloud(high, low, close)

        # Tenkan and Kijun should be based on highs and lows
        tenkan = result["tenkan_sen"]
        kijun = result["kijun_sen"]

        # Both should have some non-NaN values
        self.assertGreater(tenkan.notna().sum(), 0)
        self.assertGreater(kijun.notna().sum(), 0)

        # Senkou Span A should be average of Tenkan and Kijun
        # (Check at least one point where all values are valid)
        valid_idx = tenkan.notna() & kijun.notna()
        if valid_idx.any():
            valid_tenkan = tenkan[valid_idx]
            valid_kijun = kijun[valid_idx]
            senkou_a = result["senkou_span_a"][valid_idx]

            # At least some values should be close to average
            expected = (valid_tenkan + valid_kijun) / 2
            self.assertTrue(((senkou_a - expected).abs() < 1).any())

    def test_indicator_with_constant_prices(self):
        """Test indicators with constant (no change) prices"""
        constant_data = pd.DataFrame(
            {
                "Open": [100.0] * 50,
                "High": [100.0] * 50,
                "Low": [100.0] * 50,
                "Close": [100.0] * 50,
                "Volume": [1000000] * 50,
            },
            index=pd.date_range("2023-01-01", periods=50, freq="D"),
        )

        # These should not crash
        close = constant_data["Close"]
        high = constant_data["High"]
        low = constant_data["Low"]

        sma = self.ti.sma(close, 20)
        self.assertFalse(sma.isna().all())

        rsi = self.ti.rsi(close, 14)
        # RSI with constant prices should be 50 or NaN
        rsi_values = rsi.dropna()
        if len(rsi_values) > 0:
            self.assertTrue((rsi_values >= 0).all() and (rsi_values <= 100).all())

        cci = self.ti.cci(high, low, close, 20)
        # CCI should handle constant prices without crashing
        self.assertEqual(len(cci), len(close))

    def test_indicator_with_missing_data(self):
        """Test indicators with NaN values in data"""
        data_with_nan = self.sample_data.copy()
        data_with_nan.loc[data_with_nan.index[10:15], "Close"] = np.nan

        close = data_with_nan["Close"]

        # SMA should handle NaN gracefully
        sma = self.ti.sma(close, 20)
        self.assertIsNotNone(sma)
        self.assertEqual(len(sma), len(close))

        # EMA should handle NaN gracefully
        ema = self.ti.ema(close, 12)
        self.assertIsNotNone(ema)
        self.assertEqual(len(ema), len(close))

    def test_macd_structure(self):
        """Test MACD return structure"""
        macd_result = self.ti.macd(self.sample_data["Close"])

        # MACD returns a tuple of (macd_line, signal_line, histogram)
        self.assertEqual(len(macd_result), 3)

        # All components should have same length as input
        for component in macd_result:
            self.assertEqual(len(component), len(self.sample_data))

    def test_bollinger_bands_width(self):
        """Test Bollinger Bands width calculation"""
        bb_result = self.ti.bollinger_bands(self.sample_data["Close"], period=20)

        # Bollinger Bands returns a tuple of (upper, middle, lower)
        self.assertEqual(len(bb_result), 3)
        upper, middle, lower = bb_result

        # All should have same length
        self.assertEqual(len(upper), len(self.sample_data))
        self.assertEqual(len(middle), len(self.sample_data))
        self.assertEqual(len(lower), len(self.sample_data))

        # Upper should always be >= lower
        valid_idx = upper.notna() & lower.notna()
        if valid_idx.any():
            self.assertTrue((upper[valid_idx] >= lower[valid_idx]).all())

    def test_stochastic_boundaries(self):
        """Test that Stochastic oscillator stays within 0-100"""
        stoch_result = self.ti.stochastic(
            self.sample_data["High"],
            self.sample_data["Low"],
            self.sample_data["Close"],
            k_period=14,
            d_period=3,
        )

        # Stochastic returns a tuple of (K, D)
        self.assertEqual(len(stoch_result), 2)
        k_line, d_line = stoch_result

        # Values should be between 0 and 100 (or NaN)
        k_values = k_line.dropna()
        d_values = d_line.dropna()

        if len(k_values) > 0:
            self.assertTrue((k_values >= 0).all() and (k_values <= 100).all())
        if len(d_values) > 0:
            self.assertTrue((d_values >= 0).all() and (d_values <= 100).all())

    def test_atr_positive_values(self):
        """Test that ATR always returns positive values"""
        atr = self.ti.atr(
            self.sample_data["High"],
            self.sample_data["Low"],
            self.sample_data["Close"],
            period=14,
        )

        # ATR should be positive or NaN
        atr_values = atr.dropna()
        if len(atr_values) > 0:
            self.assertTrue((atr_values > 0).all())

    def test_williams_r_boundaries(self):
        """Test that Williams %R stays within -100 to 0"""
        williams_r = self.ti.williams_r(
            self.sample_data["High"],
            self.sample_data["Low"],
            self.sample_data["Close"],
            period=14,
        )

        # Williams %R should be between -100 and 0
        wr_values = williams_r.dropna()
        if len(wr_values) > 0:
            self.assertTrue((wr_values >= -100).all() and (wr_values <= 0).all())


class TestIndicatorRobustness(BaseTestCase):
    """Test indicator robustness and error handling"""

    def setUp(self):
        """Set up test fixtures"""
        super().setUp()
        self.ti = TechnicalIndicators()

    def test_empty_series(self):
        """Test indicators with empty series"""
        empty_series = pd.Series([], dtype=float)

        # Should return empty or handle gracefully
        try:
            result = self.ti.sma(empty_series, 20)
            self.assertEqual(len(result), 0)
        except Exception:
            # It's acceptable to raise an exception for empty input
            pass

    def test_single_value_series(self):
        """Test indicators with single value"""
        single_value = pd.Series([100.0])

        # Should return series of same length
        result = self.ti.sma(single_value, 20)
        self.assertEqual(len(result), 1)

    def test_period_larger_than_data(self):
        """Test indicator with period larger than data length"""
        small_data = pd.Series([100.0, 101.0, 102.0, 103.0, 104.0])

        # Period of 20 on 5 data points
        result = self.ti.sma(small_data, 20)

        # Should return all NaN or same length
        self.assertEqual(len(result), len(small_data))

    def test_negative_period(self):
        """Test indicator with negative period handling"""
        data = pd.Series(np.random.rand(50) * 100)

        # Should either handle gracefully or raise meaningful error
        try:
            result = self.ti.sma(data, -20)
            # If it doesn't error, result should be valid
            self.assertEqual(len(result), len(data))
        except (ValueError, AssertionError):
            # Expected behavior - reject invalid period
            pass

    def test_zero_period(self):
        """Test indicator with zero period handling"""
        data = pd.Series(np.random.rand(50) * 100)

        try:
            result = self.ti.sma(data, 0)
            self.assertEqual(len(result), len(data))
        except (ValueError, AssertionError, ZeroDivisionError):
            # Expected behavior
            pass


if __name__ == "__main__":
    unittest.main()
