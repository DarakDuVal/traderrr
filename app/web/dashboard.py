"""
app/web/dashboard.py - Web dashboard interface
"""

from flask import Blueprint, render_template, request
import json
import logging
from typing import List, Dict, Any, Union, Tuple
import os

# Get the directory where this file is located
current_dir = os.path.dirname(os.path.abspath(__file__))
template_dir = os.path.join(current_dir, "templates")

web_bp = Blueprint("web", __name__, template_folder=template_dir)
logger = logging.getLogger(__name__)

# Default API key for development (should be set via environment in production)
DEFAULT_API_KEY = "test-api-key-67890"


@web_bp.route("/")
def dashboard() -> Union[str, Tuple[str, int]]:
    """Main dashboard"""
    try:
        # Get data from API endpoints
        signals_data: List[Any] = []
        portfolio_overview: Dict[str, Any] = {}
        portfolio_metrics: Dict[str, Any] = {}

        # Try to get signals from API
        try:
            # In a real deployment, you'd call the API endpoints
            # For now, we'll use placeholder data or import directly
            from app.api.routes import current_signals

            signals_data = current_signals
        except Exception as e:
            logger.warning(f"Could not get signals: {e}")

        # Portfolio data is now loaded client-side with JWT authentication
        # This ensures each user only sees their own portfolio data
        portfolio_value = 0.0
        # Empty values - will be populated by client-side API calls after authentication

        # Calculate summary stats
        total_signals = len(signals_data)
        buy_signals = len([s for s in signals_data if "BUY" in s.signal_type.value])
        sell_signals = len([s for s in signals_data if "SELL" in s.signal_type.value])
        avg_confidence = (
            sum(s.confidence for s in signals_data) / len(signals_data)
            if signals_data
            else 0
        )

        # Determine status color
        if total_signals > 5:
            status_color = "good"
        elif total_signals > 2:
            status_color = "warning"
        else:
            status_color = "error"

        # Get last update time
        try:
            from app.api.routes import last_update

            update_time = last_update
        except Exception:
            update_time = None

        return render_template(
            "dashboard.html",
            api_key=DEFAULT_API_KEY,
            signals=signals_data,
            total_signals=total_signals,
            buy_signals=buy_signals,
            sell_signals=sell_signals,
            avg_confidence=avg_confidence,
            portfolio_value=portfolio_value,  # Dynamically calculated from database
            total_tickers=len(portfolio_overview),
            last_update=update_time,
            portfolio_overview=portfolio_overview,
            portfolio_metrics=portfolio_metrics,
            status_color=status_color,
        )

    except Exception as e:
        logger.error(f"Dashboard error: {e}")
        return (
            f"""
        <div style="text-align: center; padding: 2rem; font-family: Arial, sans-serif;">
            <h1>🚨 Dashboard Error</h1>
            <p>Error loading dashboard: {e}</p>
            <p><a href="/api/health">Check System Health</a></p>
        </div>
        """,
            500,
        )


@web_bp.route("/signals")
def signals_page() -> Union[str, Tuple[str, int]]:
    """Detailed signals page"""
    try:
        from app.api.routes import current_signals

        signals_html = """
        <div style="font-family: Arial, sans-serif; padding: 2rem;">
            <h1>Trading Signals Detail</h1>
        """

        if current_signals:
            for signal in current_signals:
                signals_html += f"""
                <div style="border: 1px solid #ddd; margin: 1rem 0; padding: 1rem; border-radius: 8px;">
                    <h3>{signal.ticker} - {signal.signal_type.value}</h3>
                    <p><strong>Confidence:</strong> {signal.confidence:.1%}</p>
                    <p><strong>Entry:</strong> ${signal.entry_price:.2f}</p>
                    <p><strong>Target:</strong> ${signal.target_price:.2f}</p>
                    <p><strong>Stop Loss:</strong> ${signal.stop_loss:.2f}</p>
                    <p><strong>Regime:</strong> {signal.regime.value}</p>
                    <p><strong>Reasons:</strong> {', '.join(signal.reasons)}</p>
                </div>
                """
        else:
            signals_html += "<p>No active signals</p>"

        signals_html += """
            <p><a href="/">← Back to Dashboard</a></p>
        </div>
        """

        return signals_html

    except Exception as e:
        return f"Error: {e}", 500


@web_bp.route("/portfolio")
def portfolio_page() -> Union[str, Tuple[str, int]]:
    """Detailed portfolio page"""
    try:
        from config.settings import Config
        from app.core.data_manager import DataManager
        from app.core.portfolio_manager import PortfolioManager

        dm = DataManager(db_path=Config.DATABASE_PATH())
        pm = PortfolioManager(db_path=Config.DATABASE_PATH())

        # Get positions from database
        positions = pm.get_all_positions()
        if not positions:
            return (
                """
                <div style="font-family: Arial, sans-serif; padding: 2rem;">
                    <h1>Portfolio Details</h1>
                    <p>No positions in portfolio</p>
                    <p><a href="/">← Back to Dashboard</a></p>
                </div>
                """,
                200,
            )

        # Get current prices
        current_prices = {}
        for ticker in positions.keys():
            try:
                data = dm.get_stock_data(ticker, period="1d")
                if not data.empty:
                    current_prices[ticker] = data["Close"].iloc[-1]
                else:
                    current_prices[ticker] = 0
            except Exception:
                current_prices[ticker] = 0

        # Calculate weights and total value
        weights = pm.get_weights(current_prices)
        total_value = pm.get_total_value(current_prices)

        portfolio_html = f"""
        <div style="font-family: Arial, sans-serif; padding: 2rem;">
            <h1>Portfolio Details</h1>
            <h2>Holdings ({len(positions)} positions)</h2>
            <h3>Total Value: ${total_value:,.2f}</h3>
            <table border="1" style="border-collapse: collapse; width: 100%;">
                <tr>
                    <th style="padding: 8px;">Ticker</th>
                    <th style="padding: 8px;">Shares</th>
                    <th style="padding: 8px;">Price</th>
                    <th style="padding: 8px;">Value</th>
                    <th style="padding: 8px;">Weight</th>
                </tr>
        """

        for ticker, shares in positions.items():
            price = current_prices.get(ticker, 0)
            value = shares * price
            weight = weights.get(ticker, 0)
            portfolio_html += f"""
                <tr>
                    <td style="padding: 8px;">{ticker}</td>
                    <td style="padding: 8px;">{shares:.2f}</td>
                    <td style="padding: 8px;">${price:.2f}</td>
                    <td style="padding: 8px;">${value:,.2f}</td>
                    <td style="padding: 8px;">{weight:.1%}</td>
                </tr>
            """

        portfolio_html += """
            </table>
            <p><a href="/">← Back to Dashboard</a></p>
        </div>
        """

        dm.close()
        return portfolio_html

    except Exception as e:
        return f"Error: {e}", 500


@web_bp.route("/api-guide")
def api_guide() -> Union[str, Tuple[str, int]]:
    """API authentication and usage guide"""
    try:
        guide_html = """
        <!DOCTYPE html>
        <html>
        <head>
            <title>Traderrr API Guide - Authentication</title>
            <meta name="viewport" content="width=device-width, initial-scale=1">
            <style>
                * { margin: 0; padding: 0; box-sizing: border-box; }
                body {
                    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                    min-height: 100vh;
                    color: #333;
                    padding: 2rem;
                }
                .container {
                    max-width: 900px;
                    margin: 0 auto;
                    background: white;
                    border-radius: 16px;
                    padding: 2rem;
                    box-shadow: 0 20px 60px rgba(0, 0, 0, 0.3);
                }
                h1 {
                    color: #2d3748;
                    margin-bottom: 1.5rem;
                    border-bottom: 3px solid #3b82f6;
                    padding-bottom: 1rem;
                }
                h2 {
                    color: #374151;
                    margin-top: 2rem;
                    margin-bottom: 1rem;
                    font-size: 1.3rem;
                }
                h3 {
                    color: #4b5563;
                    margin-top: 1.5rem;
                    margin-bottom: 0.5rem;
                    font-size: 1.1rem;
                }
                p, li {
                    color: #555;
                    line-height: 1.6;
                    margin-bottom: 0.8rem;
                }
                ul {
                    margin-left: 2rem;
                    margin-bottom: 1rem;
                }
                code {
                    background: #f3f4f6;
                    padding: 0.2rem 0.5rem;
                    border-radius: 4px;
                    font-family: 'Courier New', monospace;
                    color: #d946ef;
                }
                .code-block {
                    background: #1f2937;
                    color: #e5e7eb;
                    padding: 1.5rem;
                    border-radius: 8px;
                    overflow-x: auto;
                    margin: 1rem 0;
                    border-left: 4px solid #3b82f6;
                }
                .code-block code {
                    background: none;
                    padding: 0;
                    color: inherit;
                    font-family: 'Monaco', 'Menlo', 'Ubuntu Mono', monospace;
                }
                .highlight {
                    background: #fef3c7;
                    padding: 1rem;
                    border-left: 4px solid #f59e0b;
                    margin: 1rem 0;
                    border-radius: 4px;
                }
                .success {
                    background: #ecfdf5;
                    padding: 1rem;
                    border-left: 4px solid #10b981;
                    margin: 1rem 0;
                    border-radius: 4px;
                    color: #047857;
                }
                .tabs {
                    display: flex;
                    gap: 1rem;
                    margin: 1.5rem 0;
                    border-bottom: 2px solid #e5e7eb;
                }
                .tab {
                    padding: 0.75rem 1.5rem;
                    background: none;
                    border: none;
                    cursor: pointer;
                    border-bottom: 3px solid transparent;
                    color: #6b7280;
                    font-weight: 500;
                    transition: all 0.2s;
                }
                .tab:hover {
                    color: #3b82f6;
                }
                .tab.active {
                    color: #3b82f6;
                    border-bottom-color: #3b82f6;
                }
                .tab-content {
                    display: none;
                }
                .tab-content.active {
                    display: block;
                }
                .nav-buttons {
                    display: flex;
                    gap: 1rem;
                    margin-top: 2rem;
                }
                a {
                    display: inline-block;
                    padding: 0.75rem 1.5rem;
                    background: #3b82f6;
                    color: white;
                    text-decoration: none;
                    border-radius: 8px;
                    transition: all 0.2s;
                    font-weight: 600;
                }
                a:hover {
                    background: #2563eb;
                    transform: translateY(-2px);
                    box-shadow: 0 4px 12px rgba(59, 130, 246, 0.3);
                }
                a.secondary {
                    background: #e5e7eb;
                    color: #374151;
                }
                a.secondary:hover {
                    background: #d1d5db;
                }
                .header-nav {
                    display: flex;
                    gap: 1.5rem;
                    margin-bottom: 2rem;
                    border-bottom: 1px solid #e5e7eb;
                    padding-bottom: 1rem;
                }
                .header-nav a {
                    display: inline;
                    padding: 0;
                    background: none;
                    color: #3b82f6;
                    font-weight: normal;
                }
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header-nav">
                    <a href="/">← Back to Dashboard</a>
                    <a href="/api/docs" style="color: #10b981;">→ Swagger UI</a>
                </div>

                <h1>🔐 Traderrr API Authentication Guide</h1>

                <p>All API endpoints require <strong>Bearer token authentication</strong> using a valid API key. This guide explains how to authenticate and use the API.</p>

                <h2>Quick Start</h2>
                <p>Every API request must include an Authorization header with your API key:</p>
                <div class="code-block"><code>Authorization: Bearer YOUR_API_KEY</code></div>

                <div class="highlight">
                    <strong>Development API Key:</strong><br/>
                    <code>test-api-key-67890</code>
                </div>

                <h2>Authentication Methods</h2>

                <div class="tabs">
                    <button class="tab active" onclick="switchTab('curl')">cURL</button>
                    <button class="tab" onclick="switchTab('python')">Python</button>
                    <button class="tab" onclick="switchTab('javascript')">JavaScript</button>
                </div>

                <div id="curl" class="tab-content active">
                    <h3>cURL Example</h3>
                    <div class="code-block"><code>curl -H "Authorization: Bearer test-api-key-67890" \\
  http://localhost:5000/api/portfolio</code></div>
                </div>

                <div id="python" class="tab-content">
                    <h3>Python Example</h3>
                    <div class="code-block"><code>import requests

headers = {
    'Authorization': 'Bearer test-api-key-67890',
    'Content-Type': 'application/json'
}

response = requests.get(
    'http://localhost:5000/api/portfolio',
    headers=headers
)

print(response.json())</code></div>
                </div>

                <div id="javascript" class="tab-content">
                    <h3>JavaScript/Fetch Example</h3>
                    <div class="code-block"><code>const apiKey = 'test-api-key-67890';

fetch('http://localhost:5000/api/portfolio', {
    headers: {
        'Authorization': `Bearer ${apiKey}`,
        'Content-Type': 'application/json'
    }
})
.then(response => response.json())
.then(data => console.log(data));</code></div>
                </div>

                <h2>Using Swagger UI with Authentication</h2>
                <p>To test endpoints interactively in the Swagger UI:</p>
                <ol>
                    <li>Go to <a href="/api/docs">/api/docs</a></li>
                    <li>Look for the <strong>"Authorize"</strong> button (🔒) in the top right</li>
                    <li>Click it and enter: <code>Bearer test-api-key-67890</code></li>
                    <li>Click "Authorize" to apply to all endpoints</li>
                    <li>Now test any endpoint directly in the UI</li>
                </ol>

                <h2>Error Responses</h2>
                <p>If authentication fails, you'll receive a 401 Unauthorized response:</p>
                <div class="code-block"><code>{
  "error": "Missing authorization header. Use: Authorization: Bearer &lt;api_key&gt;",
  "timestamp": "2024-11-27T10:30:45"
}</code></div>

                <div class="success">
                    <strong>Common Issues:</strong>
                    <ul>
                        <li><strong>Missing header:</strong> Make sure Authorization header is included</li>
                        <li><strong>Invalid key:</strong> Check that your API key is correct</li>
                        <li><strong>Wrong format:</strong> Must be "Bearer YOUR_KEY" (with space)</li>
                    </ul>
                </div>

                <h2>Available Endpoints</h2>
                <p>Visit the <a href="/api/docs">interactive Swagger documentation</a> to see all endpoints and test them directly.</p>

                <h2>Production Considerations</h2>
                <ul>
                    <li><strong>Never hardcode API keys</strong> in your source code</li>
                    <li><strong>Store keys securely</strong> in environment variables or secrets manager</li>
                    <li><strong>Use HTTPS</strong> in production to encrypt API keys in transit</li>
                    <li><strong>Rotate keys regularly</strong> for security</li>
                    <li><strong>Monitor usage</strong> to detect unauthorized access</li>
                </ul>

                <div class="nav-buttons">
                    <a href="/">← Back to Dashboard</a>
                    <a href="/api/docs">Go to Swagger UI →</a>
                </div>
            </div>

            <script>
                function switchTab(tabName) {
                    const contents = document.querySelectorAll('.tab-content');
                    contents.forEach(content => content.classList.remove('active'));
                    const tabs = document.querySelectorAll('.tab');
                    tabs.forEach(tab => tab.classList.remove('active'));
                    document.getElementById(tabName).classList.add('active');
                    event.target.classList.add('active');
                }
            </script>
        </body>
        </html>
        """
        return guide_html

    except Exception as e:
        logger.error(f"API guide error: {e}")
        return f"Error: {e}", 500


@web_bp.route("/performance")
def performance_page() -> Union[str, Tuple[str, int]]:
    """Performance analytics dashboard with charts"""
    try:
        import requests

        # Fetch performance metrics from API
        days = request.args.get("days", default=90, type=int)
        days = max(1, min(days, 365))

        try:
            # Setup authentication headers
            auth_headers = {
                "Authorization": f"Bearer {DEFAULT_API_KEY}",
                "Content-Type": "application/json",
            }

            # Get performance data
            perf_response = requests.get(
                "http://localhost:5000/api/portfolio-performance?limit=1000",
                headers=auth_headers,
            )
            perf_data = perf_response.json().get("performance", [])

            # Get summary
            summary_response = requests.get(
                f"http://localhost:5000/api/portfolio-performance/summary?days={days}",
                headers=auth_headers,
            )
            summary = summary_response.json().get("summary", {})

            # Get metrics
            metrics_response = requests.get(
                f"http://localhost:5000/api/portfolio-performance/metrics?days={days}",
                headers=auth_headers,
            )
            metrics = metrics_response.json().get("metrics", {})

        except Exception as e:
            logger.warning(f"Could not fetch performance data: {e}")
            perf_data = []
            summary = {}
            metrics = {}

        # Prepare chart data
        dates = [item.get("date", "") for item in perf_data]
        values = [item.get("portfolio_value", 0) for item in perf_data]
        returns = [
            item.get("daily_return", 0) * 100 for item in perf_data
        ]  # Convert to %
        volatilities = [
            item.get("volatility", 0) * 100 for item in perf_data
        ]  # Convert to %
        sharpe_ratios = [item.get("sharpe_ratio", 0) for item in perf_data]

        # Reverse for chronological order in charts
        dates.reverse()
        values.reverse()
        returns.reverse()
        volatilities.reverse()
        sharpe_ratios.reverse()

        performance_html = """
        <!DOCTYPE html>
        <html>
        <head>
            <title>Portfolio Performance Dashboard</title>
            <meta name="viewport" content="width=device-width, initial-scale=1">
            <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
            <style>
                * { margin: 0; padding: 0; box-sizing: border-box; }
                body {
                    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                    min-height: 100vh;
                    color: #333;
                }
                .header {
                    background: rgba(255, 255, 255, 0.95);
                    padding: 1.5rem 2rem;
                    border-bottom: 1px solid rgba(255, 255, 255, 0.2);
                    box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
                }
                .header h1 {
                    color: #2d3748;
                    font-size: 1.8rem;
                    font-weight: 700;
                    margin-bottom: 0.5rem;
                }
                .header .nav-links {
                    display: flex;
                    gap: 1rem;
                    margin-top: 1rem;
                }
                .header a {
                    color: #3b82f6;
                    text-decoration: none;
                    font-weight: 600;
                    padding: 0.5rem 1rem;
                    border-radius: 6px;
                    transition: all 0.2s;
                }
                .header a:hover {
                    background: #f0f4ff;
                    color: #1d4ed8;
                }
                .container {
                    max-width: 1400px;
                    margin: 0 auto;
                    padding: 2rem;
                }
                .card {
                    background: rgba(255, 255, 255, 0.95);
                    border-radius: 12px;
                    padding: 1.5rem;
                    margin: 1rem 0;
                    box-shadow: 0 4px 16px rgba(0, 0, 0, 0.1);
                    border: 1px solid rgba(255, 255, 255, 0.2);
                }
                .card h2 {
                    color: #2d3748;
                    margin-bottom: 1rem;
                    font-size: 1.3rem;
                    font-weight: 600;
                }
                .grid {
                    display: grid;
                    grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
                    gap: 1rem;
                    margin: 1rem 0;
                }
                .metric-card {
                    text-align: center;
                    padding: 1.5rem;
                    background: linear-gradient(135deg, #f8fafc 0%, #e2e8f0 100%);
                    border-radius: 10px;
                    border: 1px solid rgba(255, 255, 255, 0.3);
                }
                .metric-value {
                    font-size: 2em;
                    font-weight: 700;
                    margin-bottom: 0.3rem;
                }
                .metric-label {
                    font-size: 0.85rem;
                    color: #64748b;
                    font-weight: 500;
                }
                .positive { color: #059669; }
                .negative { color: #dc2626; }
                .neutral { color: #6366f1; }
                .chart-container {
                    position: relative;
                    height: 400px;
                    margin: 1rem 0;
                }
                .controls {
                    display: flex;
                    gap: 1rem;
                    margin: 1rem 0;
                    flex-wrap: wrap;
                }
                .controls select {
                    padding: 0.6rem 1rem;
                    border: 1px solid #e2e8f0;
                    border-radius: 6px;
                    font-size: 0.95rem;
                    cursor: pointer;
                }
                @media (max-width: 768px) {
                    .container { padding: 1rem; }
                    .grid { grid-template-columns: repeat(auto-fit, minmax(150px, 1fr)); }
                    .metric-value { font-size: 1.5em; }
                    .chart-container { height: 300px; }
                }
            </style>
        </head>
        <body>
            <div class="header">
                <h1>📊 Portfolio Performance Dashboard</h1>
                <div class="nav-links">
                    <a href="/">← Main Dashboard</a>
                    <a href="/portfolio">Portfolio</a>
                    <a href="/signals">Signals</a>
                </div>
            </div>
            <div class="container">
        """

        # Add summary metrics
        if summary:
            current_value = summary.get("current_value") or 0
            opening_value = summary.get("opening_value") or 0
            period_return = summary.get("period_return") or 0
            avg_volatility = summary.get("avg_volatility") or 0
            avg_sharpe = summary.get("avg_sharpe_ratio") or 0
            worst_drawdown = summary.get("worst_drawdown") or 0

            return_color = (
                "positive" if (period_return and period_return >= 0) else "negative"
            )
            sharpe_color = (
                "positive"
                if (avg_sharpe and avg_sharpe >= 1.0)
                else ("neutral" if (avg_sharpe and avg_sharpe >= 0) else "negative")
            )

            performance_html += f"""
                <div class="card">
                    <h2>Performance Summary (Last {days} Days)</h2>
                    <div class="grid">
                        <div class="metric-card">
                            <div class="metric-value">${current_value:,.0f}</div>
                            <div class="metric-label">Current Value</div>
                        </div>
                        <div class="metric-card">
                            <div class="metric-value {return_color}">{period_return:.2%}</div>
                            <div class="metric-label">Period Return</div>
                        </div>
                        <div class="metric-card">
                            <div class="metric-value">${opening_value:,.0f}</div>
                            <div class="metric-label">Opening Value</div>
                        </div>
                        <div class="metric-card">
                            <div class="metric-value neutral">{avg_volatility:.2%}</div>
                            <div class="metric-label">Avg Volatility</div>
                        </div>
                        <div class="metric-card">
                            <div class="metric-value {sharpe_color}">{avg_sharpe:.2f}</div>
                            <div class="metric-label">Avg Sharpe Ratio</div>
                        </div>
                        <div class="metric-card">
                            <div class="metric-value negative">{worst_drawdown:.2%}</div>
                            <div class="metric-label">Worst Drawdown</div>
                        </div>
                    </div>
                </div>
            """

        # Add metrics section
        if metrics:
            performance_html += f"""
                <div class="card">
                    <h2>Detailed Metrics ({metrics.get('period_days', 90)} Day Period)</h2>
                    <div class="grid">
                        <div class="metric-card">
                            <div class="metric-label">Records</div>
                            <div class="metric-value neutral">{metrics.get('records_count', 0)}</div>
                        </div>
                        <div class="metric-card">
                            <div class="metric-label">Total Return</div>
                            <div class="metric-value {'positive' if (metrics.get('total_return') and metrics.get('total_return') >= 0) else 'negative'}">{(metrics.get('total_return') or 0):.2%}</div>
                        </div>
                        <div class="metric-card">
                            <div class="metric-label">Min Value</div>
                            <div class="metric-value">${metrics.get('min_value', 0):,.0f}</div>
                        </div>
                        <div class="metric-card">
                            <div class="metric-label">Max Value</div>
                            <div class="metric-value">${metrics.get('max_value', 0):,.0f}</div>
                        </div>
                        <div class="metric-card">
                            <div class="metric-label">Max Volatility</div>
                            <div class="metric-value">{metrics.get('max_volatility', 0):.2%}</div>
                        </div>
                        <div class="metric-card">
                            <div class="metric-label">Min Volatility</div>
                            <div class="metric-value">{metrics.get('min_volatility', 0):.2%}</div>
                        </div>
                        <div class="metric-card">
                            <div class="metric-label">Best Sharpe</div>
                            <div class="metric-value positive">{metrics.get('best_sharpe_ratio', 0):.2f}</div>
                        </div>
                        <div class="metric-card">
                            <div class="metric-label">Worst Sharpe</div>
                            <div class="metric-value {'positive' if (metrics.get('worst_sharpe_ratio') and metrics.get('worst_sharpe_ratio') >= 0) else 'negative'}">{(metrics.get('worst_sharpe_ratio') or 0):.2f}</div>
                        </div>
                        <div class="metric-card">
                            <div class="metric-label">Avg Daily Return</div>
                            <div class="metric-value neutral">{metrics.get('avg_daily_return', 0):.4%}</div>
                        </div>
                    </div>
                </div>
            """

        # Add charts
        if perf_data:
            performance_html += f"""
                <div class="card">
                    <h2>Portfolio Value Over Time</h2>
                    <div class="chart-container">
                        <canvas id="valueChart"></canvas>
                    </div>
                </div>

                <div class="card">
                    <h2>Daily Returns</h2>
                    <div class="chart-container">
                        <canvas id="returnsChart"></canvas>
                    </div>
                </div>

                <div class="card">
                    <h2>Volatility & Sharpe Ratio Trends</h2>
                    <div class="chart-container">
                        <canvas id="volatilityChart"></canvas>
                    </div>
                </div>

                <script>
                    // Portfolio Value Chart
                    const valueCtx = document.getElementById('valueChart').getContext('2d');
                    new Chart(valueCtx, {{
                        type: 'line',
                        data: {{
                            labels: {json.dumps(dates[-50:])},  // Last 50 days
                            datasets: [{{
                                label: 'Portfolio Value',
                                data: {json.dumps([round(v, 2) for v in values[-50:]])},
                                borderColor: '#3b82f6',
                                backgroundColor: 'rgba(59, 130, 246, 0.1)',
                                tension: 0.4,
                                fill: true,
                                pointRadius: 3,
                                pointBackgroundColor: '#3b82f6'
                            }}]
                        }},
                        options: {{
                            responsive: true,
                            maintainAspectRatio: false,
                            plugins: {{
                                legend: {{ display: true, position: 'top' }}
                            }},
                            scales: {{
                                y: {{ beginAtZero: false }}
                            }}
                        }}
                    }});

                    // Daily Returns Chart
                    const returnsCtx = document.getElementById('returnsChart').getContext('2d');
                    new Chart(returnsCtx, {{
                        type: 'bar',
                        data: {{
                            labels: {json.dumps(dates[-50:])},  // Last 50 days
                            datasets: [{{
                                label: 'Daily Return (%)',
                                data: {json.dumps([round(r, 4) for r in returns[-50:]])},
                                backgroundColor: (ctx) => ctx.raw >= 0 ? '#10b981' : '#ef4444',
                                borderColor: (ctx) => ctx.raw >= 0 ? '#059669' : '#dc2626',
                                borderWidth: 1
                            }}]
                        }},
                        options: {{
                            responsive: true,
                            maintainAspectRatio: false,
                            plugins: {{
                                legend: {{ display: true, position: 'top' }}
                            }},
                            scales: {{
                                y: {{ ticks: {{ callback: (v) => v.toFixed(2) + '%' }} }}
                            }}
                        }}
                    }});

                    // Volatility & Sharpe Ratio Chart
                    const volatilityCtx = document.getElementById('volatilityChart').getContext('2d');
                    new Chart(volatilityCtx, {{
                        type: 'line',
                        data: {{
                            labels: {json.dumps(dates[-50:])},  // Last 50 days
                            datasets: [
                                {{
                                    label: 'Volatility (%)',
                                    data: {json.dumps([round(v, 4) for v in volatilities[-50:]])},
                                    borderColor: '#f59e0b',
                                    backgroundColor: 'rgba(245, 158, 11, 0.1)',
                                    tension: 0.4,
                                    fill: true,
                                    yAxisID: 'y',
                                    pointRadius: 2
                                }},
                                {{
                                    label: 'Sharpe Ratio',
                                    data: {json.dumps([round(s, 2) for s in sharpe_ratios[-50:]])},
                                    borderColor: '#8b5cf6',
                                    backgroundColor: 'rgba(139, 92, 246, 0.1)',
                                    tension: 0.4,
                                    fill: true,
                                    yAxisID: 'y1',
                                    pointRadius: 2
                                }}
                            ]
                        }},
                        options: {{
                            responsive: true,
                            maintainAspectRatio: false,
                            interaction: {{ mode: 'index', intersect: false }},
                            plugins: {{
                                legend: {{ display: true, position: 'top' }}
                            }},
                            scales: {{
                                y: {{ type: 'linear', display: true, position: 'left' }},
                                y1: {{ type: 'linear', display: true, position: 'right', grid: {{ drawOnChartArea: false }} }}
                            }}
                        }}
                    }});
                </script>
            """
        else:
            performance_html += """
                <div class="card">
                    <p style="text-align: center; color: #64748b;">
                        No performance data available yet. Run daily updates to generate performance metrics.
                    </p>
                </div>
            """

        performance_html += """
            </div>
        </body>
        </html>
        """

        return performance_html

    except Exception as e:
        logger.error(f"Performance dashboard error: {e}")
        return (
            f"""
        <div style="text-align: center; padding: 2rem; font-family: Arial, sans-serif;">
            <h1>🚨 Performance Dashboard Error</h1>
            <p>Error loading performance dashboard: {e}</p>
            <p><a href="/">Back to Dashboard</a></p>
        </div>
        """,
            500,
        )
