# Trading Signals System

A comprehensive algorithmic trading system built with Yahoo Finance data, advanced technical indicators, and regime-adaptive signal generation. Features real-time data management, intelligent portfolio analysis, and production-ready deployment on IBM Cloud.

## Current Status

✅ **Production Ready** | ✅ **67/67 Tests Passing** | ✅ **Fully Documented**

- **Latest Version**: All core issues resolved and tested
- **Test Coverage**: Comprehensive unit tests for data management, indicators, signals, and portfolio analysis
- **Code Quality**: Proper error handling, logging, and graceful fallbacks throughout
- **Database**: Secure SQLite with composite key constraints, proper schema, and migration support
- **API**: 7 RESTful endpoints with full documentation and error handling

## Features

### Core Functionality

- **Real-time Data**: Yahoo Finance integration with caching and error handling
- **Advanced Indicators**: 15+ technical indicators with regime detection
- **Smart Signals**: Context-aware buy/sell signals with confidence scoring
- **Portfolio Analytics**: Risk metrics, correlation analysis, and optimization
- **Web Dashboard**: Real-time monitoring with interactive charts
- **RESTful API**: Complete API for integration and automation

### Technical Highlights

- **Regime-Adaptive Strategies**: Automatically detects market conditions (trending, mean-reverting, volatile) and applies appropriate strategies
- **Dual-Signal Generation**: Momentum strategy for trending markets + Mean reversion strategy for ranging markets
- **Risk Management**: ATR-based position sizing, Value-at-Risk (VaR), correlation analysis, and stress testing
- **Confidence Scoring**: Multi-factor confidence calculation (0.0-1.0) with regime alignment bonuses
- **Performance**: Vectorized pandas operations, efficient SQLite caching, and concurrent data downloads
- **Production Ready**: Comprehensive logging, error recovery, graceful fallbacks, and monitoring
- **Fully Tested**: 67 unit tests covering data management, indicators, signals, and portfolio analysis

## 📋 Prerequisites

- Python 3.8 or higher
- 4GB+ RAM (8GB recommended for full portfolio)
- 10GB+ disk space for historical data
- IBM Cloud account (for cloud deployment)

## Installation

### Quick Setup

```bash
# Navigate to project directory
cd traderrr

# Create virtual environment
python -m venv trading_env
source trading_env/bin/activate  # On Windows: trading_env\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Create environment file (.env)
# The system automatically loads from .env on startup
cat > .env << EOF
FLASK_ENV=development
DATABASE_PATH=data/market_data.db
MIN_CONFIDENCE=0.6
UPDATE_INTERVAL_MINUTES=30
BACKUP_ENABLED=true
SECRET_KEY=dev-secret-key-change-in-production
API_HOST=127.0.0.1
API_PORT=5000
EOF
```

**Important**: The `.env` file MUST be created before running `python main.py`. The application requires these environment variables for proper initialization.

```bash
# Run setup script
python setup.py

# OR manual setup:
mkdir -p data logs backups cache
python -c "from config.database import DatabaseConfig; DatabaseConfig('data/market_data.db').init_database()"
```

```bash
# Generate sample data for testing (optional)
python utils/dev_tools.py --populate
```

```bash
# Run all tests
python -m pytest tests/ -v

# Run specific test categories
python -m pytest tests/test_data_manager.py -v
python -m pytest tests/test_indicators.py -v
python -m pytest tests/test_signals.py -v
python -m pytest tests/test_portfolio.py -v

# Run tests with coverage
pip install pytest-cov
python -m pytest tests/ --cov=app --cov-report=html
```

```bash
# Start the Flask application
python main.py

# Application will be available at:
# Web Dashboard: http://localhost:5000
# API Health: http://localhost:5000/api/health
# API Signals: http://localhost:5000/api/signals
```

```bash
# Test health endpoint
curl http://localhost:5000/api/health

# Test signals endpoint
curl http://localhost:5000/api/signals

# Test portfolio endpoint
curl http://localhost:5000/api/portfolio

# Trigger manual update
curl -X POST http://localhost:5000/api/update
```

```bash
# Quick backtest
python scripts/backtest.py --tickers AAPL MSFT --capital 10000

# Detailed backtest with output
python scripts/backtest.py \
  --tickers AAPL MSFT GOOGL VTI \
  --start-date 2023-01-01 \
  --end-date 2024-01-01 \
  --capital 50000 \
  --frequency weekly \
  --output backtest_results.json
```

### Docker build

```bash
docker build -t traderrr .
docker run -p 8080:8080 traderrr

# Install IBM Cloud CLI and login
ibmcloud login
ibmcloud plugin install code-engine

python scripts/deploy.py \
  --registry-namespace your-namespace \
  --project-name trading-signals \
  --cpu 1 \
  --memory 2G
```

## Configuration

The system uses environment variables and `config/settings.py` for configuration. Key settings:

### Environment Variables (.env file)

```bash
FLASK_ENV=development              # development or production
DATABASE_PATH=data/market_data.db  # SQLite database location
MIN_CONFIDENCE=0.6                 # Minimum signal confidence (0.0-1.0)
UPDATE_INTERVAL_MINUTES=30         # How often to refresh signals
BACKUP_ENABLED=true                # Enable automatic backups
SECRET_KEY=your-secret-key         # Flask secret key
API_HOST=127.0.0.1                 # API server host
API_PORT=5000                       # API server port
```

### Config Settings (config/settings.py)

Edit `config/settings.py` to customize portfolio and strategy parameters:

```python
@classmethod
def PORTFOLIO_TICKERS(cls):
    """List of tickers to monitor"""
    return ['AAPL', 'MSFT', 'GOOGL', 'JPM', 'VTI', 'NVDA', 'TSM']

@classmethod
def PORTFOLIO_WEIGHTS(cls):
    """Portfolio allocation weights (must sum to 1.0)"""
    return {
        'AAPL': 0.25,
        'MSFT': 0.20,
        'GOOGL': 0.20,
        'JPM': 0.15,
        'VTI': 0.20
    }

@classmethod
def PORTFOLIO_VALUE(cls):
    """Total portfolio value in USD"""
    return 100000

@classmethod
def MIN_CONFIDENCE(cls):
    """Minimum confidence threshold for signals (0.0-1.0)"""
    return 0.6

@classmethod
def UPDATE_INTERVAL(cls):
    """Update interval in minutes"""
    return 30
```

### Signal Generation Parameters

The system automatically adjusts to market conditions:
- **Momentum Strategy**: For trending markets - requires 4+ indicators aligned
- **Mean Reversion Strategy**: For ranging markets - requires 3+ indicators aligned
- **Confidence Multipliers**: Regime alignment, volume confirmation, extreme indicators

## 🎯 Usage Examples

### Basic Signal Generation

```python
from app.core.data_manager import DataManager
from app.core.signal_generator import SignalGenerator
from config.settings import Config

# Initialize components
dm = DataManager(db_path=Config.DATABASE_PATH())
signal_gen = SignalGenerator(min_confidence=Config.MIN_CONFIDENCE())

# Get data and generate signals
data = dm.get_stock_data('AAPL', period='6mo')
signal = signal_gen.generate_signal('AAPL', data)

if signal:
    print(f"Signal: {signal.signal_type.value}")
    print(f"Confidence: {signal.confidence:.2%}")
    print(f"Entry: ${signal.entry_price:.2f}")
    print(f"Target: ${signal.target_price:.2f}")
    print(f"Stop Loss: ${signal.stop_loss:.2f}")
    print(f"Regime: {signal.regime.value}")
    print(f"Reasons: {signal.reasons}")

dm.close()
```

### Portfolio Signal Generation

```python
from app.core.data_manager import DataManager
from app.core.signal_generator import SignalGenerator
from config.settings import Config

# Initialize
dm = DataManager(db_path=Config.DATABASE_PATH())
signal_gen = SignalGenerator(min_confidence=Config.MIN_CONFIDENCE())

# Get portfolio data
portfolio_data = dm.get_multiple_stocks(Config.PORTFOLIO_TICKERS(), period='6mo')

# Generate signals for all tickers
signals = signal_gen.generate_portfolio_signals(portfolio_data)

# Sorted by confidence (highest first)
for signal in signals:
    print(f"{signal.ticker}: {signal.signal_type.value} ({signal.confidence:.1%} confidence)")
    print(f"  Entry: ${signal.entry_price:.2f} | Target: ${signal.target_price:.2f}")

dm.close()
```

### Portfolio Analysis

```python
from app.core.data_manager import DataManager
from app.core.portfolio_analyzer import PortfolioAnalyzer
from config.settings import Config

dm = DataManager(db_path=Config.DATABASE_PATH())
analyzer = PortfolioAnalyzer()

# Download portfolio data
portfolio_data = dm.get_multiple_stocks(Config.PORTFOLIO_TICKERS(), period='1y')
weights = Config.PORTFOLIO_WEIGHTS()

# Calculate metrics
metrics = analyzer.analyze_portfolio(portfolio_data, weights)
print(f"Portfolio Volatility: {metrics.volatility:.2%}")
print(f"Sharpe Ratio: {metrics.sharpe_ratio:.2f}")
print(f"Max Drawdown: {metrics.max_drawdown:.2%}")
print(f"Value at Risk: {metrics.value_at_risk:.2%}")

# Risk analysis
position_risks = analyzer.calculate_position_risks(
    portfolio_data,
    weights,
    Config.PORTFOLIO_VALUE()
)
for risk in position_risks:
    print(f"{risk.ticker}: Risk contribution {risk.contribution_to_risk:.4f}")

dm.close()
```

### Technical Indicators & Market Regime

```python
from app.core.data_manager import DataManager
from app.core.indicators import TechnicalIndicators, MarketRegimeDetector
from config.settings import Config

dm = DataManager(db_path=Config.DATABASE_PATH())
ti = TechnicalIndicators()
detector = MarketRegimeDetector()

# Get data
data = dm.get_stock_data('AAPL', period='3mo')
prices = data['Close']

# Calculate indicators
rsi = ti.rsi(prices).iloc[-1]
macd_line, signal_line, _ = ti.macd(prices)
bb_upper, bb_middle, bb_lower = ti.bollinger_bands(prices)

# Detect market regime
hurst = detector.hurst_exponent(prices)
trend_strength = detector.trend_strength(prices)
vol_regime = detector.volatility_regime(prices)

print(f"RSI: {rsi:.1f}")
print(f"MACD: {'Bullish' if macd_line.iloc[-1] > signal_line.iloc[-1] else 'Bearish'}")
print(f"Hurst Exponent: {hurst:.3f} ({'Trending' if hurst > 0.5 else 'Mean Reverting'})")
print(f"Trend Strength: {trend_strength:.3f}")
print(f"Volatility Regime: {vol_regime}")

dm.close()
```

## 🌐 Web Dashboard

Access the web interface at `http://localhost:5000`

### Features:

- **Real-time Signals**: Current buy/sell recommendations with confidence scores
- **Portfolio Overview**: Holdings, performance metrics, and sector allocation
- **Risk Monitoring**: VaR, correlation analysis, and stress test results
- **System Health**: Database status, update times, and performance metrics

### API Endpoints:

- `GET /api/signals` - Current trading signals
- `GET /api/portfolio` - Portfolio overview
- `POST /api/update` - Trigger signal update
- `GET /api/health` - System health check

## ☁️ IBM Cloud Deployment

### Prerequisites

```bash
# Install IBM Cloud CLI
curl -fsSL https://clis.cloud.ibm.com/install/linux | sh

# Install Code Engine plugin
ibmcloud plugin install code-engine

# Login to IBM Cloud
ibmcloud login
```

### Automated Deployment

```bash
# Deploy to IBM Cloud Code Engine
python deployment_utilities.py deploy --cpu 1 --memory 2G

# Or use Docker deployment
docker build -t traderrr .
docker tag traderrr icr.io/your-namespace/traderrr
docker push icr.io/your-namespace/traderrr
```

### Manual Deployment Steps

1. **Create Code Engine Project**

```bash
ibmcloud ce project create --name trading-signals
ibmcloud ce project select --name trading-signals
```

2. **Create Services**

```bash
# Cloudant database
ibmcloud resource service-instance-create trading-cloudant-db cloudantnosqldb lite us-south

# Object storage  
ibmcloud resource service-instance-create trading-object-storage cloud-object-storage lite global
```

3. **Deploy Application**

```bash
ibmcloud ce application create \
    --name traderrr \
    --build-source . \
    --build-strategy dockerfile \
    --cpu 1 \
    --memory 2G \
    --min-scale 1 \
    --max-scale 3 \
    --port 8080
```

4. **Bind Services**

```bash
ibmcloud ce application bind --name traderrr --service-instance trading-cloudant-db
ibmcloud ce application bind --name traderrr --service-instance trading-object-storage
```

### Environment Variables

Set these in IBM Cloud Console or via CLI:

```bash
ibmcloud ce application update traderrr \
    --env DATABASE_PATH=/app/data/market_data.db \
    --env MIN_CONFIDENCE=0.6 \
    --env UPDATE_INTERVAL_MINUTES=30 \
    --env BACKUP_ENABLED=true
```

## 🔧 System Management

### Database Operations

```bash
# Backup database
python deployment_utilities.py database backup --file backup_20250120.db

# Restore from backup
python deployment_utilities.py database restore --file backup_20250120.db

# Get database statistics
python deployment_utilities.py database stats

# Clean old data
python deployment_utilities.py database cleanup

# Export data
python deployment_utilities.py database export --file portfolio_data.csv
```

### Monitoring

```bash
# Check system health
python deployment_utilities.py monitor

# Run maintenance tasks
python deployment_utilities.py maintenance
```

### Scheduled Tasks

The system automatically runs:

- **Signal updates**: Every 30 minutes during market hours
- **Data cleanup**: Daily at midnight
- **Database backup**: Daily at 2 AM
- **Health checks**: Every 5 minutes

## 📊 Performance Optimization

### Data Caching

- Database caching for frequently accessed data
- 30-minute cache for intraday data
- 6-hour cache for daily data
- Automatic cache invalidation

### Computation Optimization

- Vectorized pandas operations
- Efficient indicator calculations
- Parallel data downloads
- SQLite database optimization

### Memory Management

- Configurable data retention periods
- Automatic cleanup of old records
- Connection pooling
- Memory usage monitoring

## 🧪 Testing

### Run Test Suite

```bash
# Full test suite (all 67 tests)
python -m pytest tests/ -v

# Run specific test file
python -m pytest tests/test_signals.py -v

# Run with coverage report
python -m pytest tests/ --cov=app --cov-report=html
```

## Code Quality & Development

### Code Formatting with Black

[Black](https://black.readthedocs.io/) is an opinionated Python code formatter that ensures consistent style across the codebase.

**Installation** (included in requirements.txt):
```bash
pip install black>=23.0.0
```

**Format Code**:
```bash
# Format all Python files
black app/ config/ tests/ utils/ scripts/ main.py

# Check formatting without applying changes
black --check app/ config/ tests/ utils/ scripts/ main.py

# Format with custom line length
black --line-length 100 app/
```

**Configuration**:
- Default line length: 88 characters
- Black is configured to work alongside Pylint
- No `.black` config file needed (uses defaults)

### Code Quality Analysis with Pylint

[Pylint](https://pylint.readthedocs.io/) performs static code analysis to identify potential bugs, code quality issues, and style problems.

**Installation** (included in requirements.txt):
```bash
pip install pylint>=2.16.0
```

**Run Pylint Analysis**:
```bash
# Analyze all code
pylint app/ config/ tests/ utils/ scripts/ main.py

# Show only errors and critical issues
pylint app/ config/ --disable=all --enable=E,F

# Generate detailed report
pylint app/ --output-format=json > pylint-report.json

# Check specific file
pylint app/core/signal_generator.py
```

**Configuration** (`.pylintrc`):
The project includes a `.pylintrc` configuration file that:
- Ignores test files (testing conventions are more relaxed)
- Disables overly strict rules for pragmatic development
- Sets maximum line length to 100 characters
- Focuses on real code quality issues, not stylistic nitpicks

**Current Code Quality Score**: 8.50/10
- 67/67 unit tests passing
- All imports optimized (unused imports removed)
- Consistent formatting throughout

### Development Workflow

**Step 1: Make Code Changes**
```bash
# Edit your files
vim app/core/signal_generator.py
```

**Step 2: Format with Black**
```bash
# Automatically format changed files
black app/core/signal_generator.py
```

**Step 3: Run Pylint**
```bash
# Check for code quality issues
pylint app/core/signal_generator.py
```

**Step 4: Run Tests**
```bash
# Ensure no regressions
python -m pytest tests/ -v
```

**Step 5: Commit Changes**
```bash
git add .
git commit -m "Description of changes"
git push
```

### Pre-Commit Best Practices

1. **Always format with Black first**
   - Ensures consistent style
   - Removes formatting debates from code reviews

2. **Fix Pylint warnings**
   - Address critical issues (E, F)
   - Review warnings (W) and suggestions (C, R)
   - Ignore acceptable style variations

3. **Run full test suite**
   - Verify all 67 tests pass
   - Check for any regressions

4. **Clean imports**
   - Remove unused imports (Pylint warning W0611)
   - Keep imports organized and minimal

### Common Pylint Issues & Solutions

| Issue | Severity | Solution |
|-------|----------|----------|
| Line too long | W | Use Black formatter or break into multiple lines |
| Unused import | W | Remove unused import statement |
| Unused variable | W | Remove or use with `_` prefix if intentional |
| Missing docstring | R | Add docstring to function/class |
| Too many arguments | W | Consider refactoring with dataclass or config |
| Broad exception | W | Catch specific exceptions when possible |

### Ignoring Pylint Warnings

If a Pylint warning is not applicable:

```python
# Disable for entire file
# pylint: disable=too-many-arguments

# Disable for specific line
some_function(a, b, c, d, e)  # pylint: disable=too-many-arguments

# Disable specific check globally in .pylintrc
# [MESSAGES CONTROL]
# disable=too-many-arguments
```

### Git Hooks (Optional)

To automatically format code before committing:

```bash
# Create pre-commit hook
cat > .git/hooks/pre-commit << 'EOF'
#!/bin/bash
black --check app/ config/ tests/ utils/ scripts/ main.py
if [ $? -ne 0 ]; then
  echo "Running black formatter..."
  black app/ config/ tests/ utils/ scripts/ main.py
  git add app/ config/ tests/ utils/ scripts/ main.py
fi
EOF

# Make hook executable
chmod +x .git/hooks/pre-commit
```

## Active Trading Signals

### How Signals Are Generated

A ticker appears in the **active signals list** when it passes through this pipeline:

1. **Data Requirement**: Must have 50+ periods of historical data
2. **Market Regime Detection**: System classifies current market as TRENDING_UP, TRENDING_DOWN, MEAN_REVERTING, SIDEWAYS, or HIGH_VOLATILITY
3. **Strategy Selection**:
   - Trending markets → Use MOMENTUM strategy (requires 4+ indicators aligned)
   - Ranging/volatile markets → Use MEAN REVERSION strategy (requires 3+ indicators aligned)
4. **Confidence Calculation**: Multi-factor scoring (0.5 base + bonuses for regime alignment, volume, extremes)
5. **Filtering**: Only signals with confidence ≥ 0.6 (60%) appear in the list
6. **Sorting**: Signals ranked by confidence (highest first)

### Signal Types

- **STRONG_BUY**: 5+ indicators aligned (highest confidence)
- **BUY**: 4+ indicators aligned
- **SELL**: 4+ bearish indicators aligned
- **STRONG_SELL**: 5+ bearish indicators aligned (highest confidence)

### Momentum Strategy (Trending Markets)

**Checked Indicators** (need 4+ for signal):
- MACD bullish/bearish crossover
- RSI in momentum range (45-75 for bullish)
- Price above moving averages (MA20 > MA50)
- Strong trend confirmation (ADX > 25)
- Volume surge (> 1.5x average)
- Composite momentum score

**Confidence Bonuses**:
- Regime alignment (BUY in uptrend): +20%
- Strong trend (ADX > 25): +10%
- Volume confirmation: +10%
- Extreme indicators (RSI > 75): +10%

### Mean Reversion Strategy (Ranging Markets)

**Checked Indicators** (need 3+ for signal):
- RSI oversold/overbought (< 30 or > 70)
- Bollinger Band extremes (price near upper/lower band)
- Stochastic oversold/overbought (%K < 20 or > 80)
- Williams %R extremes (< -80 or > -20)
- Mean reversion composite score

**Confidence Bonuses**:
- Ranging market alignment: +10%
- Bollinger Band extremes: +10%
- RSI extremes: +10%
- Volume confirmation: +10%

### Market Regime Detection

The system adapts based on:

| Indicator | Trending | Mean-Reverting | Ranging |
|-----------|----------|----------------|---------|
| Hurst Exponent | > 0.55 | < 0.45 | 0.45-0.55 |
| Trend Strength | > 0.7 | Low | Moderate |
| Volatility | Normal | Low | High |
| Strategy Used | Momentum | MR | MR |

### Risk Management

- **Position Sizing**: ATR-based (scales with volatility)
  - Stop Loss: 2 × ATR below entry
  - Target: 4 × ATR above entry
- **Maximum Position**: 20% of portfolio per ticker
- **Sector Limits**: 40% max concentration
- **Risk Monitoring**: Real-time correlation & drawdown tracking
- **Stress Testing**: Portfolio stress under extreme scenarios

### Why Tickers Don't Appear

A ticker is filtered out if:
- Less than 50 trading days of data available
- Strategy doesn't trigger (insufficient indicators aligned)
- Confidence score drops below 0.6 threshold
- Market regime doesn't match signal type

## 🔐 Security & Privacy

### Data Security

- Local database storage
- No API keys in code
- Environment variable configuration
- Secure IBM Cloud deployment

### Privacy

- No personal trading data stored
- Only market data collection
- Configurable data retention
- Optional cloud backup encryption

## Troubleshooting

### Common Issues & Solutions

**Application Won't Start - Unicode/Emoji Errors**:

```bash
# Error: 'charmap' codec can't encode character
# Solution: The system no longer uses emoji in output
# Make sure you have the latest version
git pull origin main
```

**Application Won't Start - Missing .env File**:

```bash
# Error: KeyError or missing database path
# Solution: Create .env file before running
cat > .env << EOF
FLASK_ENV=development
DATABASE_PATH=data/market_data.db
MIN_CONFIDENCE=0.6
UPDATE_INTERVAL_MINUTES=30
API_HOST=127.0.0.1
API_PORT=5000
EOF

python main.py
```

**API Endpoints Return Errors - Config Method Errors**:

```bash
# Error: "'method' object is not iterable"
# Solution: All Config methods must be called with parentheses
# Correct: Config.PORTFOLIO_TICKERS()
# Incorrect: Config.PORTFOLIO_TICKERS
```

**No Signals Generated - Confidence Too Low**:

```bash
# Issue: Tickers appear in data but not in active signals
# Possible reasons:
# 1. Confidence score below 0.6 threshold
# 2. Insufficient data (< 50 periods)
# 3. No strategy triggered (not enough indicators aligned)

# Solution: Lower confidence threshold for testing
python -c "
from app.core.data_manager import DataManager
from app.core.signal_generator import SignalGenerator

dm = DataManager()
sg = SignalGenerator(min_confidence=0.3)  # Lower threshold
data = dm.get_stock_data('AAPL', period='6mo')
signal = sg.generate_signal('AAPL', data)
if signal:
    print(f'{signal.ticker}: {signal.signal_type.value}')
    print(f'Confidence: {signal.confidence:.1%}')
    print(f'Reasons: {signal.reasons}')
else:
    print('No signal generated')
dm.close()
"
```

**Database Errors - UNIQUE Constraint Violations**:

```bash
# This is EXPECTED - indicates duplicate insertion attempts
# The system gracefully handles this with fallback to cached data
# Check logs: grep "UNIQUE constraint" logs/trading_system.log
# These appear at DEBUG level, not ERROR level
```

**Data Download Errors - Yahoo Finance Issues**:

```bash
# Check Yahoo Finance connectivity
python -c "import yfinance as yf; data = yf.download('AAPL', period='1d'); print(len(data))"

# Verify database connectivity
python -c "
from app.core.data_manager import DataManager
dm = DataManager()
data = dm.get_stock_data('AAPL', period='1d')
print(f'Got {len(data)} records')
dm.close()
"
```

**Dashboard Shows Missing Data**:

```bash
# Error: "name 'pd' is not defined"
# Solution: Update to latest code with pandas import fix
git pull origin main
pip install -r requirements.txt
```

### Running Tests

```bash
# Full test suite (all 67 tests should pass)
python -m pytest tests/ -v

# Run specific test file
python -m pytest tests/test_signals.py -v

# Run with coverage report
python -m pytest tests/ --cov=app --cov-report=html
```

### Logs and Debugging

```bash
# Check application logs in real-time
tail -f logs/trading_system.log

# Filter for errors
grep ERROR logs/trading_system.log

# Check health endpoint
curl http://localhost:5000/api/health | python -m json.tool

# Check current signals
curl http://localhost:5000/api/signals | python -m json.tool

# Check portfolio status
curl http://localhost:5000/api/portfolio | python -m json.tool
```

### Performance Optimization

```bash
# Check database size and statistics
python -c "
import sqlite3
conn = sqlite3.connect('data/market_data.db')
cursor = conn.cursor()

# Table sizes
cursor.execute('SELECT name, COUNT(*) as count FROM (SELECT name FROM sqlite_master WHERE type=\"table\") t JOIN (SELECT count(*) FROM daily_data) GROUP BY name')
for row in cursor:
    print(f'{row[0]}: {row[1]:,} records')

conn.close()
"

# Clean old data (> 2 years)
python -c "
from app.core.data_manager import DataManager
dm = DataManager()
deleted = dm.cleanup_old_data(days_to_keep=730)
print(f'Deleted {deleted} old records')
dm.close()
"
```

## 📚 Additional Resources

### Documentation

- [Yahoo Finance API](https://pypi.org/project/yfinance/)
- [TA-Lib Documentation](https://ta-lib.org/)
- [IBM Cloud Code Engine](https://cloud.ibm.com/docs/codeengine)
- [Technical Analysis Basics](https://www.investopedia.com/technical-analysis-4689657)

### Customization Examples

- Adding new indicators
- Implementing custom strategies
- Extending the web dashboard
- Integration with brokers

### Community

- GitHub Issues for bug reports
- Feature requests welcome
- Trading strategy discussions
- Performance optimization tips

## 📄 License

This project is for educational and personal use. Not financial advice.

**Disclaimer**: This system is for educational purposes only. Always consult with a financial advisor before making
investment decisions. Past performance does not guarantee future results.

---

## 🏗 System Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Yahoo Finance │────│  Data Manager   │────│   SQLite DB     │
│       API       │    │                 │    │                 │
└─────────────────┘    └─────────────────┘    └─────────────────┘
                                │
                                ▼
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Technical     │────│ Signal Generator│────│ Portfolio       │
│   Indicators    │    │                 │    │ Analyzer        │
└─────────────────┘    └─────────────────┘    └─────────────────┘
                                │
                                ▼
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│  Web Dashboard  │────│  Flask API      │────│ Monitoring &    │
│                 │    │                 │    │ Alerts          │
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

## Project Structure

```
traderrr/
├── main.py                         # Flask app entry point and WSGI application
├── requirements.txt                # Python dependencies
├── .env                           # Environment variables (create before running)
│
├── app/                           # Main application package
│   ├── __init__.py
│   ├── api/
│   │   ├── __init__.py
│   │   └── routes.py              # REST API endpoints (/api/signals, /api/health, etc.)
│   ├── core/
│   │   ├── __init__.py
│   │   ├── data_manager.py        # Yahoo Finance data retrieval & caching
│   │   ├── signal_generator.py    # Trading signal generation logic
│   │   ├── portfolio_analyzer.py  # Portfolio metrics & risk analysis
│   │   └── indicators.py          # Technical indicators & market regime detection
│   └── web/
│       ├── __init__.py
│       └── dashboard.py            # Web dashboard UI
│
├── config/                        # Configuration modules
│   ├── __init__.py
│   ├── settings.py                # Config class with static methods
│   ├── database.py                # Database schema & initialization
│   └── json                       # (Legacy, use settings.py instead)
│
├── tests/                         # Unit test suite (67 tests, all passing)
│   ├── test_data_manager.py
│   ├── test_indicators.py
│   ├── test_portfolio.py
│   └── test_signals.py
│
├── scripts/                       # Utility and maintenance scripts
│   ├── daily_update.py            # Background data update routine
│   ├── backtest.py                # Strategy backtesting
│   └── deploy.py                  # IBM Cloud deployment helper
│
├── utils/                         # Development utilities
│   └── dev_tools.py               # Sample data generation & testing helpers
│
├── data/                          # Data storage (created on first run)
│   └── market_data.db             # SQLite database with daily/intraday data
│
├── logs/                          # Application logs
│   └── trading_system.log         # Main application log
│
├── backups/                       # Database backups
│   └── *.db                       # Backup files (created by backup_database())
│
├── cache/                         # Temporary cache files
│
├── Dockerfile                     # Docker container configuration
├── manifest.yml                   # IBM Cloud manifest
└── README.md                      # This documentation
```

### Key Modules

- **app/core/data_manager.py** (595 lines): Handles Yahoo Finance data, database caching, rate limiting
- **app/core/signal_generator.py** (506 lines): Regime detection, dual strategies, confidence scoring
- **app/core/indicators.py** (900+ lines): 20+ technical indicators + market regime detection
- **app/core/portfolio_analyzer.py**: Portfolio metrics, risk analysis, optimization
- **app/api/routes.py** (410 lines): REST API with 7 endpoints + signal initialization
- **main.py** (369 lines): Flask setup, database init, background scheduler

---

*Built with ❤️ for algorithmic trading enthusiasts*