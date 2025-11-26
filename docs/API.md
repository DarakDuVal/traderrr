# Traderrr Trading System API Documentation

## Overview

The Traderrr Trading System API is a professional algorithmic trading platform providing:

- **Trading Signal Generation**: Automated buy/sell signals based on technical analysis
- **Portfolio Management**: Track positions, manage allocations, and monitor performance
- **Risk Analysis**: Analyze portfolio risk, correlation matrices, and optimization
- **Performance Metrics**: Historical performance data and comprehensive metrics

**API Version**: 1.0.0
**Base URL**: `http://localhost:5000/api`
**Documentation**: `http://localhost:5000/api/docs` (Swagger UI)
**OpenAPI Spec**: `http://localhost:5000/apispec.json`

---

## Authentication

All API endpoints require Bearer token authentication via the `Authorization` header.

### Format

```
Authorization: Bearer YOUR_API_KEY
```

### Demo API Keys

For testing, use these demo keys:
- `demo-api-key-12345` (demo_user)
- `test-api-key-67890` (test_user)

### Generating API Keys

```python
from app.api.auth import generate_api_key

api_key = generate_api_key("username")
print(f"New API key: {api_key}")
```

### Error Response (Missing/Invalid Key)

```json
{
  "error": "Missing authorization header. Use: Authorization: Bearer <api_key>",
  "timestamp": "2025-11-26T10:30:00.123456"
}
```

---

## API Endpoints

### Health Endpoints

#### GET /health

Check system health status including database connectivity and data freshness.

**Request:**
```bash
curl -H "Authorization: Bearer demo-api-key-12345" \
  http://localhost:5000/api/health
```

**Response (200 - Healthy):**
```json
{
  "status": "healthy",
  "timestamp": "2025-11-26T10:30:00.123456",
  "database": "connected",
  "last_update": "2025-11-26T10:25:00.123456",
  "signal_count": 15,
  "version": "1.0.0"
}
```

**Response (503 - Degraded):**
```json
{
  "status": "degraded",
  "timestamp": "2025-11-26T10:30:00.123456",
  "database": "connected",
  "last_update": "2025-11-26T08:00:00.123456",
  "signal_count": 15,
  "version": "1.0.0",
  "warning": "Data may be stale"
}
```

---

### Signals Endpoints

#### GET /signals

Get current active trading signals.

**Request:**
```bash
curl -H "Authorization: Bearer demo-api-key-12345" \
  http://localhost:5000/api/signals
```

**Response:**
```json
{
  "signals": [
    {
      "ticker": "AAPL",
      "signal_type": "BUY",
      "confidence": 0.85,
      "entry_price": 150.25,
      "stop_loss": 145.00,
      "target_price": 160.00,
      "regime": "TRENDING_UP",
      "reasons": [
        "RSI above 50 with upward momentum",
        "Price above 20-day MA",
        "Volume increasing"
      ],
      "timestamp": "2025-11-26T10:20:00.123456"
    }
  ],
  "last_update": "2025-11-26T10:20:00.123456",
  "total_count": 1
}
```

#### GET /signal-history

Get historical trading signals with optional filters.

**Query Parameters:**
- `ticker` (string): Filter by ticker symbol
- `start_date` (string): Start date (YYYY-MM-DD)
- `end_date` (string): End date (YYYY-MM-DD)
- `signal_type` (string): Filter by BUY, SELL, or HOLD
- `min_confidence` (number): Minimum confidence (0.0-1.0)
- `limit` (integer): Max records (default: 100, max: 1000)

**Request:**
```bash
curl -H "Authorization: Bearer demo-api-key-12345" \
  "http://localhost:5000/api/signal-history?ticker=AAPL&signal_type=BUY&min_confidence=0.8&limit=10"
```

**Response:**
```json
{
  "signals": [...],
  "count": 10,
  "filters": {
    "ticker": "AAPL",
    "start_date": null,
    "end_date": null,
    "signal_type": "BUY",
    "min_confidence": 0.8,
    "limit": 10
  }
}
```

#### GET /signal-history/{ticker}

Get signal history for a specific ticker.

**Parameters:**
- `ticker` (path): Stock ticker symbol (e.g., AAPL)
- `limit` (query): Max records (default: 50, max: 1000)

**Request:**
```bash
curl -H "Authorization: Bearer demo-api-key-12345" \
  http://localhost:5000/api/signal-history/AAPL?limit=20
```

#### GET /signal-stats

Get signal statistics and performance metrics.

**Query Parameters:**
- `ticker` (string): Optional - filter by specific ticker

**Request:**
```bash
curl -H "Authorization: Bearer demo-api-key-12345" \
  http://localhost:5000/api/signal-stats?ticker=AAPL
```

**Response:**
```json
{
  "ticker": "AAPL",
  "stats": {
    "total_signals": 45,
    "buy_signals": 18,
    "sell_signals": 12,
    "hold_signals": 15,
    "average_confidence": 0.76,
    "success_rate": 0.72,
    "period": "30d",
    "last_updated": "2025-11-26T10:20:00.123456"
  }
}
```

#### POST /update

Manually trigger a signal update (runs in background).

**Request:**
```bash
curl -X POST -H "Authorization: Bearer demo-api-key-12345" \
  http://localhost:5000/api/update
```

**Response (202 - Accepted):**
```json
{
  "message": "Signal update initiated",
  "timestamp": "2025-11-26T10:30:00.123456"
}
```

---

### Portfolio Performance Endpoints

#### GET /portfolio-performance

Get historical portfolio performance data.

**Query Parameters:**
- `start_date` (string): Start date (YYYY-MM-DD)
- `end_date` (string): End date (YYYY-MM-DD)
- `limit` (integer): Max records (default: 100, max: 1000)

**Request:**
```bash
curl -H "Authorization: Bearer demo-api-key-12345" \
  "http://localhost:5000/api/portfolio-performance?limit=30"
```

**Response:**
```json
{
  "performance": [
    {
      "date": "2025-11-26",
      "portfolio_value": 150000.00,
      "daily_return": 0.025,
      "volatility": 0.12,
      "sharpe_ratio": 1.5,
      "max_drawdown": -0.08
    }
  ],
  "count": 30,
  "filters": {
    "start_date": null,
    "end_date": null,
    "limit": 30
  }
}
```

#### GET /portfolio-performance/summary

Get portfolio performance summary for a period.

**Query Parameters:**
- `days` (integer): Look-back period (default: 30, max: 365)

**Request:**
```bash
curl -H "Authorization: Bearer demo-api-key-12345" \
  http://localhost:5000/api/portfolio-performance/summary?days=90
```

#### GET /portfolio-performance/metrics

Get comprehensive portfolio performance metrics.

**Query Parameters:**
- `days` (integer): Analysis period (default: 90, max: 365)

**Request:**
```bash
curl -H "Authorization: Bearer demo-api-key-12345" \
  http://localhost:5000/api/portfolio-performance/metrics?days=180
```

**Response:**
```json
{
  "period_days": 180,
  "metrics": {
    "total_return": 0.185,
    "annualized_return": 0.412,
    "volatility": 0.145,
    "sharpe_ratio": 2.84,
    "max_drawdown": -0.12,
    "win_rate": 0.58,
    "worst_day": -0.045,
    "best_day": 0.062
  }
}
```

#### GET /portfolio-performance/latest

Get the latest portfolio performance record.

**Request:**
```bash
curl -H "Authorization: Bearer demo-api-key-12345" \
  http://localhost:5000/api/portfolio-performance/latest
```

---

### Portfolio Management Endpoints

#### GET /portfolio

Get portfolio overview with metrics and risk analysis.

**Request:**
```bash
curl -H "Authorization: Bearer demo-api-key-12345" \
  http://localhost:5000/api/portfolio
```

**Response:**
```json
{
  "portfolio_metrics": {
    "volatility": 0.145,
    "sharpe_ratio": 2.84,
    "max_drawdown": -0.12,
    "value_at_risk": -0.085,
    "expected_shortfall": -0.105
  },
  "position_risks": [
    {
      "ticker": "AAPL",
      "weight": 0.25,
      "position_size": 37500,
      "risk_contribution": 0.042,
      "liquidity_score": 0.95,
      "concentration_risk": 0.12
    }
  ],
  "portfolio_overview": {
    "AAPL": {
      "price": 150.25,
      "daily_change": 0.012,
      "volume_ratio": 1.15,
      "weight": 0.25
    }
  },
  "total_value": 150000.00,
  "updated_at": "2025-11-26T10:30:00.123456"
}
```

#### GET /portfolio/positions

Get all portfolio positions with current values.

**Request:**
```bash
curl -H "Authorization: Bearer demo-api-key-12345" \
  http://localhost:5000/api/portfolio/positions
```

**Response:**
```json
{
  "positions": [
    {
      "ticker": "AAPL",
      "shares": 250,
      "current_price": 150.25,
      "position_value": 37562.50
    }
  ],
  "total_value": 150000.00,
  "updated_at": "2025-11-26T10:30:00.123456"
}
```

#### POST /portfolio/positions

Add or update a portfolio position.

**Request Body:**
```json
{
  "ticker": "MSFT",
  "shares": 100
}
```

**Request:**
```bash
curl -X POST \
  -H "Authorization: Bearer demo-api-key-12345" \
  -H "Content-Type: application/json" \
  -d '{"ticker": "MSFT", "shares": 100}' \
  http://localhost:5000/api/portfolio/positions
```

**Response (201):**
```json
{
  "message": "Position MSFT updated successfully",
  "position": {
    "ticker": "MSFT",
    "shares": 100.0,
    "current_price": 450.75,
    "position_value": 45075.00
  },
  "updated_at": "2025-11-26T10:30:00.123456"
}
```

#### PUT /portfolio/positions/{ticker}

Update shares for a specific position.

**Request:**
```bash
curl -X PUT \
  -H "Authorization: Bearer demo-api-key-12345" \
  -H "Content-Type: application/json" \
  -d '{"shares": 150}' \
  http://localhost:5000/api/portfolio/positions/MSFT
```

#### DELETE /portfolio/positions/{ticker}

Remove a position from the portfolio.

**Request:**
```bash
curl -X DELETE \
  -H "Authorization: Bearer demo-api-key-12345" \
  http://localhost:5000/api/portfolio/positions/MSFT
```

**Response:**
```json
{
  "message": "Position MSFT removed successfully",
  "updated_at": "2025-11-26T10:30:00.123456"
}
```

---

### Ticker Data Endpoints

#### GET /tickers/{ticker}

Get detailed data for a specific ticker including technical indicators.

**Parameters:**
- `ticker` (path): Stock ticker symbol
- `period` (query): Data period (default: 3mo) - e.g., 1d, 5d, 1mo, 3mo, 6mo, 1y
- `indicators` (query): Include technical indicators (true/false)

**Request:**
```bash
curl -H "Authorization: Bearer demo-api-key-12345" \
  "http://localhost:5000/api/tickers/AAPL?period=6mo&indicators=true"
```

**Response:**
```json
{
  "ticker": "AAPL",
  "period": "6mo",
  "data_points": 126,
  "date_range": {
    "start": "2025-05-26",
    "end": "2025-11-26"
  },
  "current_price": 150.25,
  "daily_change": 0.012,
  "volume": 52000000,
  "indicators": {
    "rsi": 65.5,
    "macd": {
      "line": 2.45,
      "signal": 1.85,
      "bullish": true
    },
    "bollinger_bands": {
      "upper": 155.80,
      "middle": 148.50,
      "lower": 141.20,
      "position": 0.65
    }
  }
}
```

---

### Risk Analysis Endpoints

#### GET /risk-report

Get comprehensive risk report for the portfolio.

**Request:**
```bash
curl -H "Authorization: Bearer demo-api-key-12345" \
  http://localhost:5000/api/risk-report
```

**Response:**
```json
{
  "portfolio_var": -0.085,
  "portfolio_es": -0.105,
  "concentration_risk": 0.18,
  "correlation_risk": 0.45,
  "position_risks": [...],
  "recommendations": [
    "Reduce AAPL concentration (25% is above 20% threshold)",
    "Consider increasing MSFT for diversification",
    "Monitor Tesla correlation - increased to 0.78"
  ]
}
```

#### GET /correlation

Get correlation matrix for portfolio assets.

**Request:**
```bash
curl -H "Authorization: Bearer demo-api-key-12345" \
  http://localhost:5000/api/correlation
```

**Response:**
```json
{
  "tickers": ["AAPL", "MSFT", "GOOGL", "AMZN", "NVDA"],
  "matrix": [
    [1.00, 0.65, 0.72, 0.58, 0.45],
    [0.65, 1.00, 0.68, 0.52, 0.48],
    [0.72, 0.68, 1.00, 0.61, 0.51],
    [0.58, 0.52, 0.61, 1.00, 0.44],
    [0.45, 0.48, 0.51, 0.44, 1.00]
  ],
  "average_correlation": 0.58,
  "max_correlation": 0.72,
  "min_correlation": 0.44
}
```

#### POST /optimization

Get optimal portfolio weights based on risk/return objectives.

**Request Body:**
```json
{
  "risk_tolerance": 0.12,
  "target_return": 0.15
}
```

**Request:**
```bash
curl -X POST \
  -H "Authorization: Bearer demo-api-key-12345" \
  -H "Content-Type: application/json" \
  -d '{"risk_tolerance": 0.12, "target_return": 0.15}' \
  http://localhost:5000/api/optimization
```

**Response:**
```json
{
  "current_weights": {
    "AAPL": 0.25,
    "MSFT": 0.20,
    "GOOGL": 0.18,
    "AMZN": 0.15,
    "NVDA": 0.22
  },
  "optimized_weights": {
    "AAPL": 0.18,
    "MSFT": 0.25,
    "GOOGL": 0.22,
    "AMZN": 0.20,
    "NVDA": 0.15
  },
  "current_metrics": {
    "volatility": 0.145,
    "sharpe_ratio": 2.84,
    "max_drawdown": -0.12
  },
  "optimized_metrics": {
    "volatility": 0.120,
    "sharpe_ratio": 3.12,
    "max_drawdown": -0.08
  },
  "parameters": {
    "risk_tolerance": 0.12,
    "target_return": 0.15
  }
}
```

---

## Error Handling

### Error Response Format

```json
{
  "error": "Error message describing the problem",
  "timestamp": "2025-11-26T10:30:00.123456",
  "details": "Additional context if available"
}
```

### Common Status Codes

| Code | Description |
|------|-------------|
| 200 | Successful GET request |
| 201 | Successful POST request (resource created) |
| 202 | Request accepted (async processing) |
| 400 | Bad request (invalid parameters) |
| 401 | Unauthorized (missing/invalid API key) |
| 404 | Not found (resource doesn't exist) |
| 500 | Server error |
| 503 | Service unavailable (degraded) |

### Example Error Responses

**Missing API Key:**
```json
{
  "error": "Missing authorization header. Use: Authorization: Bearer <api_key>",
  "timestamp": "2025-11-26T10:30:00.123456"
}
```

**Invalid Position Data:**
```json
{
  "error": "Validation failed",
  "issues": ["Shares must be positive", "Ticker must be valid"],
  "timestamp": "2025-11-26T10:30:00.123456"
}
```

**No Portfolio Configured:**
```json
{
  "error": "No portfolio positions configured",
  "timestamp": "2025-11-26T10:30:00.123456"
}
```

---

## Rate Limiting

Currently, there is no rate limiting implemented. All authenticated requests are processed immediately.

---

## Pagination

Endpoints that return lists support pagination via `limit` parameter:
- Default limit: 100 records
- Maximum limit: 1000 records
- Limits are applied to prevent excessive data transfer

---

## Data Types

### Numeric Precision

- **Prices & Values**: Float with 2 decimal places
- **Percentages**: Float (0.0 to 1.0 for ratios, e.g., 0.25 = 25%)
- **Timestamps**: ISO 8601 format with microsecond precision

### Date Formats

- **Query Parameters**: YYYY-MM-DD (e.g., 2025-11-26)
- **Response Timestamps**: ISO 8601 format (e.g., 2025-11-26T10:30:00.123456)

---

## Implementation Examples

### Python

```python
import requests
import json

API_KEY = "demo-api-key-12345"
BASE_URL = "http://localhost:5000/api"

headers = {
    "Authorization": f"Bearer {API_KEY}",
    "Content-Type": "application/json"
}

# Get current signals
response = requests.get(f"{BASE_URL}/signals", headers=headers)
signals = response.json()
print(f"Current signals: {signals['total_count']}")

# Add portfolio position
position_data = {
    "ticker": "MSFT",
    "shares": 100
}
response = requests.post(
    f"{BASE_URL}/portfolio/positions",
    headers=headers,
    json=position_data
)
print(f"Status: {response.status_code}")
print(response.json())
```

### JavaScript/Node.js

```javascript
const API_KEY = "demo-api-key-12345";
const BASE_URL = "http://localhost:5000/api";

const headers = {
  "Authorization": `Bearer ${API_KEY}`,
  "Content-Type": "application/json"
};

// Get current signals
fetch(`${BASE_URL}/signals`, { headers })
  .then(r => r.json())
  .then(data => console.log(`Current signals: ${data.total_count}`));

// Add portfolio position
const positionData = {
  ticker: "MSFT",
  shares: 100
};

fetch(`${BASE_URL}/portfolio/positions`, {
  method: "POST",
  headers,
  body: JSON.stringify(positionData)
})
  .then(r => r.json())
  .then(data => console.log(data));
```

### cURL

```bash
# Health check
curl -H "Authorization: Bearer demo-api-key-12345" \
  http://localhost:5000/api/health

# Get signals
curl -H "Authorization: Bearer demo-api-key-12345" \
  http://localhost:5000/api/signals

# Add position
curl -X POST \
  -H "Authorization: Bearer demo-api-key-12345" \
  -H "Content-Type: application/json" \
  -d '{"ticker":"MSFT","shares":100}' \
  http://localhost:5000/api/portfolio/positions
```

---

## Swagger UI

Interactive API documentation is available at:

**`http://localhost:5000/api/docs`**

The Swagger UI allows you to:
- View all endpoints and their documentation
- See request/response schemas
- Try out API calls directly in the browser
- Download OpenAPI specification

---

## OpenAPI Specification

The full OpenAPI 3.0 specification is available at:

**`http://localhost:5000/apispec.json`**

This can be imported into tools like:
- Postman
- Insomnia
- SwaggerHub
- VS Code REST Client

---

## Support

For issues, questions, or contributions, please refer to the main project documentation or contact the development team.

**Last Updated**: 2025-11-26
**API Version**: 1.0.0
**Status**: Production
