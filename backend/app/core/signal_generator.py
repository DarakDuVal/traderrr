"""
app/core/signal_generator.py - Advanced trading signal generation system
Combines multiple technical indicators with market regime detection
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional
from dataclasses import dataclass
from datetime import datetime
import logging
from enum import Enum

from .indicators import TechnicalIndicators, MarketRegimeDetector, AdvancedIndicators


class SignalType(Enum):
    BUY = "BUY"
    SELL = "SELL"
    HOLD = "HOLD"
    STRONG_BUY = "STRONG_BUY"
    STRONG_SELL = "STRONG_SELL"


class MarketRegime(Enum):
    TRENDING_UP = "TRENDING_UP"
    TRENDING_DOWN = "TRENDING_DOWN"
    MEAN_REVERTING = "MEAN_REVERTING"
    SIDEWAYS = "SIDEWAYS"
    HIGH_VOLATILITY = "HIGH_VOLATILITY"


@dataclass
class TradingSignal:
    ticker: str
    signal_type: SignalType
    confidence: float
    entry_price: float
    stop_loss: float
    target_price: float
    regime: MarketRegime
    indicators: Dict[str, float]
    timestamp: datetime
    reasons: List[str]


class SignalGenerator:
    """
    Advanced signal generator that adapts strategy based on market regime
    """

    def __init__(
        self,
        momentum_threshold: float = 60.0,
        mean_reversion_threshold: float = 70.0,
        volatility_factor: float = 2.0,
        min_confidence: float = 0.6,
    ):

        self.momentum_threshold = momentum_threshold
        self.mean_reversion_threshold = mean_reversion_threshold
        self.volatility_factor = volatility_factor
        self.min_confidence = min_confidence

        self.ti = TechnicalIndicators()
        self.regime_detector = MarketRegimeDetector()
        self.advanced = AdvancedIndicators()

        self.logger = logging.getLogger(__name__)

    def generate_signal(
        self, ticker: str, data: pd.DataFrame
    ) -> Optional[TradingSignal]:
        """
        Generate trading signal for a single ticker

        Args:
            ticker: Stock symbol
            data: OHLCV DataFrame with at least 50 periods

        Returns:
            TradingSignal object or None if no signal
        """
        if len(data) < 50:
            self.logger.warning(f"Insufficient data for {ticker}: {len(data)} periods")
            return None

        try:
            # Get current market regime
            regime = self._detect_market_regime(data)

            # Calculate all indicators
            indicators = self._calculate_indicators(data)

            # Generate signal based on regime
            if regime in [MarketRegime.TRENDING_UP, MarketRegime.TRENDING_DOWN]:
                signal_data = self._momentum_strategy(data, indicators, regime)
            else:
                signal_data = self._mean_reversion_strategy(data, indicators, regime)

            if signal_data is None:
                return None

            # Calculate confidence score
            confidence = self._calculate_confidence(
                indicators, regime, signal_data["signal_type"]
            )

            if confidence < self.min_confidence:
                return None

            # Calculate stop loss and target
            current_price = data["Close"].iloc[-1]
            atr = indicators["atr"]

            if signal_data["signal_type"] in [SignalType.BUY, SignalType.STRONG_BUY]:
                stop_loss = current_price - (atr * self.volatility_factor)
                target_price = current_price + (atr * self.volatility_factor * 2)
            else:
                stop_loss = current_price + (atr * self.volatility_factor)
                target_price = current_price - (atr * self.volatility_factor * 2)

            return TradingSignal(
                ticker=ticker,
                signal_type=signal_data["signal_type"],
                confidence=confidence,
                entry_price=current_price,
                stop_loss=stop_loss,
                target_price=target_price,
                regime=regime,
                indicators=indicators,
                timestamp=datetime.now(),
                reasons=signal_data["reasons"],
            )

        except Exception as e:
            self.logger.error(f"Error generating signal for {ticker}: {e}")
            return None

    def generate_portfolio_signals(
        self, portfolio_data: Dict[str, pd.DataFrame]
    ) -> List[TradingSignal]:
        """
        Generate signals for entire portfolio

        Args:
            portfolio_data: Dict mapping ticker to OHLCV DataFrame

        Returns:
            List of TradingSignal objects
        """
        signals = []

        for ticker, data in portfolio_data.items():
            signal = self.generate_signal(ticker, data)
            if signal:
                signals.append(signal)

        # Sort by confidence score (highest first)
        signals.sort(key=lambda x: x.confidence, reverse=True)

        return signals

    def _detect_market_regime(self, data: pd.DataFrame) -> MarketRegime:
        """Detect current market regime"""
        close = data["Close"]

        # Calculate regime indicators
        hurst = self.regime_detector.hurst_exponent(close)
        trend_strength = self.regime_detector.trend_strength(close)
        vol_regime = self.regime_detector.volatility_regime(close)

        # Determine trend direction
        sma_short = close.rolling(20).mean().iloc[-1]
        sma_long = close.rolling(50).mean().iloc[-1]
        trend_up = sma_short > sma_long

        # Classify regime
        if vol_regime == "high":
            return MarketRegime.HIGH_VOLATILITY
        elif hurst > 0.55 and trend_strength > 0.7:
            return MarketRegime.TRENDING_UP if trend_up else MarketRegime.TRENDING_DOWN
        elif hurst < 0.45:
            return MarketRegime.MEAN_REVERTING
        else:
            return MarketRegime.SIDEWAYS

    def _calculate_indicators(self, data: pd.DataFrame) -> Dict[str, float]:
        """Calculate all technical indicators"""
        close = data["Close"]
        high = data["High"]
        low = data["Low"]
        volume = data["Volume"]

        indicators = {}

        try:
            # Price-based indicators
            indicators["rsi"] = self.ti.rsi(close, 14).iloc[-1]
            indicators["rsi_oversold"] = indicators["rsi"] < 30
            indicators["rsi_overbought"] = indicators["rsi"] > 70

            # MACD
            macd_line, signal_line, histogram = self.ti.macd(close)
            indicators["macd"] = macd_line.iloc[-1]
            indicators["macd_signal"] = signal_line.iloc[-1]
            indicators["macd_histogram"] = histogram.iloc[-1]
            indicators["macd_bullish"] = indicators["macd"] > indicators["macd_signal"]

            # Bollinger Bands
            bb_upper, bb_middle, bb_lower = self.ti.bollinger_bands(close)
            indicators["bb_upper"] = bb_upper.iloc[-1]
            indicators["bb_middle"] = bb_middle.iloc[-1]
            indicators["bb_lower"] = bb_lower.iloc[-1]

            # Calculate BB position safely to avoid division by zero
            bb_range = bb_upper.iloc[-1] - bb_lower.iloc[-1]
            if bb_range > 1e-10:  # Avoid division by zero when bands are equal
                indicators["bb_position"] = (
                    close.iloc[-1] - bb_lower.iloc[-1]
                ) / bb_range
            else:
                # If bands are equal, price is at middle
                indicators["bb_position"] = 0.5

            # Stochastic
            stoch_k, stoch_d = self.ti.stochastic(high, low, close)
            indicators["stoch_k"] = stoch_k.iloc[-1]
            indicators["stoch_d"] = stoch_d.iloc[-1]
            indicators["stoch_oversold"] = indicators["stoch_k"] < 20
            indicators["stoch_overbought"] = indicators["stoch_k"] > 80

            # Williams %R
            indicators["williams_r"] = self.ti.williams_r(high, low, close).iloc[-1]

            # ATR for volatility
            indicators["atr"] = self.ti.atr(high, low, close).iloc[-1]

            # ADX for trend strength
            adx, di_plus, di_minus = self.ti.adx(high, low, close)
            indicators["adx"] = adx.iloc[-1]
            indicators["di_plus"] = di_plus.iloc[-1]
            indicators["di_minus"] = di_minus.iloc[-1]
            indicators["strong_trend"] = indicators["adx"] > 25

            # Moving averages
            indicators["sma_20"] = close.rolling(20).mean().iloc[-1]
            indicators["sma_50"] = close.rolling(50).mean().iloc[-1]
            indicators["ema_12"] = self.ti.ema(close, 12).iloc[-1]
            indicators["ema_26"] = self.ti.ema(close, 26).iloc[-1]

            # Price relative to moving averages
            current_price = close.iloc[-1]
            indicators["above_sma_20"] = current_price > indicators["sma_20"]
            indicators["above_sma_50"] = current_price > indicators["sma_50"]
            indicators["ma_bullish"] = indicators["sma_20"] > indicators["sma_50"]

            # Volume indicators
            indicators["volume_sma"] = volume.rolling(20).mean().iloc[-1]
            indicators["volume_ratio"] = volume.iloc[-1] / indicators["volume_sma"]
            indicators["volume_surge"] = indicators["volume_ratio"] > 1.5

            # Advanced composite indicators
            indicators["momentum_score"] = self.advanced.composite_momentum(data).iloc[
                -1
            ]
            indicators["mean_reversion_score"] = self.advanced.mean_reversion_score(
                data
            ).iloc[-1]

            # Squeeze momentum
            squeeze_data = self.advanced.squeeze_momentum(high, low, close)
            indicators["squeeze_on"] = squeeze_data["squeeze_on"].iloc[-1]
            indicators["squeeze_momentum"] = squeeze_data["momentum"].iloc[-1]

        except Exception as e:
            self.logger.error(f"Error calculating indicators: {e}")
            # Return minimal indicators if calculation fails
            indicators = {
                "rsi": 50.0,
                "macd": 0.0,
                "bb_position": 0.5,
                "atr": close.std() if len(close) > 1 else 1.0,
                "momentum_score": 0.0,
                "mean_reversion_score": 0.0,
            }

        return indicators

    def _momentum_strategy(
        self, data: pd.DataFrame, indicators: Dict[str, float], regime: MarketRegime
    ) -> Optional[Dict]:
        """Generate momentum-based signals"""
        reasons = []

        # Bullish momentum conditions
        bullish_conditions = 0
        bearish_conditions = 0

        # MACD signal
        if indicators.get("macd_bullish", False):
            bullish_conditions += 1
            reasons.append("MACD bullish crossover")
        else:
            bearish_conditions += 1
            reasons.append("MACD bearish crossover")

        # RSI momentum (not extreme)
        rsi = indicators.get("rsi", 50)
        if 45 < rsi < 75:
            bullish_conditions += 1
            reasons.append("RSI in bullish momentum range")
        elif rsi < 45:
            bearish_conditions += 1
            reasons.append("RSI showing bearish momentum")

        # Moving average alignment
        if indicators.get("above_sma_20", False) and indicators.get(
            "ma_bullish", False
        ):
            bullish_conditions += 1
            reasons.append("Price above MA20 and MA bullish")
        elif not indicators.get("above_sma_20", True) and not indicators.get(
            "ma_bullish", True
        ):
            bearish_conditions += 1
            reasons.append("Price below MA20 and MA bearish")

        # ADX trend strength
        if indicators.get("strong_trend", False):
            if indicators.get("di_plus", 0) > indicators.get("di_minus", 0):
                bullish_conditions += 1
                reasons.append("Strong uptrend confirmed by ADX")
            else:
                bearish_conditions += 1
                reasons.append("Strong downtrend confirmed by ADX")

        # Volume confirmation
        if indicators.get("volume_surge", False):
            if bullish_conditions > bearish_conditions:
                bullish_conditions += 1
                reasons.append("Volume surge confirms bullish momentum")
            else:
                bearish_conditions += 1
                reasons.append("Volume surge confirms bearish momentum")

        # Momentum score
        momentum_score = indicators.get("momentum_score", 0)
        if momentum_score > 30:
            bullish_conditions += 1
            reasons.append("Composite momentum score bullish")
        elif momentum_score < -30:
            bearish_conditions += 1
            reasons.append("Composite momentum score bearish")

        # Generate signal
        if bullish_conditions >= 4:
            if bullish_conditions >= 5:
                return {"signal_type": SignalType.STRONG_BUY, "reasons": reasons}
            else:
                return {"signal_type": SignalType.BUY, "reasons": reasons}
        elif bearish_conditions >= 4:
            if bearish_conditions >= 5:
                return {"signal_type": SignalType.STRONG_SELL, "reasons": reasons}
            else:
                return {"signal_type": SignalType.SELL, "reasons": reasons}

        return None

    def _mean_reversion_strategy(
        self, data: pd.DataFrame, indicators: Dict[str, float], regime: MarketRegime
    ) -> Optional[Dict]:
        """Generate mean reversion signals"""
        reasons = []

        # Mean reversion buy conditions (oversold)
        buy_conditions = 0
        sell_conditions = 0

        # RSI oversold/overbought
        if indicators.get("rsi_oversold", False):
            buy_conditions += 1
            reasons.append("RSI oversold")
        elif indicators.get("rsi_overbought", False):
            sell_conditions += 1
            reasons.append("RSI overbought")

        # Bollinger Band position
        bb_position = indicators.get("bb_position", 0.5)
        if bb_position < 0.1:  # Near lower band
            buy_conditions += 1
            reasons.append("Price near Bollinger Band lower band")
        elif bb_position > 0.9:  # Near upper band
            sell_conditions += 1
            reasons.append("Price near Bollinger Band upper band")

        # Stochastic oversold/overbought
        if indicators.get("stoch_oversold", False):
            buy_conditions += 1
            reasons.append("Stochastic oversold")
        elif indicators.get("stoch_overbought", False):
            sell_conditions += 1
            reasons.append("Stochastic overbought")

        # Williams %R
        williams = indicators.get("williams_r", -50)
        if williams < -80:
            buy_conditions += 1
            reasons.append("Williams %R oversold")
        elif williams > -20:
            sell_conditions += 1
            reasons.append("Williams %R overbought")

        # Mean reversion score
        mr_score = indicators.get("mean_reversion_score", 0)
        if mr_score > 40:
            buy_conditions += 1
            reasons.append("Mean reversion score indicates oversold")
        elif mr_score < -40:
            sell_conditions += 1
            reasons.append("Mean reversion score indicates overbought")

        # Volume confirmation (higher volume on reversals)
        if indicators.get("volume_surge", False):
            if buy_conditions > sell_conditions:
                buy_conditions += 1
                reasons.append("Volume surge confirms oversold reversal")
            elif sell_conditions > buy_conditions:
                sell_conditions += 1
                reasons.append("Volume surge confirms overbought reversal")

        # Generate signal
        if buy_conditions >= 3:
            if buy_conditions >= 4:
                return {"signal_type": SignalType.STRONG_BUY, "reasons": reasons}
            else:
                return {"signal_type": SignalType.BUY, "reasons": reasons}
        elif sell_conditions >= 3:
            if sell_conditions >= 4:
                return {"signal_type": SignalType.STRONG_SELL, "reasons": reasons}
            else:
                return {"signal_type": SignalType.SELL, "reasons": reasons}

        return None

    def _calculate_confidence(
        self,
        indicators: Dict[str, float],
        regime: MarketRegime,
        signal_type: SignalType,
    ) -> float:
        """Calculate confidence score for the signal"""
        confidence = 0.5  # Base confidence

        # Regime-signal alignment
        if regime in [MarketRegime.TRENDING_UP, MarketRegime.TRENDING_DOWN]:
            if (
                signal_type in [SignalType.BUY, SignalType.STRONG_BUY]
                and regime == MarketRegime.TRENDING_UP
            ):
                confidence += 0.2
            elif (
                signal_type in [SignalType.SELL, SignalType.STRONG_SELL]
                and regime == MarketRegime.TRENDING_DOWN
            ):
                confidence += 0.2
        else:  # Mean reverting or sideways
            # Mean reversion signals get boost in ranging markets
            confidence += 0.1

        # Strong trend confirmation
        if indicators.get("strong_trend", False):
            confidence += 0.1

        # Volume confirmation
        if indicators.get("volume_surge", False):
            confidence += 0.1

        # Multiple indicator agreement
        momentum_score = abs(indicators.get("momentum_score", 0))
        mr_score = abs(indicators.get("mean_reversion_score", 0))

        if momentum_score > 50 or mr_score > 50:
            confidence += 0.1

        # Bollinger band extremes
        bb_position = indicators.get("bb_position", 0.5)
        if bb_position < 0.1 or bb_position > 0.9:
            confidence += 0.1

        # RSI extremes
        rsi = indicators.get("rsi", 50)
        if rsi < 25 or rsi > 75:
            confidence += 0.1

        # Strong signal bonus
        if signal_type in [SignalType.STRONG_BUY, SignalType.STRONG_SELL]:
            confidence += 0.1

        return min(1.0, confidence)

    def get_signal_summary(self, signals: List[TradingSignal]) -> Dict:
        """Generate summary of portfolio signals"""
        if not signals:
            return {
                "total_signals": 0,
                "buy_signals": 0,
                "sell_signals": 0,
                "average_confidence": 0.0,
                "top_picks": [],
            }

        buy_signals = len(
            [
                s
                for s in signals
                if s.signal_type in [SignalType.BUY, SignalType.STRONG_BUY]
            ]
        )
        sell_signals = len(
            [
                s
                for s in signals
                if s.signal_type in [SignalType.SELL, SignalType.STRONG_SELL]
            ]
        )
        avg_confidence = np.mean([s.confidence for s in signals])

        # Top 3 highest confidence signals
        top_picks = signals[:3]

        return {
            "total_signals": len(signals),
            "buy_signals": buy_signals,
            "sell_signals": sell_signals,
            "average_confidence": avg_confidence,
            "top_picks": [
                {
                    "ticker": s.ticker,
                    "signal": s.signal_type.value,
                    "confidence": s.confidence,
                    "regime": s.regime.value,
                    "reasons": s.reasons,
                }
                for s in top_picks
            ],
        }
