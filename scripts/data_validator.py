# ================================
# scripts/data_validator.py
# Data validation utility
# ================================
# !/usr/bin/env python3
"""
scripts/data_validator.py
Validate trading data quality and consistency
"""

import sys
import os
import pandas as pd
from datetime import datetime

# Add project root to path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)


def validate_ohlcv_data(data: pd.DataFrame, ticker: str) -> dict:
    """Validate OHLCV data quality"""
    issues = []
    warnings = []

    # Check required columns
    required_cols = ["Open", "High", "Low", "Close", "Volume"]
    missing_cols = [col for col in required_cols if col not in data.columns]
    if missing_cols:
        issues.append(f"Missing columns: {missing_cols}")
        return {"ticker": ticker, "issues": issues, "warnings": warnings}

    # Check for NaN values
    nan_counts = data[required_cols].isna().sum()
    for col, count in nan_counts.items():
        if count > 0:
            warnings.append(f"{col} has {count} NaN values")

    # Check OHLC consistency
    high_low_issues = (data["High"] < data["Low"]).sum()
    if high_low_issues > 0:
        issues.append(f"{high_low_issues} records where High < Low")

    open_high_issues = (data["Open"] > data["High"]).sum()
    close_high_issues = (data["Close"] > data["High"]).sum()
    open_low_issues = (data["Open"] < data["Low"]).sum()
    close_low_issues = (data["Close"] < data["Low"]).sum()

    ohlc_issues = (
        open_high_issues + close_high_issues + open_low_issues + close_low_issues
    )
    if ohlc_issues > 0:
        issues.append(f"{ohlc_issues} OHLC consistency violations")

    # Check for negative values
    negative_prices = (data[["Open", "High", "Low", "Close"]] <= 0).any(axis=1).sum()
    if negative_prices > 0:
        issues.append(f"{negative_prices} records with negative/zero prices")

    negative_volume = (data["Volume"] < 0).sum()
    if negative_volume > 0:
        issues.append(f"{negative_volume} records with negative volume")

    # Check for outliers (price changes > 50% in one day)
    price_changes = data["Close"].pct_change().abs()
    outliers = (price_changes > 0.5).sum()
    if outliers > 0:
        warnings.append(f"{outliers} potential price outliers (>50% daily change)")

    # Check for gaps in data
    if len(data) > 1:
        date_diff = pd.Series(data.index).diff()
        gaps = (date_diff > pd.Timedelta(days=7)).sum()
        if gaps > 0:
            warnings.append(f"{gaps} potential data gaps (>7 days)")

    # Check data recency
    if len(data) > 0:
        last_date = data.index[-1]
        days_old = (
            datetime.now() - last_date.tz_localize(None)
            if last_date.tz
            else datetime.now() - last_date
        ).days
        if days_old > 7:
            warnings.append(f"Data is {days_old} days old")

    return {
        "ticker": ticker,
        "issues": issues,
        "warnings": warnings,
        "records": len(data),
        "date_range": (
            f"{data.index[0].date()} to {data.index[-1].date()}"
            if len(data) > 0
            else "No data"
        ),
    }


def validate_portfolio_data():
    """Validate all portfolio data"""
    from app.core.data_manager import DataManager
    from config.settings import Config

    print("🔍 Validating Portfolio Data")
    print("=" * 50)

    dm = DataManager()

    all_results = []
    total_issues = 0
    total_warnings = 0

    for ticker in Config.PORTFOLIO_TICKERS:
        print(f"Validating {ticker}...", end=" ")

        try:
            data = dm._get_cached_data(ticker, "1d")

            if data is None or data.empty:
                print("❌ No data")
                all_results.append(
                    {
                        "ticker": ticker,
                        "issues": ["No data available"],
                        "warnings": [],
                        "records": 0,
                        "date_range": "No data",
                    }
                )
                total_issues += 1
                continue

            validation_result = validate_ohlcv_data(data, ticker)
            all_results.append(validation_result)

            issues = len(validation_result["issues"])
            warnings = len(validation_result["warnings"])
            total_issues += issues
            total_warnings += warnings

            if issues > 0:
                print(f"❌ {issues} issues, {warnings} warnings")
            elif warnings > 0:
                print(f"⚠️  {warnings} warnings")
            else:
                print("✅ OK")

        except Exception as e:
            print(f"❌ Error: {str(e)}")
            all_results.append(
                {
                    "ticker": ticker,
                    "issues": [f"Validation error: {str(e)}"],
                    "warnings": [],
                    "records": 0,
                    "date_range": "Error",
                }
            )
            total_issues += 1

    dm.close()

    # Print detailed results
    print("\n" + "=" * 50)
    print("Detailed Results:")

    for result in all_results:
        if result["issues"] or result["warnings"]:
            print(
                f"\n{result['ticker']} ({result['records']} records, {result['date_range']}):"
            )
            for issue in result["issues"]:
                print(f"  ❌ {issue}")
            for warning in result["warnings"]:
                print(f"  ⚠️  {warning}")

    # Summary
    print("\n" + "=" * 50)
    print(f"Validation Summary:")
    print(f"Total tickers: {len(Config.PORTFOLIO_TICKERS)}")
    print(f"Total issues: {total_issues}")
    print(f"Total warnings: {total_warnings}")

    if total_issues == 0:
        print("🎉 No critical data issues found!")
        return 0
    else:
        print("⚠️  Data issues detected. Consider refreshing data.")
        return 1


if __name__ == "__main__":
    exit_code = validate_portfolio_data()
    sys.exit(exit_code)
