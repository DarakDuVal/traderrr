# 📊 Active Trading Signals: Complete Decision Flow

## Quick answer

A ticker appears in the active signals list when:

1. It has **≥ 50 periods** of historical data.  
2. One of two strategies triggers (**momentum** OR **mean reversion**).  
3. The signal passes the confidence threshold (**≥ 0.6 / 60%**).  
4. Results are sorted by confidence (highest first).

---

## The complete decision pipeline

**Step 1 — Data check**  
- If `len(data) < 50` → skip ticker (insufficient data)

**Step 2 — Detect market regime**  
*(code: `app/core/signal_generator.py:157-179`)*

- Calculate Hurst exponent, trend strength, volatility  
- Compare `SMA(20)` vs `SMA(50)`  
- Classify as: `TRENDING_UP`, `TRENDING_DOWN`, `MEAN_REVERTING`, `SIDEWAYS`, `HIGH_VOLATILITY`

**Step 3 — Select strategy based on regime**

- `TRENDING` → run **MOMENTUM** strategy  
- `MEAN_REVERTING`, `SIDEWAYS`, `HIGH_VOLATILITY` → run **MEAN REVERSION** strategy

**Step 4 — Count conditions**

- **Momentum** needs ≥ 4 bullish OR bearish conditions  
- **Mean reversion** needs ≥ 3 buy OR sell conditions  
- If threshold not met → skip ticker

**Step 5 — Calculate confidence score**  
*(code: `app/core/signal_generator.py:425-471`)*

- Base: `0.5` (50%)  
- Add bonuses for regime alignment, trend strength, volume, extremes  
- Cap at `1.0` (100%)  
- If `confidence < 0.6` → skip ticker

**Step 6 — Calculate trade parameters**

- Entry price = current close  
- Stop loss & target = ATR-based  
- Create `TradingSignal` object

**Step 7 — Return & sort**

- Collect generated signals  
- Sort by confidence (highest first)  
- Return ordered list to API

---

## Section 1 — The data requirement filter

**Code location:** `app/core/signal_generator.py:80-82`

```py
if len(data) < 50:
    self.logger.warning(f"Insufficient data for {ticker}: {len(data)} periods")
    return None
```

What this means:

- Each ticker must have at least 50 trading days of historical data.  
- Young stocks or delisted symbols get filtered out.  
- Ensures reliable indicator calculations (RSI, MACD, moving averages).

Why 50 periods?

- Technical indicators need history.  
- ~50 trading days ≈ 2.5 months → statistical reliability.

---

## Section 2 — Market regime detection

**Code location:** `app/core/signal_generator.py:157-179`

```py
def _detect_market_regime(self, data: pd.DataFrame) -> MarketRegime:
    """Detect current market regime"""
    hurst = self.regime_detector.hurst_exponent(close)
    trend_strength = self.regime_detector.trend_strength(close)
    vol_regime = self.regime_detector.volatility_regime(close)

    sma_short = close.rolling(20).mean().iloc[-1]
    sma_long = close.rolling(50).mean().iloc[-1]
    trend_up = sma_short > sma_long

    if vol_regime == 'high':
        return MarketRegime.HIGH_VOLATILITY
    elif hurst > 0.55 and trend_strength > 0.7:
        return MarketRegime.TRENDING_UP if trend_up else MarketRegime.TRENDING_DOWN
    elif hurst < 0.45:
        return MarketRegime.MEAN_REVERTING
    else:
        return MarketRegime.SIDEWAYS
```

**Regime decision matrix**

| Condition                                      | Regime          | Strategy       |
|-----------------------------------------------:|----------------:|----------------|
| Volatility is HIGH                             | HIGH_VOLATILITY | Mean Reversion |
| Hurst > 0.55 AND Trend > 0.7 AND SMA20 > SMA50 | TRENDING_UP     | Momentum       |
| Hurst > 0.55 AND Trend > 0.7 AND SMA20 < SMA50 | TRENDING_DOWN   | Momentum       |
| Hurst < 0.45                                   | MEAN_REVERTING  | Mean Reversion |
| Everything else                                | SIDEWAYS        | Mean Reversion |

Key insight: the system adapts its strategy to the current market regime.

---

## Section 3A — Momentum strategy (trending markets)

**Trigger:** `TRENDING_UP` or `TRENDING_DOWN`  
**Code:** `app/core/signal_generator.py:271-346`

**Buy conditions (examples):**

| Condition              | Code reference                 | Why                              |
|-----------------------:|-------------------------------:|----------------------------------|
| MACD bullish crossover | `macd > macd_signal`           | Confirms momentum                |
| RSI momentum           | `45 < rsi < 75`                | Healthy momentum (not extreme)   |
| Moving avg bullish     | `price > MA20 && MA20 > MA50`  | Trend aligned                    |
| Strong trend (ADX)     | `ADX > 25 && DI+ > DI-`        | Directional confirmation         |
| Volume surge           | `volume > 1.5 * avg_volume`    | Conviction in move               |
| Momentum score         | `composite_momentum > 30`      | Composite indicator agree        |

**Signal generation logic:**

```py
if bullish_conditions >= 4:
    if bullish_conditions >= 5:
        return {'signal_type': SignalType.STRONG_BUY, 'reasons': [... ]}
    else:
        return {'signal_type': SignalType.BUY, 'reasons': [... ]}
```

---

## Section 3B — Mean reversion strategy (ranging/volatile markets)

**Trigger:** `MEAN_REVERTING`, `SIDEWAYS`, `HIGH_VOLATILITY`  
**Code:** `app/core/signal_generator.py:348-423`

**Buy conditions (examples):**

| Condition           | Code reference               | Why                          |
|--------------------:|-----------------------------:|-----------------------------|
| RSI oversold        | `rsi < 30`                   | Stock is beaten down        |
| BB lower band       | `bb_position < 0.1`          | Price near lower support    |
| Stochastic oversold | `stoch_k < 20`               | Confirms momentum reversal  |
| Williams %R         | `williams < -80`             | Alternative oversold metric |
| MR score            | `mean_reversion_score > 40`  | Composite says oversold     |

Signal returns `STRONG_BUY` for 4+ conditions, `BUY` for 3 conditions.

---

## SECTION 4: Confidence Score Calculation

**Code Location:** `app/core/signal_generator.py:425–471`

The confidence score determines whether a signal is strong enough to be included in the final list.  
The process starts with a base score and adds bonuses depending on indicator strength and alignment.

---

### Scoring System

```python
confidence = 0.5   # Base score (50%)
```

Then bonuses are added:

| Condition | Code Line | Bonus | Meaning |
|----------|-----------|--------|---------|
| Regime matches signal direction | 433–440 | **+0.2** | Biggest boost; signal agrees with market regime |
| Strong trend (ADX > 25) | 443 | +0.1 | Confirms momentum direction |
| Volume surge (> 1.5× average) | 447 | +0.1 | High conviction from traders |
| Momentum or MR score > 50 | 454 | +0.1 | Composite indicator agreement |
| Bollinger Band extreme (position < 0.1 or > 0.9) | 459 | +0.1 | Price at statistically extreme level |
| RSI extreme (< 25 or > 75) | 464 | +0.1 | Overbought/oversold strength |
| Strong signal type (STRONG_BUY / STRONG_SELL) | 468 | +0.1 | Reinforces confidence |

Final cap:

```python
confidence = min(confidence, 1.0)   # Max = 100%
```

---

### Real Scoring Examples

#### Example 1: STRONG_BUY in TRENDING_UP

- Base: `0.5`
- Regime alignment: `+0.2`
- Strong trend: `+0.1`
- Volume surge: `+0.1`
- Strong signal type: `+0.1`

**Final Score: 1.0** → ✅ PASSED

---

#### Example 2: BUY in SIDEWAYS Market

- Base: `0.5`
- BB extreme: `+0.1`
- Composite score > 50: `+0.1`

**Final Score: 0.7** → ✅ PASSED

---

#### Example 3: SELL in TRENDING_UP

- Base: `0.5`
- No regime alignment: `+0.0`
- BB extreme: `+0.1`

**Final Score: 0.6** → ⚠️ Barely passed (threshold = 0.6)

---

#### Example 4: Weak Signal

- Base: `0.5`
- No bonuses

**Final Score: 0.5** → ❌ Rejected

---

### Minimum Confidence Requirement

From lines 103–104:

```python
if confidence < self.min_confidence:   # self.min_confidence = 0.6
    return None   # Reject weak signals
```

Any signal with confidence < **0.6** is **not included** in the active signals list.

---

## SECTION 5: Position Sizing (Stop Loss & Target)

**Code Location:** `app/core/signal_generator.py:106–115`

Position sizing in this system is based on **ATR (Average True Range)**, which adjusts stop loss and target levels based on volatility.  
Higher volatility → wider stops.  
Lower volatility → tighter stops.

---

### Code Logic

```python
current_price = data['Close'].iloc[-1]
atr = indicators['atr']   # Average True Range (volatility measure)

# For BUY signals
if signal_data['signal_type'] in [SignalType.BUY, SignalType.STRONG_BUY]:
    stop_loss = current_price - (atr * self.volatility_factor)            # 2 × ATR
    target_price = current_price + (atr * self.volatility_factor * 2)     # 4 × ATR

# For SELL signals
else:
    stop_loss = current_price + (atr * self.volatility_factor)
    target_price = current_price - (atr * self.volatility_factor * 2)
```

---

### Why ATR-Based?

Using ATR is preferred because:

- **ATR scales with volatility** (more volatile = bigger ATR).
- **High-volatility stocks** get *wider* stop losses → prevents getting stopped out by noise.
- **Low-volatility stocks** get *tighter* stops → gives precision and better risk–reward.
- Keeps stop and target distances consistent across different stocks.

---

### Practical Example

**Ticker:** TSLA  
**Current Price:** \$250  
**ATR:** \$10  
**Volatility Factor:** `2.0`

#### BUY Signal:
- **Stop Loss:**  
  `250 - (10 × 2) = 230`
- **Target Price:**  
  `250 + (10 × 2 × 2) = 290`
- **Risk/Reward Ratio:**  
  `1 : 8`

This means risking \$20 for a potential \$40 gain.

---

## SECTION 6: Portfolio Collection & Sorting

**Code Location:** `app/core/signal_generator.py:134–155`

The system loops through every ticker in the portfolio, generates a signal for each, filters out invalid ones, and finally sorts them by confidence.

```python
def generate_portfolio_signals(self, portfolio_data: Dict[str, pd.DataFrame]) -> List[TradingSignal]:
    signals = []

    for ticker, data in portfolio_data.items():
        signal = self.generate_signal(ticker, data)  # Run through entire pipeline
        if signal:
            signals.append(signal)  # Only include tickers that passed ALL filters

    # Sort by confidence score (highest first)
    signals.sort(key=lambda x: x.confidence, reverse=True)

    return signals
```

**Key Point:**  
Only tickers where `generate_signal()` returns a **non-None** `TradingSignal` object appear in the final list.

---

## SECTION 7: API Response Format

**Code Location:** `app/api/routes.py:67–94`

When you call the endpoint:

```
/api/signals
```

You receive a JSON response structured like this:

```json
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
    }
  ],
  "last_update": "2025-01-15T10:30:00",
  "total_count": 5
}
```

---

## Why a Ticker **Does NOT** Appear

A ticker is excluded if:

| Reason | Lines | Example |
|--------|--------|---------|
| Insufficient data | 80–82 | Only 30 days of data available |
| No strategy triggers | 97–98 | Only 2 bullish conditions (need 4 for momentum) |
| Confidence too low | 103–104 | Score = 0.55 (min threshold = 0.60) |
| Wrong regime match | 434–440 | SELL signal during TRENDING_UP market |
| Weak indicators | All | No volume surge, RSI normal, MACD flat |

---

## Summary Decision Tree

```
┌─ Fetch data for all tickers
│
├─ For each ticker:
│   ├─ Data >= 50 periods? → NO → Skip
│   │
│   ├─ Detect regime (trending, ranging, volatile?)
│   │
│   ├─ Apply appropriate strategy
│   │     ├─ Momentum → Need 4+ conditions
│   │     └─ Mean Reversion → Need 3+ conditions
│   │     → If neither threshold met → Skip
│   │
│   ├─ Calculate confidence (0.5 base + bonuses)
│   │     └─ Confidence < 0.6? → Skip
│   │
│   └─ Create TradingSignal:
│         ├─ Signal Type (BUY / SELL / STRONG_BUY / STRONG_SELL)
│         ├─ Confidence (0.6–1.0)
│         ├─ Entry, Stop Loss, Target
│         └─ Reasons list
│
└─ Sort all signals by confidence (DESC)
    └─ Return to API
```

---

## Real-World Example: Complete Ticker Journey  
**Scenario:** MSFT on 2025-01-15

### **STEP 1: Data Check**
- 252 trading days → ✅ Pass

### **STEP 2: Market Regime**
- Hurst: 0.62 (trending)  
- Trend Strength: 0.78 (strong)  
- Volatility: Normal  
- SMA20 = 420 > SMA50 = 410 → Uptrend  
- **Regime = TRENDING_UP**

### **STEP 3: Select Strategy**
- → **MOMENTUM strategy**

### **STEP 4: Count Conditions**

| Condition | Value | Pass? |
|----------|--------|--------|
| MACD > Signal | 5.2 > 3.1 | ✅ |
| RSI | 62 (between 45–75) | ✅ |
| Price > MA20 > MA50 | 425 > 420 > 410 | ✅ |
| ADX > 25 | 28 | ✅ |
| Volume > 1.5× average | 65M / 42M = 1.55× | ✅ |
| Momentum Score > 30 | 45 | ✅ |

→ **6 CONDITIONS MET → STRONG_BUY**

### **STEP 5: Confidence Calculation**
- Base: 0.50  
- +0.20 regime alignment  
- +0.10 strong trend  
- +0.10 volume surge  
- +0.10 momentum score  
- +0.10 strong signal type  
- **Final Score: 1.0**

### **STEP 6: Position Sizing**
- Price: 425  
- ATR: 8.5  

```
Stop Loss = 425 - (8.5 × 2) = 408
Target     = 425 + (8.5 × 2 × 2) = 459
```

### **STEP 7: Create Signal Object**
MSFT is included with:

- **Signal Type:** STRONG_BUY  
- **Confidence:** 1.0  
- **Entry:** 425  
- **Stop:** 408  
- **Target:** 459  
- **Reasons:** 6 conditions met

### **FINAL**
Sorted with all other signals by confidence → If this is highest confidence, appears first in `/api/signals`.

---

This is the complete system. A ticker shows up when it passes all these filters, starting with data availability, through the appropriate strategy, and finally confidence threshold. The system is regime-aware and adaptive, not rigid.


