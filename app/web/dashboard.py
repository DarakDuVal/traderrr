"""
app/web/dashboard.py - Web dashboard interface
"""

from flask import Blueprint, render_template_string, request, jsonify
import requests
import json
import logging
import pandas as pd
from datetime import datetime

web_bp = Blueprint("web", __name__)
logger = logging.getLogger(__name__)

# Dashboard HTML template
DASHBOARD_HTML = """
<!DOCTYPE html>
<html>
<head>
    <title>Trading Dashboard</title>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { 
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; 
            margin: 0; 
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            color: #333;
        }
        .header {
            background: rgba(255, 255, 255, 0.95);
            backdrop-filter: blur(10px);
            border-bottom: 1px solid rgba(255, 255, 255, 0.2);
            padding: 1rem 2rem;
            position: sticky;
            top: 0;
            z-index: 100;
        }
        .header h1 {
            color: #2d3748;
            font-size: 1.8rem;
            font-weight: 700;
        }
        .container { 
            max-width: 1400px; 
            margin: 0 auto; 
            padding: 2rem;
        }
        .card { 
            background: rgba(255, 255, 255, 0.95); 
            backdrop-filter: blur(10px);
            border-radius: 16px; 
            padding: 1.5rem; 
            margin: 1rem 0; 
            box-shadow: 0 8px 32px rgba(0, 0, 0, 0.1);
            border: 1px solid rgba(255, 255, 255, 0.2);
            transition: transform 0.2s ease, box-shadow 0.2s ease;
        }
        .card:hover {
            transform: translateY(-2px);
            box-shadow: 0 12px 40px rgba(0, 0, 0, 0.15);
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
        .metric { 
            text-align: center; 
            padding: 1rem;
            background: linear-gradient(135deg, #f8fafc 0%, #e2e8f0 100%);
            border-radius: 12px;
            border: 1px solid rgba(255, 255, 255, 0.3);
        }
        .metric-value { 
            font-size: 2.2em; 
            font-weight: 700; 
            margin-bottom: 0.3rem;
        }
        .metric-label {
            font-size: 0.9rem;
            color: #64748b;
            font-weight: 500;
        }
        .status-good { color: #059669; }
        .status-warning { color: #d97706; }
        .status-error { color: #dc2626; }
        .status-neutral { color: #6366f1; }

        table { 
            width: 100%; 
            border-collapse: collapse; 
            margin-top: 1rem;
        }
        th, td { 
            text-align: left; 
            padding: 0.75rem; 
            border-bottom: 1px solid #e2e8f0; 
        }
        th { 
            background: linear-gradient(135deg, #f1f5f9 0%, #e2e8f0 100%);
            font-weight: 600;
            color: #374151;
        }
        tr:hover { background-color: #f8fafc; }

        .signal-row {
            border-left: 4px solid transparent;
            transition: all 0.2s ease;
        }
        .signal-buy { border-left-color: #059669; }
        .signal-sell { border-left-color: #dc2626; }
        .signal-strong-buy { border-left-color: #047857; background-color: #ecfdf5; }
        .signal-strong-sell { border-left-color: #b91c1c; background-color: #fef2f2; }

        .confidence-high { 
            color: #059669; 
            font-weight: 600;
            background: #ecfdf5;
            padding: 0.2rem 0.5rem;
            border-radius: 6px;
        }
        .confidence-medium { 
            color: #d97706; 
            font-weight: 600;
            background: #fffbeb;
            padding: 0.2rem 0.5rem;
            border-radius: 6px;
        }
        .confidence-low { 
            color: #dc2626; 
            font-weight: 600;
            background: #fef2f2;
            padding: 0.2rem 0.5rem;
            border-radius: 6px;
        }

        .btn { 
            padding: 0.75rem 1.5rem; 
            margin: 0.25rem; 
            border: none; 
            border-radius: 8px; 
            cursor: pointer; 
            font-weight: 600;
            transition: all 0.2s ease;
            text-decoration: none;
            display: inline-block;
        }
        .btn:hover { transform: translateY(-1px); }
        .btn-primary { 
            background: linear-gradient(135deg, #3b82f6 0%, #1d4ed8 100%); 
            color: white; 
            box-shadow: 0 4px 12px rgba(59, 130, 246, 0.3);
        }
        .btn-primary:hover { box-shadow: 0 6px 16px rgba(59, 130, 246, 0.4); }
        .btn-success { 
            background: linear-gradient(135deg, #10b981 0%, #047857 100%); 
            color: white; 
            box-shadow: 0 4px 12px rgba(16, 185, 129, 0.3);
        }
        .btn-success:hover { box-shadow: 0 6px 16px rgba(16, 185, 129, 0.4); }
        .btn-warning { 
            background: linear-gradient(135deg, #f59e0b 0%, #d97706 100%); 
            color: white; 
            box-shadow: 0 4px 12px rgba(245, 158, 11, 0.3);
        }

        .loading {
            display: inline-block;
            width: 20px;
            height: 20px;
            border: 3px solid rgba(255,255,255,.3);
            border-radius: 50%;
            border-top-color: #fff;
            animation: spin 1s ease-in-out infinite;
        }

        @keyframes spin {
            to { transform: rotate(360deg); }
        }

        .alert {
            padding: 1rem;
            border-radius: 8px;
            margin: 1rem 0;
            border-left: 4px solid;
        }
        .alert-info {
            background: #eff6ff;
            border-color: #3b82f6;
            color: #1e40af;
        }
        .alert-success {
            background: #ecfdf5;
            border-color: #10b981;
            color: #047857;
        }
        .alert-warning {
            background: #fffbeb;
            border-color: #f59e0b;
            color: #92400e;
        }

        .ticker-tag {
            background: linear-gradient(135deg, #6366f1 0%, #4f46e5 100%);
            color: white;
            padding: 0.2rem 0.6rem;
            border-radius: 6px;
            font-size: 0.8rem;
            font-weight: 600;
        }

        .last-update {
            font-size: 0.85rem;
            color: #64748b;
            margin-top: 0.5rem;
        }

        .form-group {
            margin: 1rem 0;
            display: flex;
            gap: 0.5rem;
            align-items: flex-end;
            flex-wrap: wrap;
        }

        .form-group label {
            font-weight: 600;
            color: #374151;
            min-width: 80px;
        }

        .form-group input {
            padding: 0.6rem;
            border: 1px solid #e2e8f0;
            border-radius: 6px;
            font-size: 0.95rem;
            min-width: 120px;
        }

        .form-group input:focus {
            outline: none;
            border-color: #3b82f6;
            box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.1);
        }

        .position-row {
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 1rem;
            background: #f8fafc;
            border-radius: 8px;
            margin: 0.5rem 0;
            border: 1px solid #e2e8f0;
        }

        .position-info {
            flex: 1;
        }

        .position-ticker {
            font-weight: 700;
            color: #2d3748;
            font-size: 1.1rem;
        }

        .position-details {
            font-size: 0.9rem;
            color: #64748b;
            margin-top: 0.25rem;
        }

        .position-value {
            font-weight: 600;
            color: #059669;
            margin: 0 1rem;
            min-width: 120px;
            text-align: right;
        }

        .position-actions {
            display: flex;
            gap: 0.5rem;
        }

        .btn-sm {
            padding: 0.5rem 1rem;
            font-size: 0.85rem;
            min-width: auto;
        }

        .btn-danger {
            background: linear-gradient(135deg, #ef4444 0%, #dc2626 100%);
            color: white;
        }

        .modal {
            display: none;
            position: fixed;
            z-index: 1000;
            left: 0;
            top: 0;
            width: 100%;
            height: 100%;
            background-color: rgba(0, 0, 0, 0.5);
        }

        .modal-content {
            background-color: white;
            margin: 5% auto;
            padding: 2rem;
            border-radius: 12px;
            width: 90%;
            max-width: 400px;
            box-shadow: 0 20px 60px rgba(0, 0, 0, 0.3);
        }

        .modal-header {
            font-size: 1.3rem;
            font-weight: 600;
            margin-bottom: 1rem;
            color: #2d3748;
        }

        .modal-footer {
            display: flex;
            gap: 0.5rem;
            justify-content: flex-end;
            margin-top: 1.5rem;
        }

        .close-modal {
            color: #6b7280;
            float: right;
            font-size: 1.5rem;
            font-weight: 700;
            cursor: pointer;
        }

        .close-modal:hover {
            color: #374151;
        }

        @media (max-width: 768px) {
            .container { padding: 1rem; }
            .grid { grid-template-columns: repeat(auto-fit, minmax(150px, 1fr)); }
            .metric-value { font-size: 1.8em; }
            table { font-size: 0.9rem; }
            .btn { padding: 0.6rem 1.2rem; }
            .position-row { flex-direction: column; align-items: flex-start; }
            .position-value { margin: 0.5rem 0; }
        }
    </style>
    <script>
        let isUpdating = false;

        function showLoading() {
            document.getElementById('refreshBtn').innerHTML = '<span class="loading"></span> Refreshing...';
            document.getElementById('updateBtn').innerHTML = '<span class="loading"></span> Updating...';
        }

        function hideLoading() {
            document.getElementById('refreshBtn').innerHTML = '🔄 Refresh';
            document.getElementById('updateBtn').innerHTML = '📊 Update Signals';
        }

        function refreshData() {
            if (isUpdating) return;
            showLoading();
            setTimeout(() => {
                location.reload();
            }, 500);
        }

        function updateSignals() {
            if (isUpdating) return;
            isUpdating = true;
            showLoading();

            fetch('/api/update', {method: 'POST'})
                .then(response => response.json())
                .then(data => {
                    if (data.error) {
                        alert('Update failed: ' + data.error);
                    } else {
                        showAlert('Update initiated successfully! Refreshing in 5 seconds...', 'success');
                        setTimeout(refreshData, 5000);
                    }
                })
                .catch(error => {
                    alert('Update failed: ' + error.message);
                })
                .finally(() => {
                    isUpdating = false;
                    hideLoading();
                });
        }

        function showAlert(message, type = 'info') {
            const alertDiv = document.createElement('div');
            alertDiv.className = `alert alert-${type}`;
            alertDiv.textContent = message;

            const container = document.querySelector('.container');
            container.insertBefore(alertDiv, container.firstChild);

            setTimeout(() => {
                alertDiv.remove();
            }, 5000);
        }

        // Auto-refresh every 5 minutes
        setInterval(refreshData, 300000);

        // Portfolio Management Functions
        function openAddPositionModal() {
            document.getElementById('addPositionModal').style.display = 'block';
        }

        function closeModal(modalId) {
            document.getElementById(modalId).style.display = 'none';
        }

        function addPosition() {
            const ticker = document.getElementById('newTicker').value.toUpperCase().trim();
            const shares = parseFloat(document.getElementById('newShares').value);

            if (!ticker || isNaN(shares) || shares < 0) {
                showAlert('Please enter a valid ticker and positive number of shares', 'warning');
                return;
            }

            fetch('/api/portfolio/positions', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ ticker, shares })
            })
            .then(response => response.json())
            .then(data => {
                if (data.error) {
                    showAlert('Error: ' + data.error + (data.issues ? ' - ' + data.issues.join(', ') : ''), 'warning');
                } else {
                    showAlert(`Position ${ticker} added successfully (${shares} shares)!`, 'success');
                    closeModal('addPositionModal');
                    document.getElementById('newTicker').value = '';
                    document.getElementById('newShares').value = '';
                    loadPortfolioPositions();
                }
            })
            .catch(error => showAlert('Error adding position: ' + error.message, 'warning'));
        }

        function updatePosition(ticker) {
            const shares = prompt(`Enter new number of shares for ${ticker}:`, '');
            if (shares === null) return;

            const sharesNum = parseFloat(shares);
            if (isNaN(sharesNum) || sharesNum < 0) {
                showAlert('Please enter a valid positive number of shares', 'warning');
                return;
            }

            fetch(`/api/portfolio/positions/${ticker}`, {
                method: 'PUT',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ shares: sharesNum })
            })
            .then(response => response.json())
            .then(data => {
                if (data.error) {
                    showAlert('Error: ' + data.error, 'warning');
                } else {
                    showAlert(`Position ${ticker} updated to ${sharesNum} shares!`, 'success');
                    loadPortfolioPositions();
                }
            })
            .catch(error => showAlert('Error updating position: ' + error.message, 'warning'));
        }

        function removePosition(ticker) {
            if (!confirm(`Are you sure you want to remove ${ticker} from your portfolio?`)) {
                return;
            }

            fetch(`/api/portfolio/positions/${ticker}`, {
                method: 'DELETE',
                headers: { 'Content-Type': 'application/json' }
            })
            .then(response => response.json())
            .then(data => {
                if (data.error) {
                    showAlert('Error: ' + data.error, 'warning');
                } else {
                    showAlert(`Position ${ticker} removed successfully!`, 'success');
                    loadPortfolioPositions();
                }
            })
            .catch(error => showAlert('Error removing position: ' + error.message, 'warning'));
        }

        function loadPortfolioPositions() {
            fetch('/api/portfolio/positions')
            .then(response => response.json())
            .then(data => {
                const container = document.getElementById('positionsContainer');
                if (!data.positions || data.positions.length === 0) {
                    container.innerHTML = '<div class="alert alert-info">No positions in portfolio. Add one to get started!</div>';
                    document.getElementById('totalPortfolioValue').textContent = '$0.00';
                    return;
                }

                let html = '';
                data.positions.forEach(position => {
                    html += `
                    <div class="position-row">
                        <div class="position-info">
                            <div class="position-ticker">${position.ticker}</div>
                            <div class="position-details">
                                ${position.shares} shares @ $${position.current_price.toFixed(2)}
                            </div>
                        </div>
                        <div class="position-value">
                            $${position.position_value.toFixed(2)}
                        </div>
                        <div class="position-actions">
                            <button onclick="updatePosition('${position.ticker}')" class="btn btn-primary btn-sm">Edit</button>
                            <button onclick="removePosition('${position.ticker}')" class="btn btn-danger btn-sm">Remove</button>
                        </div>
                    </div>
                    `;
                });
                container.innerHTML = html;
                document.getElementById('totalPortfolioValue').textContent = '$' + data.total_value.toFixed(2);
            })
            .catch(error => {
                console.error('Error loading positions:', error);
                document.getElementById('positionsContainer').innerHTML = '<div class="alert alert-warning">Error loading positions</div>';
            });
        }

        // Add loading states on page load
        document.addEventListener('DOMContentLoaded', function() {
            hideLoading();
            loadPortfolioPositions();
        });

        // Close modals when clicking outside
        window.onclick = function(event) {
            const modal = document.getElementById('addPositionModal');
            if (event.target === modal) {
                modal.style.display = 'none';
            }
        };
    </script>
</head>
<body>
    <div class="header">
        <h1>🚀 Trading Signals Dashboard</h1>
    </div>

    <div class="container">
        <div class="card">
            <h2>📊 System Overview</h2>
            <div class="grid">
                <div class="metric">
                    <div class="metric-value status-{{ status_color }}">{{ total_signals }}</div>
                    <div class="metric-label">Active Signals</div>
                </div>
                <div class="metric">
                    <div class="metric-value status-good">{{ buy_signals }}</div>
                    <div class="metric-label">Buy Signals</div>
                </div>
                <div class="metric">
                    <div class="metric-value status-error">{{ sell_signals }}</div>
                    <div class="metric-label">Sell Signals</div>
                </div>
                <div class="metric">
                    <div class="metric-value status-neutral">{{ '{:.1%}'.format(avg_confidence) }}</div>
                    <div class="metric-label">Avg Confidence</div>
                </div>
                <div class="metric">
                    <div class="metric-value status-neutral">${{ '{:,.0f}'.format(portfolio_value) }}</div>
                    <div class="metric-label">Portfolio Value</div>
                </div>
            </div>

            <div style="margin-top: 1.5rem;">
                <button id="refreshBtn" class="btn btn-primary" onclick="refreshData()">🔄 Refresh</button>
                <button id="updateBtn" class="btn btn-success" onclick="updateSignals()">📊 Update Signals</button>
                <a href="/api/health" class="btn btn-warning" target="_blank">🏥 Health Check</a>
            </div>

            {% if last_update %}
            <div class="last-update">
                <strong>Last Update:</strong> {{ last_update }}
            </div>
            {% endif %}
        </div>

        {% if signals %}
        <div class="card">
            <h2>🎯 Active Trading Signals</h2>
            <div style="overflow-x: auto;">
                <table>
                    <thead>
                        <tr>
                            <th>Ticker</th>
                            <th>Signal</th>
                            <th>Confidence</th>
                            <th>Entry Price</th>
                            <th>Target</th>
                            <th>Stop Loss</th>
                            <th>Regime</th>
                            <th>Key Reasons</th>
                        </tr>
                    </thead>
                    <tbody>
                        {% for signal in signals %}
                        <tr class="signal-row signal-{{ signal.signal_type.value.lower().replace('_', '-') }}">
                            <td><span class="ticker-tag">{{ signal.ticker }}</span></td>
                            <td><strong>{{ signal.signal_type.value.replace('_', ' ') }}</strong></td>
                            <td>
                                <span class="confidence-{{ 'high' if signal.confidence > 0.8 else 'medium' if signal.confidence > 0.6 else 'low' }}">
                                    {{ '{:.1%}'.format(signal.confidence) }}
                                </span>
                            </td>
                            <td>${{ '{:.2f}'.format(signal.entry_price) }}</td>
                            <td>${{ '{:.2f}'.format(signal.target_price) }}</td>
                            <td>${{ '{:.2f}'.format(signal.stop_loss) }}</td>
                            <td>{{ signal.regime.value.replace('_', ' ').title() }}</td>
                            <td style="max-width: 200px; font-size: 0.85rem;">
                                {{ ', '.join(signal.reasons[:2]) }}{% if signal.reasons|length > 2 %}...{% endif %}
                            </td>
                        </tr>
                        {% endfor %}
                    </tbody>
                </table>
            </div>
        </div>
        {% else %}
        <div class="card">
            <h2>🎯 Trading Signals</h2>
            <div class="alert alert-info">
                No active signals at this time. Click "Update Signals" to generate fresh analysis.
            </div>
        </div>
        {% endif %}

        <div class="card">
            <h2>📈 Portfolio Overview</h2>
            <div style="overflow-x: auto;">
                <table>
                    <thead>
                        <tr>
                            <th>Ticker</th>
                            <th>Weight</th>
                            <th>Last Price</th>
                            <th>Daily Change</th>
                            <th>Volume Ratio</th>
                            <th>Status</th>
                        </tr>
                    </thead>
                    <tbody>
                        {% for ticker, data in portfolio_overview.items() %}
                        <tr>
                            <td><span class="ticker-tag">{{ ticker }}</span></td>
                            <td>{{ '{:.1%}'.format(data.get('weight', 0)) }}</td>
                            <td>${{ '{:.2f}'.format(data.get('price', 0)) }}</td>
                            <td class="{{ 'status-good' if data.get('daily_change', 0) > 0 else 'status-error' if data.get('daily_change', 0) < 0 else 'status-neutral' }}">
                                {{ '{:+.2%}'.format(data.get('daily_change', 0)) }}
                            </td>
                            <td class="{{ 'status-warning' if data.get('volume_ratio', 1) > 1.5 else 'status-neutral' }}">
                                {{ '{:.1f}x'.format(data.get('volume_ratio', 1)) }}
                            </td>
                            <td>
                                {% if data.get('daily_change', 0) > 0.02 %}
                                    <span class="status-good">📈 Strong</span>
                                {% elif data.get('daily_change', 0) > 0 %}
                                    <span class="status-good">📊 Positive</span>
                                {% elif data.get('daily_change', 0) < -0.02 %}
                                    <span class="status-error">📉 Weak</span>
                                {% elif data.get('daily_change', 0) < 0 %}
                                    <span class="status-error">📊 Negative</span>
                                {% else %}
                                    <span class="status-neutral">➡️ Flat</span>
                                {% endif %}
                            </td>
                        </tr>
                        {% endfor %}
                    </tbody>
                </table>
            </div>
        </div>

        <div class="card">
            <h2>🛡️ Risk & Performance</h2>
            <div class="grid">
                {% if portfolio_metrics %}
                <div class="metric">
                    <div class="metric-value status-{{ 'warning' if portfolio_metrics.get('volatility', 0) > 0.25 else 'good' }}">
                        {{ '{:.1%}'.format(portfolio_metrics.get('volatility', 0)) }}
                    </div>
                    <div class="metric-label">Volatility</div>
                </div>
                <div class="metric">
                    <div class="metric-value status-{{ 'good' if portfolio_metrics.get('sharpe_ratio', 0) > 1 else 'warning' if portfolio_metrics.get('sharpe_ratio', 0) > 0.5 else 'error' }}">
                        {{ '{:.2f}'.format(portfolio_metrics.get('sharpe_ratio', 0)) }}
                    </div>
                    <div class="metric-label">Sharpe Ratio</div>
                </div>
                <div class="metric">
                    <div class="metric-value status-{{ 'error' if portfolio_metrics.get('max_drawdown', 0) < -0.15 else 'warning' if portfolio_metrics.get('max_drawdown', 0) < -0.10 else 'good' }}">
                        {{ '{:.1%}'.format(portfolio_metrics.get('max_drawdown', 0)) }}
                    </div>
                    <div class="metric-label">Max Drawdown</div>
                </div>
                <div class="metric">
                    <div class="metric-value status-error">
                        {{ '{:.1%}'.format(portfolio_metrics.get('value_at_risk', 0)) }}
                    </div>
                    <div class="metric-label">VaR (95%)</div>
                </div>
                {% else %}
                <div class="alert alert-info">
                    Portfolio metrics will be calculated when signals are updated.
                </div>
                {% endif %}
            </div>
        </div>

        <div class="card">
            <h2>💼 Portfolio Management</h2>
            <div style="margin-bottom: 1.5rem;">
                <button class="btn btn-success" onclick="openAddPositionModal()">➕ Add Position</button>
            </div>
            <div style="margin-bottom: 1rem;">
                <div class="metric" style="text-align: left;">
                    <div style="font-size: 0.9rem; color: #64748b;">Total Portfolio Value</div>
                    <div style="font-size: 1.8rem; font-weight: 700; color: #059669; margin-top: 0.5rem;" id="totalPortfolioValue">$0.00</div>
                </div>
            </div>
            <div id="positionsContainer" style="max-height: 500px; overflow-y: auto;">
                <div class="alert alert-info">Loading positions...</div>
            </div>
        </div>

        <div id="addPositionModal" class="modal">
            <div class="modal-content">
                <span class="close-modal" onclick="closeModal('addPositionModal')">&times;</span>
                <div class="modal-header">Add New Position</div>
                <div class="form-group">
                    <label for="newTicker">Ticker:</label>
                    <input type="text" id="newTicker" placeholder="e.g., AAPL" maxlength="10">
                </div>
                <div class="form-group">
                    <label for="newShares">Shares:</label>
                    <input type="number" id="newShares" placeholder="e.g., 100" step="0.01" min="0">
                </div>
                <div class="modal-footer">
                    <button class="btn btn-primary" onclick="addPosition()">Add Position</button>
                    <button class="btn" style="background: #e2e8f0; color: #374151;" onclick="closeModal('addPositionModal')">Cancel</button>
                </div>
            </div>
        </div>

        <div class="card">
            <h2>⚙️ System Information</h2>
            <div class="alert alert-info">
                <strong>🎯 Strategy:</strong> Adaptive momentum and mean-reversion signals<br>
                <strong>📊 Coverage:</strong> {{ total_tickers }} portfolio positions<br>
                <strong>🔄 Updates:</strong> Automatic every 30 minutes during market hours<br>
                <strong>🛡️ Risk Management:</strong> Position sizing with volatility-based stops<br>
                <strong>☁️ Deployment:</strong> IBM Cloud optimized architecture
            </div>
        </div>
    </div>
</body>
</html>
"""


@web_bp.route("/")
def dashboard():
    """Main dashboard"""
    try:
        # Get data from API endpoints
        signals_data = []
        portfolio_overview = {}
        portfolio_metrics = {}

        # Try to get signals from API
        try:
            # In a real deployment, you'd call the API endpoints
            # For now, we'll use placeholder data or import directly
            from app.api.routes import current_signals, last_update

            signals_data = current_signals
        except Exception as e:
            logger.warning(f"Could not get signals: {e}")

        # Try to get portfolio overview
        try:
            from config.settings import Config
            from app.core.data_manager import DataManager
            from app.core.indicators import TechnicalIndicators

            dm = DataManager(db_path=Config.DATABASE_PATH())
            ti = TechnicalIndicators()

            # Get basic overview for each ticker
            for ticker in Config.PORTFOLIO_TICKERS()[:10]:  # Limit for performance
                try:
                    data = dm.get_stock_data(ticker, period="5d")
                    if not data.empty:
                        current_price = data["Close"].iloc[-1]
                        daily_change = data["Close"].pct_change().iloc[-1]
                        volume_ratio = (
                            data["Volume"].iloc[-1]
                            / data["Volume"].rolling(5).mean().iloc[-1]
                        )

                        portfolio_overview[ticker] = {
                            "price": current_price,
                            "daily_change": (
                                daily_change if not pd.isna(daily_change) else 0
                            ),
                            "volume_ratio": (
                                volume_ratio if not pd.isna(volume_ratio) else 1
                            ),
                            "weight": Config.PORTFOLIO_WEIGHTS().get(ticker, 0),
                        }
                except Exception as e:
                    logger.warning(f"Error getting data for {ticker}: {e}")
                    portfolio_overview[ticker] = {
                        "price": 0,
                        "daily_change": 0,
                        "volume_ratio": 1,
                        "weight": Config.PORTFOLIO_WEIGHTS().get(ticker, 0),
                    }

            dm.close()

        except Exception as e:
            logger.warning(f"Could not get portfolio overview: {e}")

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
        except:
            update_time = None

        return render_template_string(
            DASHBOARD_HTML,
            signals=signals_data,
            total_signals=total_signals,
            buy_signals=buy_signals,
            sell_signals=sell_signals,
            avg_confidence=avg_confidence,
            portfolio_value=19500,  # From config
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
def signals_page():
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
def portfolio_page():
    """Detailed portfolio page"""
    try:
        from config.settings import Config

        portfolio_html = f"""
        <div style="font-family: Arial, sans-serif; padding: 2rem;">
            <h1>Portfolio Details</h1>
            <h2>Holdings ({len(Config.PORTFOLIO_TICKERS())} positions)</h2>
            <table border="1" style="border-collapse: collapse; width: 100%;">
                <tr>
                    <th style="padding: 8px;">Ticker</th>
                    <th style="padding: 8px;">Weight</th>
                    <th style="padding: 8px;">Value</th>
                </tr>
        """

        for ticker, weight in Config.PORTFOLIO_WEIGHTS().items():
            value = weight * Config.PORTFOLIO_VALUE()
            portfolio_html += f"""
                <tr>
                    <td style="padding: 8px;">{ticker}</td>
                    <td style="padding: 8px;">{weight:.1%}</td>
                    <td style="padding: 8px;">${value:,.0f}</td>
                </tr>
            """

        portfolio_html += """
            </table>
            <p><a href="/">← Back to Dashboard</a></p>
        </div>
        """

        return portfolio_html

    except Exception as e:
        return f"Error: {e}", 500
