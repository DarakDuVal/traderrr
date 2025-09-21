"""
app/core/indicators.py - Technical indicators for trading signals
Optimized for vectorized operations and numerical stability
"""

import pandas as pd
import numpy as np
from typing import Tuple, Optional
import warnings

warnings.filterwarnings('ignore')


class TechnicalIndicators:
    """
    Comprehensive technical indicators class with momentum and mean reversion signals
    """

    @staticmethod
    def sma(data: pd.Series, period: int) -> pd.Series:
        """Simple Moving Average"""
        return data.rolling(window=period, min_periods=period).mean()

    @staticmethod
    def ema(data: pd.Series, period: int, alpha: Optional[float] = None) -> pd.Series:
        """Exponential Moving Average"""
        if alpha is None:
            alpha = 2.0 / (period + 1.0)
        return data.ewm(alpha=alpha, adjust=False).mean()

    @staticmethod
    def rsi(data: pd.Series, period: int = 14) -> pd.Series:
        """
        Relative Strength Index
        Optimized for numerical stability
        """
        delta = data.diff()
        gain = delta.where(delta > 0, 0.0)
        loss = -delta.where(delta < 0, 0.0)

        # Use Wilder's smoothing (exponential)
        alpha = 1.0 / period
        avg_gain = gain.ewm(alpha=alpha, adjust=False).mean()
        avg_loss = loss.ewm(alpha=alpha, adjust=False).mean()

        # Avoid division by zero
        rs = avg_gain / avg_loss.replace(0, np.nan)
        rsi = 100.0 - (100.0 / (1.0 + rs))

        return rsi.fillna(50.0)  # Fill NaN with neutral value

    @staticmethod
    def macd(data: pd.Series,
             fast_period: int = 12,
             slow_period: int = 26,
             signal_period: int = 9) -> Tuple[pd.Series, pd.Series, pd.Series]:
        """MACD with signal line and histogram"""
        ema_fast = TechnicalIndicators.ema(data, fast_period)
        ema_slow = TechnicalIndicators.ema(data, slow_period)

        macd_line = ema_fast - ema_slow
        signal_line = TechnicalIndicators.ema(macd_line, signal_period)
        histogram = macd_line - signal_line

        return macd_line, signal_line, histogram

    @staticmethod
    def bollinger_bands(data: pd.Series,
                        period: int = 20,
                        std_dev: float = 2.0) -> Tuple[pd.Series, pd.Series, pd.Series]:
        """Bollinger Bands with middle, upper, and lower bands"""
        middle = data.rolling(window=period, min_periods=period).mean()
        std = data.rolling(window=period, min_periods=period).std()

        upper = middle + (std * std_dev)
        lower = middle - (std * std_dev)

        return upper, middle, lower

    @staticmethod
    def stochastic(high: pd.Series,
                   low: pd.Series,
                   close: pd.Series,
                   k_period: int = 14,
                   d_period: int = 3) -> Tuple[pd.Series, pd.Series]:
        """Stochastic Oscillator %K and %D"""
        lowest_low = low.rolling(window=k_period, min_periods=k_period).min()
        highest_high = high.rolling(window=k_period, min_periods=k_period).max()

        # Avoid division by zero
        range_val = highest_high - lowest_low
        k_percent = ((close - lowest_low) / range_val.replace(0, np.nan)) * 100
        k_percent = k_percent.fillna(50.0)

        d_percent = k_percent.rolling(window=d_period, min_periods=d_period).mean()

        return k_percent, d_percent

    @staticmethod
    def atr(high: pd.Series,
            low: pd.Series,
            close: pd.Series,
            period: int = 14) -> pd.Series:
        """Average True Range"""
        tr1 = high - low
        tr2 = abs(high - close.shift(1))
        tr3 = abs(low - close.shift(1))

        true_range = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        return true_range.rolling(window=period, min_periods=period).mean()

    @staticmethod
    def williams_r(high: pd.Series,
                   low: pd.Series,
                   close: pd.Series,
                   period: int = 14) -> pd.Series:
        """Williams %R"""
        highest_high = high.rolling(window=period, min_periods=period).max()
        lowest_low = low.rolling(window=period, min_periods=period).min()

        range_val = highest_high - lowest_low
        wr = ((highest_high - close) / range_val.replace(0, np.nan)) * -100

        return wr.fillna(-50.0)

    @staticmethod
    def cci(high: pd.Series,
            low: pd.Series,
            close: pd.Series,
            period: int = 20) -> pd.Series:
        """Commodity Channel Index"""
        typical_price = (high + low + close) / 3
        sma_tp = typical_price.rolling(window=period, min_periods=period).mean()
        mean_deviation = typical_price.rolling(window=period, min_periods=period).apply(
            lambda x: np.mean(np.abs(x - x.mean()))
        )

        cci = (typical_price - sma_tp) / (0.015 * mean_deviation)
        return cci.fillna(0.0)

    @staticmethod
    def adx(high: pd.Series,
            low: pd.Series,
            close: pd.Series,
            period: int = 14) -> Tuple[pd.Series, pd.Series, pd.Series]:
        """Average Directional Index with +DI and -DI"""
        # True Range
        tr = TechnicalIndicators.atr(high, low, close, 1)

        # Directional Movements
        dm_plus = high.diff()
        dm_minus = -low.diff()

        # Set to 0 if not the larger movement
        dm_plus = dm_plus.where((dm_plus > dm_minus) & (dm_plus > 0), 0)
        dm_minus = dm_minus.where((dm_minus > dm_plus) & (dm_minus > 0), 0)

        # Smooth the values
        alpha = 1.0 / period
        atr_smooth = tr.ewm(alpha=alpha, adjust=False).mean()
        dm_plus_smooth = dm_plus.ewm(alpha=alpha, adjust=False).mean()
        dm_minus_smooth = dm_minus.ewm(alpha=alpha, adjust=False).mean()

        # Calculate DI+ and DI-
        di_plus = 100 * (dm_plus_smooth / atr_smooth)
        di_minus = 100 * (dm_minus_smooth / atr_smooth)

        # Calculate DX
        di_sum = di_plus + di_minus
        di_diff = abs(di_plus - di_minus)
        dx = 100 * (di_diff / di_sum.replace(0, np.nan))

        # Calculate ADX
        adx = dx.ewm(alpha=alpha, adjust=False).mean()

        return adx.fillna(25.0), di_plus.fillna(25.0), di_minus.fillna(25.0)

    @staticmethod
    def fibonacci_levels(high: float, low: float) -> dict:
        """Calculate Fibonacci retracement levels"""
        diff = high - low
        return {
            'level_0': high,
            'level_236': high - 0.236 * diff,
            'level_382': high - 0.382 * diff,
            'level_500': high - 0.500 * diff,
            'level_618': high - 0.618 * diff,
            'level_786': high - 0.786 * diff,
            'level_100': low
        }

    @staticmethod
    def pivot_points(high: float, low: float, close: float) -> dict:
        """Calculate pivot points and support/resistance levels"""
        pivot = (high + low + close) / 3

        return {
            'pivot': pivot,
            'r1': 2 * pivot - low,
            'r2': pivot + (high - low),
            'r3': high + 2 * (pivot - low),
            's1': 2 * pivot - high,
            's2': pivot - (high - low),
            's3': low - 2 * (high - pivot)
        }

    @staticmethod
    def ichimoku_cloud(high: pd.Series,
                       low: pd.Series,
                       close: pd.Series) -> dict:
        """Ichimoku Cloud components"""
        # Tenkan-sen (Conversion Line)
        tenkan_sen = ((high.rolling(9).max() + low.rolling(9).min()) / 2)

        # Kijun-sen (Base Line)
        kijun_sen = ((high.rolling(26).max() + low.rolling(26).min()) / 2)

        # Senkou Span A (Leading Span A)
        senkou_span_a = ((tenkan_sen + kijun_sen) / 2).shift(26)

        # Senkou Span B (Leading Span B)
        senkou_span_b = ((high.rolling(52).max() + low.rolling(52).min()) / 2).shift(26)

        # Chikou Span (Lagging Span)
        chikou_span = close.shift(-26)

        return {
            'tenkan_sen': tenkan_sen,
            'kijun_sen': kijun_sen,
            'senkou_span_a': senkou_span_a,
            'senkou_span_b': senkou_span_b,
            'chikou_span': chikou_span
        }


class MarketRegimeDetector:
    """
    Detect market regimes (trending vs mean-reverting)
    """

    @staticmethod
    def hurst_exponent(prices: pd.Series, max_lag: int = 20) -> float:
        """
        Calculate Hurst Exponent to determine market regime
        H > 0.5: Trending (momentum)
        H < 0.5: Mean reverting
        H = 0.5: Random walk
        """
        if len(prices) < max_lag * 2:
            return 0.5

        lags = range(2, max_lag)
        tau = []

        for lag in lags:
            # Calculate the variance of the differences
            pp = np.subtract(prices[lag:].values, prices[:-lag].values)
            tau.append(np.sqrt(np.std(pp)))

        # Linear regression on log-log plot
        tau = np.array(tau)
        lags = np.array(lags)

        # Remove any NaN or infinite values
        valid_idx = np.isfinite(tau) & (tau > 0)
        if not np.any(valid_idx):
            return 0.5

        tau = tau[valid_idx]
        lags = lags[valid_idx]

        try:
            poly = np.polyfit(np.log(lags), np.log(tau), 1)
            return poly[0] * 2.0
        except:
            return 0.5

    @staticmethod
    def trend_strength(prices: pd.Series, period: int = 20) -> float:
        """
        Calculate trend strength using R-squared of linear regression
        Returns value between 0 and 1
        """
        if len(prices) < period:
            return 0.0

        recent_prices = prices.tail(period)
        x = np.arange(len(recent_prices))

        try:
            # Linear regression
            poly = np.polyfit(x, recent_prices.values, 1)
            trend_line = np.polyval(poly, x)

            # Calculate R-squared
            ss_res = np.sum((recent_prices.values - trend_line) ** 2)
            ss_tot = np.sum((recent_prices.values - np.mean(recent_prices.values)) ** 2)

            if ss_tot == 0:
                return 0.0

            r_squared = 1 - (ss_res / ss_tot)
            return max(0.0, min(1.0, r_squared))

        except:
            return 0.0

    @staticmethod
    def volatility_regime(prices: pd.Series,
                          short_period: int = 10,
                          long_period: int = 30) -> str:
        """
        Classify volatility regime
        Returns: 'low', 'normal', 'high'
        """
        if len(prices) < long_period:
            return 'normal'

        # Calculate rolling volatilities
        returns = prices.pct_change().dropna()
        short_vol = returns.rolling(short_period).std() * np.sqrt(252)  # Annualized
        long_vol = returns.rolling(long_period).std() * np.sqrt(252)

        current_vol = short_vol.iloc[-1]
        avg_vol = long_vol.iloc[-1]

        if pd.isna(current_vol) or pd.isna(avg_vol):
            return 'normal'

        if current_vol < avg_vol * 0.8:
            return 'low'
        elif current_vol > avg_vol * 1.2:
            return 'high'
        else:
            return 'normal'


class AdvancedIndicators:
    """
    Advanced technical indicators and composite signals
    """

    @staticmethod
    def squeeze_momentum(high: pd.Series,
                         low: pd.Series,
                         close: pd.Series,
                         length: int = 20,
                         mult: float = 2.0,
                         length_kc: int = 20,
                         mult_kc: float = 1.5) -> dict:
        """
        TTM Squeeze indicator
        Identifies periods of low volatility followed by breakouts
        """
        # Bollinger Bands
        bb_upper, bb_middle, bb_lower = TechnicalIndicators.bollinger_bands(
            close, length, mult
        )

        # Keltner Channels
        tr = TechnicalIndicators.atr(high, low, close, 1)
        atr_val = tr.rolling(length_kc).mean()
        kc_upper = bb_middle + (mult_kc * atr_val)
        kc_lower = bb_middle - (mult_kc * atr_val)

        # Squeeze condition
        squeeze_on = (bb_lower > kc_lower) & (bb_upper < kc_upper)
        squeeze_off = (bb_lower < kc_lower) | (bb_upper > kc_upper)
        no_squeeze = ~(squeeze_on | squeeze_off)

        # Momentum
        highest = high.rolling(length_kc).max()
        lowest = low.rolling(length_kc).min()
        m1 = (highest + lowest) / 2
        momentum = close - (m1 + TechnicalIndicators.sma(close, length_kc)) / 2

        return {
            'squeeze_on': squeeze_on,
            'squeeze_off': squeeze_off,
            'no_squeeze': no_squeeze,
            'momentum': momentum
        }

    @staticmethod
    def composite_momentum(data: pd.DataFrame) -> pd.Series:
        """
        Composite momentum score combining multiple indicators
        Returns score between -100 and 100
        """
        close = data['Close']
        high = data['High']
        low = data['Low']

        # Individual momentum components
        rsi = TechnicalIndicators.rsi(close, 14)
        macd_line, macd_signal, _ = TechnicalIndicators.macd(close)
        stoch_k, stoch_d = TechnicalIndicators.stochastic(high, low, close)
        williams = TechnicalIndicators.williams_r(high, low, close)

        # Normalize indicators to -50 to 50 scale
        rsi_norm = (rsi - 50)  # Already -50 to 50
        macd_norm = np.where(macd_line > macd_signal, 25, -25)  # Binary signal
        stoch_norm = (stoch_k - 50)  # -50 to 50
        williams_norm = (williams + 50)  # Convert from -100,0 to -50,50

        # Combine with weights
        composite = (
                0.3 * rsi_norm +
                0.3 * macd_norm +
                0.2 * stoch_norm +
                0.2 * williams_norm
        )

        return composite.fillna(0)

    @staticmethod
    def mean_reversion_score(data: pd.DataFrame) -> pd.Series:
        """
        Mean reversion score based on multiple indicators
        Returns score between -100 and 100
        """
        close = data['Close']
        high = data['High']
        low = data['Low']

        # Bollinger Band position
        bb_upper, bb_middle, bb_lower = TechnicalIndicators.bollinger_bands(close)
        bb_position = (close - bb_lower) / (bb_upper - bb_lower) * 100
        bb_score = 50 - bb_position  # Invert: low position = high score

        # Z-score
        sma_20 = close.rolling(20).mean()
        std_20 = close.rolling(20).std()
        z_score = (close - sma_20) / std_20
        z_score_norm = np.clip(-z_score * 25, -50, 50)  # Scale and invert

        # RSI mean reversion
        rsi = TechnicalIndicators.rsi(close)
        rsi_mr = np.where(rsi > 70, rsi - 70, np.where(rsi < 30, 30 - rsi, 0))
        rsi_mr_norm = np.clip(rsi_mr * 2.5, -50, 50)

        # Combine scores
        mr_score = (
                0.4 * bb_score +
                0.4 * z_score_norm +
                0.2 * rsi_mr_norm
        )

        return mr_score.fillna(0)