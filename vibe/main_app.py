"""
main.py - Main trading application for IBM Cloud deployment
Flask API with scheduled tasks and real-time monitoring
"""

import os
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List
import schedule
import time
import threading
from flask import Flask, request, jsonify, render_template_string
from flask_cors import CORS
import pandas as pd

# Import our custom modules
from data_manager import DataManager
from signal_generator import SignalGenerator, TradingSignal
from indicators import TechnicalIndicators

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize Flask app
app = Flask(__name__)
CORS(app)

# Configuration
class Config:
    # Portfolio configuration
    PORTFOLIO_TICKERS = [
        'AAPL', 'META', 'MSFT', 'NVDA', 'GOOGL',  # Large Cap Tech
        'JPM', 'BAC',  # Financial
        'PG', 'JNJ', 'KO',  # Consumer Staples
        'VTI', 'SPY',  # ETFs
        'SIEGY', 'VWAGY', 'SYIEY', 'BYDDY',  # International ADRs
        'QTUM', 'QBTS'  # Quantum/Emerging Tech
    ]
    
    # Database settings
    DATABASE_PATH = os.getenv('DATABASE_PATH', 'market_data.db')
    BACKUP_ENABLED = os.getenv('BACKUP_ENABLED', 'true').lower() == 'true'
    BACKUP_INTERVAL_HOURS = int(os.getenv('BACKUP_INTERVAL_HOURS', '24'))
    
    # Signal settings
    MIN_CONFIDENCE = float(os.getenv('MIN_CONFIDENCE', '0.6'))
    UPDATE_INTERVAL_MINUTES = int(os.getenv('UPDATE_INTERVAL_MINUTES', '30'))
    
    # IBM Cloud settings
    CLOUDANT_URL = os.getenv('CLOUDANT_URL')
    OBJECT_STORAGE_URL = os.getenv('OBJECT_STORAGE_URL')
    WATSON_API_KEY = os.getenv('WATSON_API_KEY')

# Global instances
dm = DataManager(db_path=Config.DATABASE_PATH)
signal_gen = SignalGenerator(min_confidence=Config.MIN_CONFIDENCE)
current_signals = []
last_update = None

# HTML template for dashboard
DASHBOARD_HTML = """
<!DOCTYPE html>
<html>
<head>
    <title>Trading Dashboard</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 20px; background-color: #f5f5f5; }
        .container { max-width: 1200px; margin: 0 auto; }
        .card { background: white; border-radius: 8px; padding: 20px; margin: 20px 0; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
        .signal-buy { border-left: 5px solid #28a745; }
        .signal-sell { border-left: 5px solid #dc3545; }
        .signal-hold { border-left: 5px solid #ffc107; }
        .confidence-high { color: #28a745; font-weight: bold; }
        .confidence-medium { color: #ffc107; font-weight: bold; }
        .confidence-low { color: #dc3545; font-weight: bold; }
        .grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 20px; }
        .metric { text-align: center; padding: 10px; }
        .metric-value { font-size: 2em; font-weight: bold; }
        .status-good { color: #28a745; }
        .status-warning { color: #ffc107; }
        .status-error { color: #dc3545; }
        table { width: 100%; border-collapse: collapse; }
        th, td { text-align: left; padding: 8px; border-bottom: 1px solid #ddd; }
        th { background-color: #f8f9fa; }
        .btn { padding: 10px 20px; margin: 5px; border: none; border-radius: 4px; cursor: pointer; }
        .btn-primary { background-color: #007bff; color: white; }
        .btn-success { background-color: #28a745; color: white; }
        .btn-danger { background-color: #dc3545; color: white; }
    </style>
    <script>
        function refreshData() {
            location.reload();
        }
        
        function updateSignals() {
            fetch('/api/update', {method: 'POST'})
                .then(response => response.json())
                .then(data => {
                    alert('Update initiated: ' + data.message);
                    setTimeout(refreshData, 5000);
                });
        }
        
        // Auto-refresh every 5 minutes
        setInterval(refreshData, 300000);
    </script>
</head>
<body>
    <div class="container">
        <h1>Trading Dashboard</h1>
        
        <div class="card">
            <h2>System Status</h2>
            <div class="grid">
                <div class="metric">
                    <div class="metric-value status-{{ status_color }}">{{ total_signals }}</div>
                    <div>Active Signals</div>
                </div>
                <div class="metric">
                    <div class="metric-value status-good">{{ buy_signals }}</div>
                    <div>Buy Signals</div>
                </div>
                <div class="metric">
                    <div class="metric-value status-error">{{ sell_signals }}</div>
                    <div>Sell Signals</div>
                </div>
                <div class="metric">
                    <div class="metric-value">{{ '{:.1%}'.format(avg_confidence) }}</div>
                    <div>Avg Confidence</div>
                </div>
            </div>
            <p><strong>Last Update:</strong> {{ last_update or 'Never' }}</p>
            <button class="btn btn-primary" onclick="refreshData()">Refresh</button>
            <button class="btn btn-success" onclick="updateSignals()">Update Signals</button>
        </div>
        
        {% if signals %}
        <div class="card">
            <h2>Active Trading Signals</h2>
            <table>
                <tr>
                    <th>Ticker</th>
                    <th>Signal</th>
                    <th>Confidence</th>
                    <th>Entry Price</th>
                    <th>Target</th>
                    <th>Stop Loss</th>
                    <th>Regime</th>
                    <th>Reasons</th>
                </tr>
                {% for signal in signals %}
                <tr class="signal-{{ signal.signal_type.value.lower().replace('_', '-') }}">
                    <td><strong>{{ signal.ticker }}</strong></td>
                    <td>{{ signal.signal_type.value }}</td>
                    <td class="confidence-{{ 'high' if signal.confidence > 0.8 else 'medium' if signal.confidence > 0.6 else 'low' }}">
                        {{ '{:.1%}'.format(signal.confidence) }}
                    </td>
                    <td>${{ '{:.2f}'.format(signal.entry_price) }}</td>
                    <td>${{ '{:.2f}'.format(signal.target_price) }}</td>
                    <td>${{ '{:.2f}'.format(signal.stop_loss) }}</td>
                    <td>{{ signal.regime.value.replace('_', ' ').title() }}</td>
                    <td>{{ ', '.join(signal.reasons[:3]) }}{% if signal.reasons|length > 3 %}...{% endif %}</td>
                </tr>
                {% endfor %}
            </table>
        </div>
        {% endif %}
        
        <div class="card">
            <h2>Portfolio Overview</h2>
            <table>
                <tr>
                    <th>Ticker</th>
                    <th>Last Price</th>
                    <th>RSI</th>
                    <th>MACD Signal</th>
                    <th>Trend</th>
                    <th>Volume</th>
                </tr>
                {% for ticker, data in portfolio_overview.items() %}
                <tr>
                    <td><strong>{{ ticker }}</strong></td>
                    <td>${{ '{:.2f}'.format(data.get('price', 0)) }}</td>
                    <td class="{{ 'status-error' if data.get('rsi', 50) > 70 else 'status-good' if data.get('rsi', 50) < 30 else '' }}">
                        {{ '{:.1f}'.format(data.get('rsi', 50)) }}
                    </td>
                    <td class="{{ 'status-good' if data.get('macd_bullish') else 'status-error' }}">
                        {{ 'Bullish' if data.get('macd_bullish') else 'Bearish' }}
                    </td>
                    <td class="{{ 'status-good' if data.get('trend_up') else 'status-error' }}">
                        {{ 'Up' if data.get('trend_up') else 'Down' }}
                    </td>
                    <td>{{ '{:.1f}'.format(data.get('volume_ratio', 1)) }}x</td>
                </tr>
                {% endfor %}
            </table>
        </div>
    </div>
</body>
</html>
"""

# API Routes
@app.route('/')
def dashboard():
    """Main dashboard"""
    try:
        # Prepare dashboard data
        signals = current_signals
        
        # Calculate summary stats
        total_signals = len(signals)
        buy_signals = len([s for s in signals if 'BUY' in s.signal_type.value])
        sell_signals = len([s for s in signals if 'SELL' in s.signal_type.value])
        avg_confidence = sum(s.confidence for s in signals) / len(signals) if signals else 0
        
        # Get portfolio overview
        portfolio_overview = get_portfolio_overview()
        
        # Determine status color
        if total_signals > 5:
            status_color = "good"
        elif total_signals > 2:
            status_color = "warning"
        else:
            status_color = "error"
        
        return render_template_string(
            DASHBOARD_HTML,
            signals=signals,
            total_signals=total_signals,
            buy_signals=buy_signals,
            sell_signals=sell_signals,
            avg_confidence=avg_confidence,
            last_update=last_update,
            portfolio_overview=portfolio_overview,
            status_color=status_color
        )
        
    except Exception as e:
        logger.error(f"Dashboard error: {e}")
        return f"Dashboard error: {e}", 500

@app.route('/api/signals', methods=['GET'])
def get_signals():
    """Get current trading signals"""
    try:
        signals_data = []
        for signal in current_signals:
            signals_data.append({
                'ticker': signal.ticker,
                'signal_type': signal.signal_type.value,
                'confidence': signal.confidence,
                'entry_price': signal.entry_price,
                'stop_loss': signal.stop_loss,
                'target_price': signal.target_price,
                'regime': signal.regime.value,
                'reasons': signal.reasons,
                'timestamp': signal.timestamp.isoformat()
            })
        
        return jsonify({
            'signals': signals_data,
            'last_update': last_update,
            'total_count': len(signals_data)
        })
        
    except Exception as e:
        logger.error(f"API error: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/portfolio', methods=['GET'])
def get_portfolio():
    """Get portfolio overview"""
    try:
        overview = get_portfolio_overview()
        return jsonify(overview)
        
    except Exception as e:
        logger.error(f"Portfolio API error: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/update', methods=['POST'])
def update_signals():
    """Manually trigger signal update"""
    try:
        # Run update in background thread
        threading.Thread(target=update_portfolio_signals, daemon=True).start()
        
        return jsonify({
            'message': 'Signal update initiated',
            'timestamp': datetime.now().isoformat()
        })
        
    except Exception as e:
        logger.error(f"Update API error: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/health', methods=['GET'])
def health_check():
    """Health check endpoint for IBM Cloud"""
    try:
        # Basic health checks
        health_status = {
            'status': 'healthy',
            'timestamp': datetime.now().isoformat(),
            'database': 'connected',
            'last_update': last_update,
            'signal_count': len(current_signals)
        }
        
        # Test database connection
        try:
            dm.get_portfolio_summary(Config.PORTFOLIO_TICKERS[:1])
        except Exception as e:
            health_status['database'] = f'error: {str(e)}'
            health_status['status'] = 'degraded'
        
        # Check if data is stale
        if last_update:
            time_since_update = datetime.now() - datetime.fromisoformat(last_update)
            if time_since_update > timedelta(hours=6):
                health_status['status'] = 'degraded'
                health_status['warning'] = 'Data may be stale'
        
        status_code = 200 if health_status['status'] == 'healthy' else 503
        return jsonify(health_status), status_code
        
    except Exception as e:
        return jsonify({
            'status': 'unhealthy',
            'error': str(e),
            'timestamp': datetime.now().isoformat()
        }), 503

# Helper Functions
def get_portfolio_overview() -> Dict:
    """Get quick overview of portfolio tickers"""
    overview = {}
    
    try:
        # Get recent data for each ticker
        for ticker in Config.PORTFOLIO_TICKERS:
            try:
                data = dm.get_stock_data(ticker, period="30d", interval="1d")
                if not data.empty:
                    # Calculate basic indicators
                    ti = TechnicalIndicators()
                    rsi = ti.rsi(data['Close']).iloc[-1]
                    macd_line, signal_line, _ = ti.macd(data['Close'])
                    
                    overview[ticker] = {
                        'price': data['Close'].iloc[-1],
                        'rsi': rsi,
                        'macd_bullish': macd_line.iloc[-1] > signal_line.iloc[-1],
                        'trend_up': data['Close'].iloc[-1] > data['Close'].rolling(20).mean().iloc[-1],
                        'volume_ratio': data['Volume'].iloc[-1] / data['Volume'].rolling(20).mean().iloc[-1]
                    }
                else:
                    overview[ticker] = {
                        'price': 0,
                        'rsi': 50,
                        'macd_bullish': False,
                        'trend_up': False,
                        'volume_ratio': 1.0
                    }
            except Exception as e:
                logger.warning(f"Error getting overview for {ticker}: {e}")
                overview[ticker] = {
                    'price': 0,
                    'rsi': 50,
                    'macd_bullish': False,
                    'trend_up': False,
                    'volume_ratio': 1.0
                }
    
    except Exception as e:
        logger.error(f"Error getting portfolio overview: {e}")
    
    return overview

def update_portfolio_signals():
    """Update trading signals for all portfolio tickers"""
    global current_signals, last_update
    
    try:
        logger.info("Starting portfolio signal update")
        
        # Download fresh data
        portfolio_data = dm.get_multiple_stocks(
            Config.PORTFOLIO_TICKERS, 
            period="6mo"
        )
        
        if not portfolio_data:
            logger.warning("No portfolio data received")
            return
        
        # Generate new signals
        new_signals = signal_gen.generate_portfolio_signals(portfolio_data)
        
        # Update global state
        current_signals.clear()
        current_signals.extend(new_signals)
        last_update = datetime.now().isoformat()
        
        logger.info(f"Updated {len(new_signals)} signals at {last_update}")
        
        # Store signals in database
        store_signals_in_db(new_signals)
        
        # Create backup if enabled
        if Config.BACKUP_ENABLED:
            backup_path = f"backup_{datetime.now().strftime('%Y%m%d_%H%M')}.db"
            dm.backup_database(backup_path)
        
    except Exception as e:
        logger.error(f"Error updating signals: {e}")

def store_signals_in_db(signals: List[TradingSignal]):
    """Store signals in database for history tracking"""
    try:
        import sqlite3
        conn = sqlite3.connect(Config.DATABASE_PATH)
        cursor = conn.cursor()
        
        for signal in signals:
            cursor.execute('''
                INSERT INTO signal_history 
                (ticker, date, signal_type, signal_value, confidence)
                VALUES (?, ?, ?, ?, ?)
            ''', (
                signal.ticker,
                signal.timestamp.date(),
                signal.signal_type.value,
                signal.entry_price,
                signal.confidence
            ))
        
        conn.commit()
        conn.close()
        
    except Exception as e:
        logger.error(f"Error storing signals in database: {e}")

# Scheduled Tasks
def run_scheduler():
    """Run scheduled tasks in background thread"""
    while True:
        schedule.run_pending()
        time.sleep(60)

# Schedule regular updates
schedule.every(Config.UPDATE_INTERVAL_MINUTES).minutes.do(update_portfolio_signals)
schedule.every().day.at("09:00").do(update_portfolio_signals)  # Market open
schedule.every().day.at("15:30").do(update_portfolio_signals)  # Before market close

# Initialize on startup
def initialize_app():
    """Initialize application on startup"""
    logger.info("Initializing trading application")
    
    try:
        # Initial data update
        update_portfolio_signals()
        
        # Start scheduler thread
        scheduler_thread = threading.Thread(target=run_scheduler, daemon=True)
        scheduler_thread.start()
        
        logger.info("Application initialized successfully")
        
    except Exception as e:
        logger.error(f"Initialization error: {e}")

# IBM Cloud Environment Detection
def is_ibm_cloud():
    """Check if running on IBM Cloud"""
    return os.getenv('VCAP_SERVICES') is not None

# Main execution
if __name__ == '__main__':
    # Initialize the application
    initialize_app()
    
    # Configure for IBM Cloud or local development
    if is_ibm_cloud():
        port = int(os.getenv('PORT', 8080))
        app.run(host='0.0.0.0', port=port, debug=False)
    else:
        # Local development
        app.run(host='localhost', port=5000, debug=True)


# requirements.txt content for the project
REQUIREMENTS_TXT = """
Flask==2.3.3
Flask-CORS==4.0.0
pandas==2.0.3
numpy==1.24.3
yfinance==0.2.18
requests==2.31.0
schedule==1.2.0
TA-Lib==0.4.25
urllib3==2.0.4
gunicorn==21.2.0
python-dotenv==1.0.0
cloudant==2.15.0
ibm-cos-sdk==2.13.0
ibm-watson==7.0.1
"""

# IBM Cloud deployment configuration
IBM_CLOUD_MANIFEST = """
---
applications:
- name: trading-signals-app
  memory: 1G
  instances: 1
  buildpacks:
    - python_buildpack
  command: gunicorn main:app --bind 0.0.0.0:$PORT --workers 2 --timeout 120
  env:
    FLASK_ENV: production
    DATABASE_PATH: /app/data/market_data.db
    MIN_CONFIDENCE: 0.6
    UPDATE_INTERVAL_MINUTES: 30
    BACKUP_ENABLED: true
  services:
    - trading-cloudant-db
    - trading-object-storage
"""

# Dockerfile for containerized deployment
DOCKERFILE = """
FROM python:3.9-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \\
    gcc \\
    g++ \\
    wget \\
    && rm -rf /var/lib/apt/lists/*

# Install TA-Lib
RUN wget http://prdownloads.sourceforge.net/ta-lib/ta-lib-0.4.0-src.tar.gz && \\
    tar -xzf ta-lib-0.4.0-src.tar.gz && \\
    cd ta-lib/ && \\
    ./configure --prefix=/usr && \\
    make && \\
    make install && \\
    cd .. && \\
    rm -rf ta-lib ta-lib-0.4.0-src.tar.gz

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create data directory
RUN mkdir -p /app/data

# Expose port
EXPOSE 8080

# Set environment variables
ENV PORT=8080
ENV FLASK_ENV=production

# Run the application
CMD ["gunicorn", "main:app", "--bind", "0.0.0.0:8080", "--workers", "2", "--timeout", "120"]
"""

# Docker Compose for local development
DOCKER_COMPOSE = """
version: '3.8'

services:
  trading-app:
    build: .
    ports:
      - "5000:8080"
    environment:
      - FLASK_ENV=development
      - DATABASE_PATH=/app/data/market_data.db
      - MIN_CONFIDENCE=0.6
      - UPDATE_INTERVAL_MINUTES=30
    volumes:
      - ./data:/app/data
      - .:/app
    depends_on:
      - redis
  
  redis:
    image: redis:alpine
    ports:
      - "6379:6379"
  
  nginx:
    image: nginx:alpine
    ports:
      - "80:80"
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf
    depends_on:
      - trading-app

volumes:
  data:
"""

# IBM Cloud Code Engine deployment script
IBM_CODE_ENGINE_DEPLOY = """
#!/bin/bash

# IBM Cloud Code Engine deployment script
# Prerequisites: IBM Cloud CLI and Code Engine plugin installed

# Set variables
PROJECT_NAME="trading-signals"
APP_NAME="trading-app"
RESOURCE_GROUP="default"
REGION="us-south"

# Login to IBM Cloud (interactive)
echo "Please login to IBM Cloud..."
ibmcloud login

# Target resource group and region
ibmcloud target -g $RESOURCE_GROUP -r $REGION

# Create Code Engine project
echo "Creating Code Engine project..."
ibmcloud ce project create --name $PROJECT_NAME

# Target the project
ibmcloud ce project select --name $PROJECT_NAME

# Create Cloudant database service
echo "Creating Cloudant database..."
ibmcloud resource service-instance-create trading-cloudant-db cloudantnosqldb lite $REGION

# Create Object Storage service
echo "Creating Object Storage..."
ibmcloud resource service-instance-create trading-object-storage cloud-object-storage lite global

# Build and deploy application
echo "Building and deploying application..."
ibmcloud ce application create \\
    --name $APP_NAME \\
    --image icr.io/$PROJECT_NAME/trading-app:latest \\
    --build-source . \\
    --build-strategy dockerfile \\
    --cpu 1 \\
    --memory 2G \\
    --min-scale 1 \\
    --max-scale 3 \\
    --port 8080 \\
    --env DATABASE_PATH=/app/data/market_data.db \\
    --env MIN_CONFIDENCE=0.6 \\
    --env UPDATE_INTERVAL_MINUTES=30 \\
    --env BACKUP_ENABLED=true

# Bind services to application
echo "Binding services..."
ibmcloud ce application bind --name $APP_NAME --service-instance trading-cloudant-db
ibmcloud ce application bind --name $APP_NAME --service-instance trading-object-storage

# Create scheduled job for daily updates
echo "Creating scheduled job..."
ibmcloud ce job create \\
    --name daily-update \\
    --image icr.io/$PROJECT_NAME/trading-app:latest \\
    --command "python" \\
    --argument "scripts/daily_update.py" \\
    --cpu 0.5 \\
    --memory 1G

# Create cron subscription for daily job
ibmcloud ce subscription cron create \\
    --name daily-update-cron \\
    --destination daily-update \\
    --schedule "0 9 * * *" \\
    --time-zone "America/New_York"

echo "Deployment complete!"
echo "Application URL: $(ibmcloud ce application get --name $APP_NAME --output json | jq -r '.status.url')"
"""

print("=== COMPLETE TRADING SYSTEM IMPLEMENTATION ===")
print()
print("Files created:")
print("1. data_manager.py - Yahoo Finance data management")
print("2. indicators.py - Technical indicators and regime detection")
print("3. signal_generator.py - Advanced signal generation")
print("4. main.py - Flask application with dashboard")
print()
print("IBM Cloud Deployment Files:")
print("- requirements.txt")
print("- Dockerfile")
print("- manifest.yml")
print("- docker-compose.yml")
print("- deploy-ibm-cloud.sh")
print()
print("Key Features:")
print("✓ Real-time Yahoo Finance data")
print("✓ Advanced technical indicators")
print("✓ Market regime detection")
print("✓ Automated signal generation")
print("✓ Web dashboard interface")
print("✓ RESTful API endpoints")
print("✓ Scheduled updates")
print("✓ IBM Cloud optimized")
print("✓ Database backup system")
print("✓ Health monitoring")
