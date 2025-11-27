Feature: Trading Signal Generation
  As a trader
  I want to receive accurate trading signals
  So that I can make informed investment decisions

  Background:
    Given the trading system is initialized
    And market data is available for the portfolio

  @signals
  Scenario: System generates buy signal for uptrend
    Given "AAPL" shows a strong uptrend
    When the signal generator analyzes the data
    Then a BUY signal should be generated for "AAPL"
    And the signal confidence should be above 70%

  @signals
  Scenario: System generates sell signal for downtrend
    Given "TSLA" shows a strong downtrend
    When the signal generator analyzes the data
    Then a SELL signal should be generated for "TSLA"
    And the signal confidence should be above 70%

  @signals
  Scenario: System generates hold signal for sideways movement
    Given "MSFT" is moving sideways
    When the signal generator analyzes the data
    Then a HOLD signal should be generated for "MSFT"

  @signals
  Scenario: Signal has all required fields
    When the signal generator creates a signal
    Then the signal should have a ticker symbol
    And the signal should have a signal type (BUY, SELL, or HOLD)
    And the signal should have a confidence level
    And the signal should have a timestamp

  @signals
  Scenario: Signal confidence correlates with indicators
    Given multiple technical indicators align for "AAPL"
    When the signal generator analyzes the data
    Then the signal confidence should be higher than misaligned indicators

  @signals
  Scenario: Signals are generated for multiple tickers
    Given the portfolio contains "AAPL", "MSFT", and "GOOGL"
    When the signal generator runs a full analysis
    Then signals should be generated for all 3 tickers

  @signals
  Scenario: Old signals are marked as stale
    Given a signal was generated 30 days ago
    When checking signal status
    Then the signal should be marked as stale
    And new analysis should be requested
