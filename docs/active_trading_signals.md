# 📊 Active Trading Signals: Complete Decision Flow

## Quick Answer

  A ticker appears in the active signals list when:
  1. It has ≥50 periods of historical data
  2. One of two strategies triggers (momentum OR mean reversion)
  3. The signal passes the confidence threshold (≥0.6 or 60%)
  4. Results are sorted by confidence (highest first)

---

## The Complete Decision Pipeline

  Step 1: DATA CHECK
  ├─ Is data length < 50?
  │  └─ YES → ❌ Return None (skip ticker)
  │  └─ NO → Continue
  │
  Step 2: DETECT MARKET REGIME (app/core/signal_generator.py:157-179)
  ├─ Calculate Hurst Exponent, Trend Strength, Volatility
  ├─ Check SMA(20) vs SMA(50) alignment
  └─ Classify as: TRENDING_UP | TRENDING_DOWN | MEAN_REVERTING | SIDEWAYS | HIGH_VOLATILITY
  │
  Step 3: SELECT STRATEGY BASED ON REGIME
  ├─ IF regime = TRENDING → Run MOMENTUM strategy (line 271-346)
  └─ ELSE (MEAN_REVERTING, SIDEWAYS, HIGH_VOLATILITY) → Run MEAN REVERSION strategy (line 348-423)
  │
  Step 4: COUNT CONDITIONS
  ├─ MOMENTUM strategy needs ≥4 bullish OR bearish conditions
  ├─ MEAN REVERSION strategy needs ≥3 buy OR sell conditions
  └─ If neither threshold met → ❌ Return None (skip ticker)
  │
  Step 5: CALCULATE CONFIDENCE SCORE (line 425-471)
  ├─ Base: 0.5 (50%)
  ├─ Add bonuses for: regime alignment, strong trends, volume, extremes
  ├─ Cap at: 1.0 (100%)
  └─ If confidence < 0.6 → ❌ Return None (filtered out)
  │
  Step 6: CALCULATE TRADE PARAMETERS
  ├─ Entry Price = Current Close (line 107)
  ├─ Stop Loss & Target = ATR-based (line 110-115)
  └─ Create TradingSignal object (line 117-128)
  │
  Step 7: RETURN & SORT
  ├─ Collect all generated signals
  ├─ Sort by confidence DESC (line 152-153)
  └─ ✅ Return ordered list to API

---

### SECTION 1: The Data Requirement Filter

  Code Location: app/core/signal_generator.py:80-82

  if len(data) < 50:
      self.logger.warning(f"Insufficient data for {ticker}: {len(data)} periods")
      return None

  What this means:
  - Each ticker must have at least 50 trading days of historical data
  - Young stocks or delisted symbols get filtered out
  - This ensures reliable indicator calculations (RSI, MACD, moving averages all need history)

  Why 50 periods?
  - Technical indicators need enough historical context
  - 50 days ≈ 2.5 months of trading history = statistical reliability

---

### SECTION 2: Market Regime Detection

  Code Location: app/core/signal_generator.py:157-179

  def _detect_market_regime(self, data: pd.DataFrame) -> MarketRegime:
      """Detect current market regime"""
      hurst = self.regime_detector.hurst_exponent(close)        # Trend vs Mean Reversion
      trend_strength = self.regime_detector.trend_strength(close) # R² on linear regression
      vol_regime = self.regime_detector.volatility_regime(close) # High/Normal/Low

      sma_short = close.rolling(20).mean().iloc[-1]
      sma_long = close.rolling(50).mean().iloc[-1]
      trend_up = sma_short > sma_long

      # Regime Classification
      if vol_regime == 'high':
          return MarketRegime.HIGH_VOLATILITY
      elif hurst > 0.55 and trend_strength > 0.7:
          return MarketRegime.TRENDING_UP if trend_up else MarketRegime.TRENDING_DOWN
      elif hurst < 0.45:
          return MarketRegime.MEAN_REVERTING
      else:
          return MarketRegime.SIDEWAYS

  Regime Decision Matrix:

  | Condition                                      | Regime          | Strategy       |
  |------------------------------------------------|-----------------|----------------|
  | Volatility is HIGH                             | HIGH_VOLATILITY | Mean Reversion |
  | Hurst > 0.55 AND Trend > 0.7 AND SMA20 > SMA50 | TRENDING_UP     | Momentum       |
  | Hurst > 0.55 AND Trend > 0.7 AND SMA20 < SMA50 | TRENDING_DOWN   | Momentum       |
  | Hurst < 0.45                                   | MEAN_REVERTING  | Mean Reversion |
  | Everything else                                | SIDEWAYS        | Mean Reversion |

  Key Insight: The system adapts its strategy based on what the market is currently doing, not using a fixed approach for all conditions.

---

### SECTION 3A: Momentum Strategy (Trending Markets)

  Trigger Condition: Market regime is TRENDING_UP or TRENDING_DOWN

  Code Location: app/core/signal_generator.py:271-346

  For BUY Signals, checks these 6 conditions (lines 282-332):

  | Condition              | Code                                    | Reason                              |
  |------------------------|-----------------------------------------|-------------------------------------|
  | MACD bullish crossover | macd > macd_signal (line 283)           | MACD line crosses above signal line |
  | RSI momentum           | 45 < rsi < 75 (line 292)                | Not extreme, shows healthy momentum |
  | Moving avg bullish     | price > MA20 AND MA20 > MA50 (line 300) | Trend aligned                       |
  | Strong trend + DI+     | ADX > 25 AND DI+ > DI- (line 308-311)   | Directional Movement confirms       |
  | Volume surge           | volume > 1.5x average (line 317-320)    | Conviction in move                  |
  | Momentum score         | composite_momentum > 30 (line 327)      | Composite indicator agrees          |

  Signal Generation (lines 335-344):
  if bullish_conditions >= 4:
      if bullish_conditions >= 5:
          return {'signal_type': SignalType.STRONG_BUY, 'reasons': [...]}
      else:
          return {'signal_type': SignalType.BUY, 'reasons': [...]}

  Example Scenario:
  Ticker: NVDA in TRENDING_UP market
  ✅ MACD bullish (condition 1)
  ✅ RSI = 62 (condition 2)
  ✅ Price above MA20, MA bullish (condition 3)
  ✅ ADX = 28, DI+ > DI- (condition 4)
  ✅ Volume 2.1x average (condition 5)
  ❌ Momentum score = 25 (condition 6)

  Result: 5 conditions met → STRONG_BUY signal generated

---

### SECTION 3B: Mean Reversion Strategy (Ranging/Volatile Markets)

  Trigger Condition: Market regime is MEAN_REVERTING, SIDEWAYS, or HIGH_VOLATILITY

  Code Location: app/core/signal_generator.py:348-423

  For BUY Signals, checks these 5 conditions (lines 359-400):

  | Condition           | Code                                 | Reason                      |
  |---------------------|--------------------------------------|-----------------------------|
  | RSI oversold        | rsi < 30 (line 360)                  | Stock is beaten down        |
  | BB lower band       | bb_position < 0.1 (line 369)         | Price near lower support    |
  | Stochastic oversold | stoch_k < 20 (line 377)              | Momentum indicator confirms |
  | Williams %R         | williams < -80 (line 386)            | Alternative oversold metric |
  | MR score            | mean_reversion_score > 40 (line 395) | Composite says oversold     |

  Signal Generation (lines 411-421):
  if buy_conditions >= 3:
      if buy_conditions >= 4:
          return {'signal_type': SignalType.STRONG_BUY, 'reasons': [...]}
      else:
          return {'signal_type': SignalType.BUY, 'reasons': [...]}

  Example Scenario:
  Ticker: AAPL in SIDEWAYS market
  ✅ RSI = 28 (condition 1)
  ✅ BB position = 0.08 (condition 2)
  ✅ Stoch %K = 18 (condition 3)
  ❌ Williams %R = -60 (not < -80)
  ✅ MR score = 52 (condition 5)

  Result: 4 conditions met → STRONG_BUY signal generated

---

### SECTION 4: Confidence Score Calculation

  Code Location: app/core/signal_generator.py:425-471

  Scoring System:
  confidence = 0.5  # Base score (50%)

  # Add bonuses (each max 0.1, capped at 1.0 total)
  if regime_matches_signal:           # Line 433-440
      confidence += 0.2  # Biggest bonus: regime alignment

  if strong_trend (ADX > 25):          # Line 443
      confidence += 0.1

  if volume_surge (volume > 1.5x):     # Line 447
      confidence += 0.1

  if momentum_score > 50 OR mr_score > 50:  # Line 454
      confidence += 0.1

  if bb_position < 0.1 OR > 0.9:      # Line 459
      confidence += 0.1

  if rsi < 25 OR > 75:                 # Line 464
      confidence += 0.1

  if STRONG_BUY or STRONG_SELL:        # Line 468
      confidence += 0.1

  return min(confidence, 1.0)  # Cap at 100%

  Real Scoring Examples:

  Example 1: STRONG_BUY in TRENDING_UP market
  0.5 base
  + 0.2 regime alignment (BUY signal in TRENDING_UP)
  + 0.1 strong trend (ADX = 30)
  + 0.1 volume confirmation
  + 0.1 strong signal type
  = 1.0 (100% confidence) ✅ PASSES

  Example 2: BUY in SIDEWAYS market
  0.5 base
  + 0.1 ranging market alignment
  + 0.1 BB extremes
  = 0.7 (70% confidence) ✅ PASSES

  Example 3: SELL in TRENDING_UP market
  0.5 base
  + 0.0 (no regime alignment - sell signal in uptrend)
  + 0.1 BB extreme
  = 0.6 (60% confidence) ✅ BARELY PASSES (threshold is 0.6)

  Example 4: WEAK signal
  0.5 base
  + 0.0 no regime bonus
  + 0.0 no other bonuses
  = 0.5 (50% confidence) ❌ FILTERED OUT (threshold is 0.6)

  The Minimum Confidence Check (line 103-104):
  if confidence < self.min_confidence:  # self.min_confidence = 0.6
      return None  # Signal rejected, ticker excluded from list

---

### SECTION 5: Position Sizing (Stop Loss & Target)

  Code Location: app/core/signal_generator.py:106-115

  current_price = data['Close'].iloc[-1]
  atr = indicators['atr']  # Average True Range (volatility measure)

  # For BUY signals
  if signal_data['signal_type'] in [SignalType.BUY, SignalType.STRONG_BUY]:
      stop_loss = current_price - (atr * self.volatility_factor)  # 2 × ATR
      target_price = current_price + (atr * self.volatility_factor * 2)  # 4 × ATR

  # For SELL signals
  else:
      stop_loss = current_price + (atr * self.volatility_factor)
      target_price = current_price - (atr * self.volatility_factor * 2)

  Why ATR-based?
  - ATR scales with volatility
  - High volatility stocks get wider stops (less likely to be stopped out by noise)
  - Low volatility stocks get tight stops (more precise entries)

  Practical Example:
  Ticker: TSLA
  Current Price: $250
  ATR: $10
  Volatility Factor: 2.0

  BUY Signal:
  Stop Loss = $250 - (10 × 2) = $230 (2% risk)
  Target = $250 + (10 × 2 × 2) = $290 (16% reward)
  Risk/Reward Ratio: 1:8

---

### SECTION 6: Portfolio Collection & Sorting

  Code Location: app/core/signal_generator.py:134-155

  def generate_portfolio_signals(self, portfolio_data: Dict[str, pd.DataFrame]) -> List[TradingSignal]:
      signals = []

      for ticker, data in portfolio_data.items():
          signal = self.generate_signal(ticker, data)  # Run through entire pipeline
          if signal:
              signals.append(signal)  # Only include tickers that passed ALL filters

      # Sort by confidence score (highest first)
      signals.sort(key=lambda x: x.confidence, reverse=True)

      return signals

  Key Point: Only tickers where generate_signal() returns a non-None TradingSignal object appear in the list.

---

### SECTION 7: API Response Format

  Code Location: app/api/routes.py:67-94

  When you call /api/signals, you get:

  {
    "signals": [
      {
        "ticker": "NVDA",
        "signal_type": "STRONG_BUY",
        "confidence": 0.95,
        "entry_price": 250.50,
        "stop_loss": 230.20,
        "target_price": 290.30,
        "regime": "TRENDING_UP",
        "reasons": [
          "MACD bullish crossover",
          "RSI in bullish momentum range",
          "Price above MA20 and MA bullish",
          "Strong uptrend confirmed by ADX",
          "Volume surge confirms bullish momentum",
          "Composite momentum score bullish"
        ],
        "timestamp": "2025-01-15T10:30:00"
      },
      ...more signals sorted by confidence...
    ],
    "last_update": "2025-01-15T10:30:00",
    "total_count": 5
  }

---

### Why a Ticker DOESN'T Appear

  A ticker is excluded if:

  | Reason               | Line    | Example                                        |
  |----------------------|---------|------------------------------------------------|
  | Insufficient data    | 80-82   | Only 30 days of history available              |
  | No strategy triggers | 97-98   | Only 2 bullish conditions (need 4 in momentum) |
  | Confidence too low   | 103-104 | Confidence = 0.55 (threshold is 0.60)          |
  | Wrong regime match   | 434-440 | SELL signal in TRENDING_UP market              |
  | Weak indicators      | All     | No volume surge, RSI normal, MACD not bullish  |

---

### Summary Decision Tree

  ┌─ Fetch data for all portfolio tickers
  │
  ├─ For each ticker:
  │  ├─ Data >= 50 periods? → NO → Skip
  │  │
  │  ├─ Detect regime (trending, ranging, volatile?)
  │  │
  │  ├─ Apply appropriate strategy (momentum or mean reversion)
  │  │  ├─ Momentum: Need 4+ conditions
  │  │  └─ Mean Rev: Need 3+ conditions
  │  │  → Either way, no signal? → Skip
  │  │
  │  ├─ Calculate confidence (0.5 base + bonuses)
  │  │  └─ Confidence < 0.6? → Skip
  │  │
  │  └─ Create TradingSignal with:
  │     ├─ Signal type (BUY, SELL, STRONG_BUY, STRONG_SELL)
  │     ├─ Confidence score (0.6 to 1.0)
  │     ├─ Entry, Stop Loss, Target prices
  │     └─ Reasons list
  │
  └─ Sort all signals by confidence (DESC)
     └─ Return to API

---

### Real-World Example: Complete Ticker Journey

  Scenario: Checking MSFT on 2025-01-15

  STEP 1: Data Check
  ✅ 252 trading days available (> 50)

  STEP 2: Market Regime
  - Hurst Exponent: 0.62 (trending)
  - Trend Strength: 0.78 (strong)
  - Volatility: Normal
  - SMA(20)=420 > SMA(50)=410 (uptrend)
  → REGIME = TRENDING_UP

  STEP 3: Select Strategy
  → MOMENTUM strategy (because TRENDING_UP)

  STEP 4: Count Conditions
  1. MACD: 5.2 > 3.1 (signal line) ✅
  2. RSI: 62 (between 45-75) ✅
  3. Price: 425 > MA20=420, MA20 > MA50 ✅
  4. ADX: 28 > 25, DI+:18 > DI-:12 ✅
  5. Volume: 65M / avg 42M = 1.55x > 1.5 ✅
  6. Momentum Score: 45 > 30 ✅

  → 6 CONDITIONS MET → STRONG_BUY signal

  STEP 5: Calculate Confidence
  - Base: 0.50
  - Regime alignment (BUY in TRENDING_UP): +0.2
  - Strong trend (ADX > 25): +0.1
  - Volume surge: +0.1
  - Momentum score > 50: +0.1
  - Strong signal type: +0.1
  → Total: 1.0 (capped)

  STEP 6: Position Sizing
  - Current Price: $425
  - ATR: $8.50
  - Stop Loss: 425 - (8.5 × 2) = $408
  - Target: 425 + (8.5 × 2 × 2) = $459

  STEP 7: Create Signal Object
  ✅ MSFT appears in active signals list with:
     - Signal Type: STRONG_BUY
     - Confidence: 1.0 (100%)
     - Entry: $425
     - Stop: $408
     - Target: $459
     - Reasons: [list of 6 conditions that triggered]

  FINAL: Sorted with all other signals by confidence
  → If this is highest confidence, appears first in /api/signals

  ---
  This is the complete system. A ticker shows up when it passes all these filters, starting with data availability, through the appropriate strategy, and finally confidence threshold. The system is regime-aware and adaptive, not rigid.
  