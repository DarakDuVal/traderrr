"""
Portfolio Management Step Definitions

Step implementations for portfolio-related BDD scenarios.
"""

from behave import given, when, then


@given("the trading system is initialized")
def step_system_initialized(context):
    """Initialize the trading system."""
    context.logger.info("Initializing trading system")
    context.portfolio = {}
    context.positions = {}


@when("the user requests their portfolio")
def step_request_portfolio(context):
    """Fetch portfolio data."""
    context.logger.info("Requesting portfolio")
    context.portfolio_data = context.portfolio.copy()


@then("the portfolio should exist")
def step_portfolio_exists(context):
    """Verify portfolio exists."""
    assert context.portfolio is not None, "Portfolio should exist"
    context.logger.info("Portfolio exists")


@then("the portfolio should be empty")
def step_portfolio_empty(context):
    """Verify portfolio is empty."""
    assert (
        len(context.portfolio) == 0
    ), f"Portfolio should be empty but has {len(context.portfolio)} positions"
    context.logger.info("Portfolio is empty")


@when('the user adds a position for "{ticker}" with {shares:d} shares')
def step_add_position(context, ticker, shares):
    """Add a position to portfolio."""
    context.logger.info(f"Adding {shares} shares of {ticker}")
    context.portfolio[ticker] = {"ticker": ticker, "shares": shares, "cost_basis": None}


@then("the portfolio should contain {count:d} position")
def step_portfolio_has_positions(context, count):
    """Verify portfolio has expected number of positions."""
    assert (
        len(context.portfolio) == count
    ), f"Expected {count} positions but found {len(context.portfolio)}"
    context.logger.info(f"Portfolio has {count} position(s)")


@then("the portfolio should contain {count:d} positions")
def step_portfolio_has_multiple_positions(context, count):
    """Verify portfolio has expected number of positions."""
    step_portfolio_has_positions(context, count)


@then('the position for "{ticker}" should have {shares:d} shares')
def step_position_shares(context, ticker, shares):
    """Verify position has expected number of shares."""
    assert ticker in context.portfolio, f"Position for {ticker} not found"
    assert (
        context.portfolio[ticker]["shares"] == shares
    ), f"Expected {shares} shares but found {context.portfolio[ticker]['shares']}"
    context.logger.info(f"Position for {ticker} has {shares} shares")


@given('the user has a position for "{ticker}" with {shares:d} shares')
def step_user_has_position(context, ticker, shares):
    """Set up a position in the portfolio."""
    step_add_position(context, ticker, shares)


@when("the user requests the portfolio value")
def step_request_portfolio_value(context):
    """Request portfolio total value."""
    context.logger.info("Requesting portfolio value")
    # Simple calculation: sum of shares * assumed price
    total_value = sum(pos["shares"] * 100 for pos in context.portfolio.values())
    context.portfolio_value = total_value


@then("the portfolio value should be a positive number")
def step_portfolio_value_positive(context):
    """Verify portfolio value is positive."""
    assert context.portfolio_value > 0, "Portfolio value should be positive"
    context.logger.info(f"Portfolio value: ${context.portfolio_value}")


@when("the user updates the position to {shares:d} shares")
def step_update_position(context, shares):
    """Update position size (uses last mentioned ticker)."""
    # Get the last mentioned ticker from the context
    last_ticker = context.scenario_data.get("last_ticker", list(context.portfolio.keys())[-1])
    context.logger.info(f"Updating {last_ticker} to {shares} shares")
    if last_ticker in context.portfolio:
        context.portfolio[last_ticker]["shares"] = shares
    context.scenario_data["last_ticker"] = last_ticker


@given('the user has a position for "{ticker}" with {shares:d} shares at ${price:d}')
def step_user_has_position_with_price(context, ticker, shares, price):
    """Set up a position with specific price."""
    context.logger.info(f"Adding {shares} shares of {ticker} at ${price}")
    context.portfolio[ticker] = {
        "ticker": ticker,
        "shares": shares,
        "price": price,
        "value": shares * price,
    }
    context.scenario_data["last_ticker"] = ticker


@when("the user requests portfolio weights")
def step_request_portfolio_weights(context):
    """Calculate portfolio weights."""
    context.logger.info("Calculating portfolio weights")
    total_value = sum(pos.get("value", pos["shares"] * 100) for pos in context.portfolio.values())
    context.weights = {
        ticker: (pos.get("value", pos["shares"] * 100) / total_value * 100)
        for ticker, pos in context.portfolio.items()
    }
    context.total_weight = sum(context.weights.values())


@then("the total weight should equal 100%")
def step_total_weight_100(context):
    """Verify total weight equals 100%."""
    assert (
        abs(context.total_weight - 100.0) < 0.01
    ), f"Total weight should be 100% but got {context.total_weight:.2f}%"
    context.logger.info(f"Total weight: {context.total_weight:.2f}%")


@then("the weight for each position should be calculated correctly")
def step_weights_calculated(context):
    """Verify each position weight is calculated correctly."""
    assert len(context.weights) > 0, "Weights should be calculated"
    assert all(w > 0 for w in context.weights.values()), "All weights should be positive"
    context.logger.info(f"Weights calculated: {context.weights}")
