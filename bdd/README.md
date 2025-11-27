# BDD Tests - Behavior-Driven Development

This directory contains Behavior-Driven Development (BDD) tests using Behave framework. BDD tests focus on user-oriented functionality and experience from a business perspective.

## Directory Structure

```
bdd/
├── features/          # Gherkin feature files (.feature)
│   ├── portfolio.feature
│   ├── signals.feature
│   └── api.feature
├── steps/             # Step implementations (Python)
│   ├── __init__.py
│   ├── portfolio_steps.py
│   ├── signal_steps.py
│   └── api_steps.py
├── environment.py     # Setup/teardown and fixtures
└── README.md          # This file
```

## Features

### Portfolio Management (portfolio.feature)
- User can view portfolio
- User can add positions
- User can update positions

### Trading Signals (signals.feature)
- System generates trading signals
- Signals have required fields
- Signals are based on technical analysis

### API Endpoints (api.feature)
- REST API is accessible
- API authentication works
- API returns correct responses

## Running BDD Tests

### Run all BDD tests
```bash
cd bdd
behave
```

### Run specific feature
```bash
behave features/portfolio.feature
```

### Run with verbose output
```bash
behave -v
```

### Run with detailed output
```bash
behave --no-capture
```

### Run with specific tags
```bash
behave --tags=@portfolio
```

## Writing BDD Tests

### Feature File Format (Gherkin)
```gherkin
Feature: Portfolio Management
  As a trader
  I want to manage my portfolio
  So that I can track my investments

  Scenario: User views empty portfolio
    Given the system is initialized
    When user requests portfolio data
    Then portfolio should be empty
```

### Step Definition Format (Python)
```python
from behave import given, when, then

@given('the system is initialized')
def step_system_initialized(context):
    """Initialize the trading system."""
    context.system = TradingSystem()

@when('user requests portfolio data')
def step_request_portfolio(context):
    """Fetch portfolio data."""
    context.portfolio = context.system.get_portfolio()

@then('portfolio should be empty')
def step_portfolio_empty(context):
    """Verify portfolio is empty."""
    assert len(context.portfolio) == 0
```

## Best Practices

1. **Write from user perspective** - Features should describe what users do/want, not technical details
2. **Use descriptive scenarios** - Each scenario should test one user action
3. **Reuse steps** - Write flexible step definitions for reuse
4. **Keep scenarios simple** - Long scenarios are hard to debug
5. **Use background** - For common setup across scenarios:

```gherkin
Feature: Trading Signals

  Background:
    Given the system is initialized
    And portfolio tickers are loaded

  Scenario: Generate buy signal
    ...
```

## Integration with CI/CD

BDD tests are automatically run as part of the code quality workflow:

```bash
# This is run in GitHub Actions
behave bdd/
```

## Debugging

### Run specific scenario by line number
```bash
behave features/portfolio.feature:5
```

### Enable Python debugger
```python
import pdb; pdb.set_trace()  # In step implementation
```

### View scenario with debugging
```bash
behave -f steps features/portfolio.feature
```

## Dependencies

Behave requires:
- `behave>=1.2.6` - BDD framework
- `parse>=1.19.0` - Parsing step definitions

Install with:
```bash
pip install -r ../requirements-dev.txt
```

## Resources

- [Behave Documentation](https://behave.readthedocs.io/)
- [Gherkin Syntax Guide](https://cucumber.io/docs/gherkin/)
- [BDD Best Practices](https://cucumber.io/docs/bdd/)
