# ================================
# scripts/health_check.py
# Simple health check utility
# ================================
# !/usr/bin/env python3
"""
scripts/health_check.py
Quick health check for the trading system
"""

import sys
import os
import requests
import json
import time
from datetime import datetime

# Add project root to path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)


def check_database():
    """Check database connectivity"""
    try:
        from config.database import DatabaseConfig
        from config.settings import Config

        db_config = DatabaseConfig(Config.DATABASE_PATH)
        if db_config.check_connection():
            return True, "Database connection successful"
        else:
            return False, "Database connection failed"
    except Exception as e:
        return False, f"Database error: {str(e)}"


def check_data_manager():
    """Check data manager functionality"""
    try:
        from app.core.data_manager import DataManager

        dm = DataManager()
        # Try to get some recent data
        test_data = dm.get_stock_data('AAPL', period='5d')
        dm.close()

        if not test_data.empty:
            return True, f"Data manager working, got {len(test_data)} records"
        else:
            return False, "Data manager returned empty data"
    except Exception as e:
        return False, f"Data manager error: {str(e)}"


def check_signal_generator():
    """Check signal generation"""
    try:
        from app.core.data_manager import DataManager
        from app.core.signal_generator import SignalGenerator

        dm = DataManager()
        sg = SignalGenerator(min_confidence=0.3)

        # Get test data and generate signal
        test_data = dm.get_stock_data('AAPL', period='3mo')
        signal = sg.generate_signal('AAPL', test_data)

        dm.close()

        if signal is not None:
            return True, f"Signal generator working: {signal.signal_type.value}"
        else:
            return True, "Signal generator working (no signal generated)"
    except Exception as e:
        return False, f"Signal generator error: {str(e)}"


def check_api_endpoints(base_url="http://localhost:5000"):
    """Check API endpoints"""
    endpoints = ['/api/health', '/api/signals', '/api/portfolio']
    results = []

    for endpoint in endpoints:
        try:
            response = requests.get(f"{base_url}{endpoint}", timeout=10)
            if response.status_code == 200:
                results.append((True, f"{endpoint}: OK ({response.status_code})"))
            else:
                results.append((False, f"{endpoint}: Failed ({response.status_code})"))
        except requests.RequestException as e:
            results.append((False, f"{endpoint}: Connection error - {str(e)}"))

    return results


def check_yahoo_finance():
    """Check Yahoo Finance connectivity"""
    try:
        import yfinance as yf
        ticker = yf.Ticker('AAPL')
        data = ticker.history(period='1d')

        if not data.empty:
            return True, "Yahoo Finance connectivity OK"
        else:
            return False, "Yahoo Finance returned empty data"
    except Exception as e:
        return False, f"Yahoo Finance error: {str(e)}"


def check_file_permissions():
    """Check file and directory permissions"""
    paths_to_check = [
        'data',
        'logs',
        'backups',
        'config.json'
    ]

    issues = []
    for path in paths_to_check:
        if not os.path.exists(path):
            if path.endswith('.json'):
                issues.append(f"Missing file: {path}")
            else:
                issues.append(f"Missing directory: {path}")
        elif path != 'config.json':  # Directories
            if not os.access(path, os.W_OK):
                issues.append(f"No write permission: {path}")

    if issues:
        return False, f"Permission issues: {', '.join(issues)}"
    else:
        return True, "File permissions OK"


def check_disk_space():
    """Check available disk space"""
    try:
        import shutil
        total, used, free = shutil.disk_usage('.')
        free_gb = free / (1024 ** 3)

        if free_gb < 1:
            return False, f"Low disk space: {free_gb:.1f}GB free"
        elif free_gb < 5:
            return True, f"Disk space warning: {free_gb:.1f}GB free"
        else:
            return True, f"Disk space OK: {free_gb:.1f}GB free"
    except Exception as e:
        return False, f"Disk space check failed: {str(e)}"


def main():
    """Run comprehensive health check"""
    print("🔍 Trading System Health Check")
    print("=" * 50)
    print(f"Timestamp: {datetime.now().isoformat()}")
    print()

    checks = [
        ("File Permissions", check_file_permissions),
        ("Disk Space", check_disk_space),
        ("Database", check_database),
        ("Yahoo Finance", check_yahoo_finance),
        ("Data Manager", check_data_manager),
        ("Signal Generator", check_signal_generator),
    ]

    results = []
    for name, check_func in checks:
        print(f"Checking {name}...", end=" ")
        try:
            success, message = check_func()
            status = "✅" if success else "❌"
            print(f"{status} {message}")
            results.append((name, success, message))
        except Exception as e:
            print(f"❌ Error: {str(e)}")
            results.append((name, False, f"Error: {str(e)}"))

    # Check API endpoints if requested
    if len(sys.argv) > 1 and sys.argv[1] == '--api':
        print("\nChecking API endpoints...")
        api_results = check_api_endpoints()
        for success, message in api_results:
            status = "✅" if success else "❌"
            print(f"{status} {message}")
            results.extend([("API", success, message)])

    # Summary
    print("\n" + "=" * 50)
    total_checks = len(results)
    passed_checks = sum(1 for _, success, _ in results if success)

    print(f"Health Check Summary: {passed_checks}/{total_checks} checks passed")

    if passed_checks == total_checks:
        print("🎉 All systems operational!")
        return 0
    else:
        print("⚠️  Some issues detected. See details above.")
        return 1


if __name__ == '__main__':
    exit_code = main()
    sys.exit(exit_code)
    