Feature: Portfolio Management
  As a trader
  I want to manage my investment portfolio
  So that I can track and optimize my positions

  Background:
    Given the trading system is initialized

  @portfolio
  Scenario: User views empty portfolio on first use
    When the user requests their portfolio
    Then the portfolio should exist
    And the portfolio should be empty

  @portfolio
  Scenario: User can add a stock position
    When the user adds a position for "AAPL" with 10 shares
    Then the portfolio should contain 1 position
    And the position for "AAPL" should have 10 shares

  @portfolio
  Scenario: User can view portfolio value
    Given the user has a position for "AAPL" with 10 shares
    When the user requests the portfolio value
    Then the portfolio value should be a positive number

  @portfolio
  Scenario: User can update position size
    Given the user has a position for "AAPL" with 10 shares
    When the user updates the position to 20 shares
    Then the position for "AAPL" should have 20 shares

  @portfolio
  Scenario: Portfolio tracks multiple positions
    Given the user has a position for "AAPL" with 10 shares
    And the user has a position for "MSFT" with 5 shares
    And the user has a position for "GOOGL" with 2 shares
    When the user requests their portfolio
    Then the portfolio should contain 3 positions

  @portfolio
  Scenario: Portfolio weight calculation
    Given the user has a position for "AAPL" with 100 shares at $150
    And the user has a position for "MSFT" with 100 shares at $300
    When the user requests portfolio weights
    Then the total weight should equal 100%
    And the weight for each position should be calculated correctly
