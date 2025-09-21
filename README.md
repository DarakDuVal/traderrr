# Trading Signals System

A comprehensive algorithmic trading system built with Yahoo Finance data, advanced technical indicators, and machine
learning-based signal generation. Designed for deployment on IBM Cloud with real-time monitoring and risk management.

## 🚀 Features

### Core Functionality

- **Real-time Data**: Yahoo Finance integration with caching and error handling
- **Advanced Indicators**: 15+ technical indicators with regime detection
- **Smart Signals**: Context-aware buy/sell signals with confidence scoring
- **Portfolio Analytics**: Risk metrics, correlation analysis, and optimization
- **Web Dashboard**: Real-time monitoring with interactive charts
- **RESTful API**: Complete API for integration and automation

### Technical Highlights

- **Regime Detection**: Automatically adapts strategy for trending vs mean-reverting markets
- **Risk Management**: Position sizing, VAR calculation, and stress testing
- **Performance Optimization**: Vectorized calculations and efficient data storage
- **Production Ready**: Comprehensive logging, error handling, and monitoring

## 📋 Prerequisites

- Python 3.8 or higher
- 4GB+ RAM (8GB recommended for full portfolio)
- 10GB+ disk space for historical data
- IBM Cloud account (for cloud deployment)

## 🛠 Installation

### Quick Setup

```bash
# Clone repository (if not already done)
cd trading-system

# Create virtual environment
python -m venv trading_env
source trading_env/bin/activate  # On Windows: trading_env\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Create environment file
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
docker build -t trading-app .
docker run -p 8080:8080 trading-app

# Install IBM Cloud CLI and login
ibmcloud login
ibmcloud plugin install code-engine

python scripts/deploy.py \
  --registry-namespace your-namespace \
  --project-name trading-signals \
  --cpu 1 \
  --memory 2G
```

## ⚙️ Configuration

Edit `config.json` to customize your setup:

```json
{
  "portfolio": {
    "tickers": [
      "AAPL",
      "MSFT",
      "GOOGL",
      "JPM",
      "VTI"
    ],
    "weights": {
      "AAPL": 0.25,
      "MSFT": 0.20,
      "GOOGL": 0.20,
      "JPM": 0.15,
      "VTI": 0.20
    },
    "total_value": 50000,
    "rebalance_threshold": 0.05
  },
  "signals": {
    "min_confidence": 0.6,
    "momentum_threshold": 60.0,
    "mean_reversion_threshold": 70.0,
    "update_interval_minutes": 30
  },
  "risk": {
    "max_position_size": 0.20,
    "max_sector_concentration": 0.40,
    "volatility_limit": 0.25
  }
}
```

## 🎯 Usage Examples

### Basic Signal Generation

```python
from data_manager import DataManager
from signal_generator import SignalGenerator

# Initialize components
dm = DataManager()
signal_gen = SignalGenerator(min_confidence=0.6)

# Get data and generate signals
data = dm.get_stock_data('AAPL', period='6mo')
signal = signal_gen.generate_signal('AAPL', data)

if signal:
    print(f"Signal: {signal.signal_type.value}")
    print(f"Confidence: {signal.confidence:.2%}")
    print(f"Entry: ${signal.entry_price:.2f}")
    print(f"Target: ${signal.target_price:.2f}")
    print(f"Stop Loss: ${signal.stop_loss:.2f}")
```

### Portfolio Analysis

```python
from portfolio_analyzer import PortfolioAnalyzer

analyzer = PortfolioAnalyzer()

# Analyze portfolio
tickers = ['AAPL', 'MSFT', 'GOOGL', 'JPM', 'VTI']
weights = {'AAPL': 0.25, 'MSFT': 0.20, 'GOOGL': 0.20, 'JPM': 0.15, 'VTI': 0.20}

# Download data
portfolio_data = {}
for ticker in tickers:
    portfolio_data[ticker] = dm.get_stock_data(ticker, period='1y')

# Calculate metrics
metrics = analyzer.analyze_portfolio(portfolio_data, weights)
print(f"Portfolio Volatility: {metrics.volatility:.2%}")
print(f"Sharpe Ratio: {metrics.sharpe_ratio:.2f}")
print(f"Max Drawdown: {metrics.max_drawdown:.2%}")

# Risk analysis
position_risks = analyzer.calculate_position_risks(portfolio_data, weights, 100000)
for risk in position_risks:
    print(f"{risk.ticker}: Risk contribution {risk.contribution_to_risk:.4f}")
```

### Technical Indicators

```python
from indicators import TechnicalIndicators, MarketRegimeDetector

ti = TechnicalIndicators()
detector = MarketRegimeDetector()

# Calculate indicators
data = dm.get_stock_data('AAPL', period='3mo')
prices = data['Close']

rsi = ti.rsi(prices)
macd_line, signal_line, histogram = ti.macd(prices)
upper, middle, lower = ti.bollinger_bands(prices)

# Detect market regime
hurst = detector.hurst_exponent(prices)
trend_strength = detector.trend_strength(prices)

print(f"RSI: {rsi.iloc[-1]:.1f}")
print(f"MACD Signal: {'Bullish' if macd_line.iloc[-1] > signal_line.iloc[-1] else 'Bearish'}")
print(f"Market Regime: {'Trending' if hurst > 0.5 else 'Mean Reverting'}")
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
docker build -t trading-app .
docker tag trading-app icr.io/your-namespace/trading-app
docker push icr.io/your-namespace/trading-app
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
    --name trading-app \
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
ibmcloud ce application bind --name trading-app --service-instance trading-cloudant-db
ibmcloud ce application bind --name trading-app --service-instance trading-object-storage
```

### Environment Variables

Set these in IBM Cloud Console or via CLI:

```bash
ibmcloud ce application update trading-app \
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
# Full test suite
python testing_framework.py

# Individual components
python -m unittest testing_framework.TestDataManager
python -m unittest testing_framework.TestSignalGenerator
python -m unittest testing_framework.TestPortfolioAnalyzer
```

### Performance Benchmarks

```bash
# Run performance tests
python -c "from testing_framework import PerformanceBenchmark; PerformanceBenchmark.benchmark_data_manager()"
```

## 📈 Strategy Details

### Signal Generation Logic

**Momentum Strategy** (Trending Markets):

- MACD bullish crossover
- RSI in momentum range (45-75)
- Price above moving averages
- Strong ADX trend confirmation
- Volume surge confirmation

**Mean Reversion Strategy** (Ranging Markets):

- RSI oversold/overbought (< 30 or > 70)
- Bollinger Band extremes
- Stochastic oversold/overbought
- Williams %R extremes
- Volume confirmation

### Risk Management

- Position sizing based on volatility (ATR)
- Maximum 20% allocation per position
- Sector concentration limits (40% max)
- Real-time correlation monitoring
- Stress testing scenarios

### Market Regime Detection

- Hurst Exponent calculation
- Trend strength analysis
- Volatility regime classification
- Automatic strategy adaptation

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

## 🛟 Troubleshooting

### Common Issues

**Data Download Errors**:

```bash
# Check Yahoo Finance connectivity
python -c "import yfinance as yf; print(yf.Ticker('AAPL').history(period='1d'))"

# Verify database connectivity
python -c "from data_manager import DataManager; dm = DataManager(); print('OK'); dm.close()"
```

**Performance Issues**:

```bash
# Check database size
python deployment_utilities.py database stats

# Clean old data
python deployment_utilities.py database cleanup

# Vacuum database
python -c "from deployment_utilities import DatabaseManager; DatabaseManager('market_data.db').vacuum_database()"
```

**Signal Generation Problems**:

```bash
# Test with minimal data
python -c "
from signal_generator import SignalGenerator
from data_manager import DataManager
dm = DataManager()
sg = SignalGenerator(min_confidence=0.3)
data = dm.get_stock_data('AAPL', period='60d')
signal = sg.generate_signal('AAPL', data)
print(signal)
"
```

### Logs and Debugging

- Application logs: Check console output
- Database logs: SQLite error messages
- IBM Cloud logs: `ibmcloud ce application logs trading-app`
- Health endpoint: `curl http://localhost:5000/api/health`

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

## 📊 File Structure

```
trading-system/
├── main.py                    # Flask application and main entry point
├── data_manager.py            # Yahoo Finance data management
├── indicators.py              # Technical indicators and regime detection
├── signal_generator.py        # Trading signal generation
├── portfolio_analyzer.py      # Portfolio analysis and risk management
├── testing_framework.py       # Testing and configuration management
├── deployment_utilities.py    # Deployment and system utilities
├── config.json               # Configuration file
├── requirements.txt          # Python dependencies
├── Dockerfile               # Container configuration
├── manifest.yml             # IBM Cloud manifest
├── market_data.db           # SQLite database (created on first run)
└── README.md                # This documentation
```

---

*Built with ❤️ for algorithmic trading enthusiasts*