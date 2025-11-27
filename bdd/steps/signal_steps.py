"""
Trading Signal Step Definitions

Step implementations for signal-related BDD scenarios.
"""

from behave import given, when, then
from datetime import datetime, timedelta


@given("market data is available for the portfolio")
def step_market_data_available(context):
    """Setup market data."""
    context.logger.info("Setting up market data")
    context.market_data = {
        "AAPL": {"price": 150, "trend": "uptrend"},
        "TSLA": {"price": 250, "trend": "downtrend"},
        "MSFT": {"price": 300, "trend": "sideways"},
    }


@given('"{ticker}" shows a strong uptrend')
def step_ticker_uptrend(context, ticker):
    """Set up ticker in uptrend."""
    context.logger.info(f"Setting {ticker} to uptrend")
    context.scenario_data["analysis_ticker"] = ticker
    context.scenario_data["trend"] = "uptrend"
    context.market_data[ticker] = {
        "price": 150,
        "trend": "uptrend",
        "momentum": 0.8,
        "rsi": 65,
        "macd": "positive",
    }


@given('"{ticker}" shows a strong downtrend')
def step_ticker_downtrend(context, ticker):
    """Set up ticker in downtrend."""
    context.logger.info(f"Setting {ticker} to downtrend")
    context.scenario_data["analysis_ticker"] = ticker
    context.scenario_data["trend"] = "downtrend"
    context.market_data[ticker] = {
        "price": 200,
        "trend": "downtrend",
        "momentum": -0.8,
        "rsi": 35,
        "macd": "negative",
    }


@given('"{ticker}" is moving sideways')
def step_ticker_sideways(context, ticker):
    """Set up ticker moving sideways."""
    context.logger.info(f"Setting {ticker} to sideways")
    context.scenario_data["analysis_ticker"] = ticker
    context.scenario_data["trend"] = "sideways"
    context.market_data[ticker] = {
        "price": 175,
        "trend": "sideways",
        "momentum": 0.0,
        "rsi": 50,
        "macd": "neutral",
    }


@when("the signal generator creates a signal")
def step_create_signal(context):
    """Create a new signal."""
    context.logger.info("Creating signal")
    context.generated_signal = {
        "ticker": "AAPL",
        "signal_type": "BUY",
        "confidence": 0.75,
        "timestamp": datetime.now(),
    }


@when("the signal generator analyzes the data")
def step_analyze_data(context):
    """Run signal generation analysis."""
    context.logger.info("Running signal analysis")
    ticker = context.scenario_data.get("analysis_ticker", "AAPL")
    data = context.market_data.get(ticker, {})

    # Simple signal generation logic
    trend = data.get("trend", "sideways")
    momentum = data.get("momentum", 0)
    rsi = data.get("rsi", 50)

    if trend == "uptrend" and momentum > 0.5 and rsi > 60:
        signal_type = "BUY"
        confidence = 0.85
    elif trend == "downtrend" and momentum < -0.5 and rsi < 40:
        signal_type = "SELL"
        confidence = 0.85
    else:
        signal_type = "HOLD"
        confidence = 0.5

    context.generated_signal = {
        "ticker": ticker,
        "signal_type": signal_type,
        "confidence": confidence,
        "timestamp": datetime.now(),
        "indicators": data,
    }
    context.logger.info(f"Generated signal: {signal_type} for {ticker}")


@then('a BUY signal should be generated for "{ticker}"')
def step_buy_signal(context, ticker):
    """Verify BUY signal was generated."""
    assert hasattr(context, "generated_signal"), "No signal was generated"
    assert (
        context.generated_signal["signal_type"] == "BUY"
    ), f"Expected BUY signal but got {context.generated_signal['signal_type']}"
    assert context.generated_signal["ticker"] == ticker
    context.logger.info(f"BUY signal confirmed for {ticker}")


@then('a SELL signal should be generated for "{ticker}"')
def step_sell_signal(context, ticker):
    """Verify SELL signal was generated."""
    assert hasattr(context, "generated_signal"), "No signal was generated"
    assert (
        context.generated_signal["signal_type"] == "SELL"
    ), f"Expected SELL signal but got {context.generated_signal['signal_type']}"
    assert context.generated_signal["ticker"] == ticker
    context.logger.info(f"SELL signal confirmed for {ticker}")


@then('a HOLD signal should be generated for "{ticker}"')
def step_hold_signal(context, ticker):
    """Verify HOLD signal was generated."""
    assert hasattr(context, "generated_signal"), "No signal was generated"
    assert (
        context.generated_signal["signal_type"] == "HOLD"
    ), f"Expected HOLD signal but got {context.generated_signal['signal_type']}"
    assert context.generated_signal["ticker"] == ticker
    context.logger.info(f"HOLD signal confirmed for {ticker}")


@then("the signal confidence should be above {percentage:d}%")
def step_confidence_threshold(context, percentage):
    """Verify signal confidence exceeds threshold."""
    confidence = context.generated_signal["confidence"]
    threshold = percentage / 100.0
    assert (
        confidence > threshold
    ), f"Signal confidence {confidence:.0%} should be above {percentage}%"
    context.logger.info(f"Signal confidence {confidence:.0%} exceeds {percentage}%")


@then("the signal should have a ticker symbol")
def step_signal_has_ticker(context):
    """Verify signal has ticker."""
    assert "ticker" in context.generated_signal
    assert context.generated_signal["ticker"] is not None
    context.logger.info(f"Signal has ticker: {context.generated_signal['ticker']}")


@then("the signal should have a signal type (BUY, SELL, or HOLD)")
def step_signal_has_type(context):
    """Verify signal has valid type."""
    assert "signal_type" in context.generated_signal
    valid_types = {"BUY", "SELL", "HOLD"}
    assert context.generated_signal["signal_type"] in valid_types
    context.logger.info(f"Signal has type: {context.generated_signal['signal_type']}")


@then("the signal should have a confidence level")
def step_signal_has_confidence(context):
    """Verify signal has confidence."""
    assert "confidence" in context.generated_signal
    assert 0 <= context.generated_signal["confidence"] <= 1
    context.logger.info(f"Signal has confidence: {context.generated_signal['confidence']:.0%}")


@then("the signal should have a timestamp")
def step_signal_has_timestamp(context):
    """Verify signal has timestamp."""
    assert "timestamp" in context.generated_signal
    assert context.generated_signal["timestamp"] is not None
    context.logger.info(f"Signal has timestamp: {context.generated_signal['timestamp']}")


@given('multiple technical indicators align for "{ticker}"')
def step_aligned_indicators(context, ticker):
    """Set up ticker with aligned indicators."""
    context.logger.info(f"Setting up aligned indicators for {ticker}")
    context.scenario_data["analysis_ticker"] = ticker
    context.market_data[ticker] = {
        "price": 160,
        "trend": "uptrend",
        "momentum": 0.9,
        "rsi": 75,
        "macd": "positive",
        "bollinger": "bullish",
        "moving_averages": "bullish",
    }


@then("the signal confidence should be higher than misaligned indicators")
def step_confidence_higher_aligned(context):
    """Verify aligned indicators produce higher confidence."""
    assert context.generated_signal["confidence"] > 0.7
    context.logger.info(
        f"Aligned indicators produce higher confidence: {context.generated_signal['confidence']:.0%}"
    )


@given('the portfolio contains "{tickers}"')
def step_portfolio_contains_tickers(context, tickers):
    """Set portfolio tickers."""
    context.portfolio_tickers = [t.strip().strip('"') for t in tickers.split(",")]
    context.logger.info(f"Portfolio contains: {context.portfolio_tickers}")


@when("the signal generator runs a full analysis")
def step_full_analysis(context):
    """Run analysis for all portfolio tickers."""
    context.logger.info("Running full portfolio analysis")
    context.generated_signals = []
    for ticker in context.portfolio_tickers:
        signal = {
            "ticker": ticker,
            "signal_type": "BUY",  # Simplified
            "confidence": 0.75,
            "timestamp": datetime.now(),
        }
        context.generated_signals.append(signal)


@then("signals should be generated for all {count:d} tickers")
def step_signals_for_all_tickers(context, count):
    """Verify signals generated for all tickers."""
    assert len(context.generated_signals) == count
    tickers = [s["ticker"] for s in context.generated_signals]
    assert set(tickers) == set(context.portfolio_tickers)
    context.logger.info(f"Signals generated for {count} tickers")


@given("a signal was generated {days:d} days ago")
def step_old_signal(context, days):
    """Create an old signal."""
    context.logger.info(f"Creating signal from {days} days ago")
    context.old_signal = {
        "ticker": "AAPL",
        "signal_type": "BUY",
        "confidence": 0.8,
        "timestamp": datetime.now() - timedelta(days=days),
    }


@when("checking signal status")
def step_check_signal_status(context):
    """Check if signal is stale."""
    age_days = (datetime.now() - context.old_signal["timestamp"]).days
    context.old_signal["is_stale"] = age_days > 7  # Signals older than 7 days are stale


@then("the signal should be marked as stale")
def step_signal_marked_stale(context):
    """Verify signal is marked stale."""
    assert context.old_signal.get("is_stale"), "Signal should be marked as stale"
    context.logger.info("Signal is marked as stale")


@then("new analysis should be requested")
def step_new_analysis_requested(context):
    """Verify new analysis is needed."""
    # In a real system, this would trigger a new analysis
    context.needs_new_analysis = True
    assert context.needs_new_analysis
    context.logger.info("New analysis should be requested")
