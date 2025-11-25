#!/usr/bin/env python3
"""
scripts/backtest.py
Backtesting framework for trading strategies
"""

import sys
import os
import pandas as pd
import numpy as np
import logging
from datetime import datetime, timedelta
from typing import Dict, List
import argparse

# Add project root to Python path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from app.core.data_manager import DataManager
from app.core.signal_generator import SignalGenerator, TradingSignal, SignalType
from app.core.portfolio_analyzer import PortfolioAnalyzer


class BacktestEngine:
    """Backtesting engine for trading strategies"""

    def __init__(self, initial_capital: float = 10000, commission: float = 0.0):
        self.initial_capital = initial_capital
        self.commission = commission
        self.logger = logging.getLogger(__name__)

        # Trading components
        self.dm = DataManager()
        self.signal_gen = SignalGenerator(
            min_confidence=0.5
        )  # Lower threshold for backtest
        self.portfolio_analyzer = PortfolioAnalyzer()

        # Backtest state
        self.cash = initial_capital
        self.positions = {}  # ticker -> shares
        self.portfolio_value = []
        self.trades = []
        self.signals_history = []

    def run_backtest(
        self,
        tickers: List[str],
        start_date: str,
        end_date: str,
        rebalance_frequency: str = "weekly",
    ) -> Dict:
        """
        Run backtest on given tickers and date range

        Args:
            tickers: List of stock symbols
            start_date: Start date 'YYYY-MM-DD'
            end_date: End date 'YYYY-MM-DD'
            rebalance_frequency: 'daily', 'weekly', 'monthly'
        """
        self.logger.info(f"Starting backtest: {start_date} to {end_date}")

        # Download historical data
        portfolio_data = {}
        for ticker in tickers:
            data = self.dm.get_stock_data(ticker, period="max")
            if not data.empty:
                # Filter to backtest period
                data = data[start_date:end_date]
                portfolio_data[ticker] = data

        if not portfolio_data:
            raise ValueError("No data available for backtest period")

        # Get common date range
        common_dates = self._get_common_dates(portfolio_data)

        # Run simulation
        for i, current_date in enumerate(common_dates):
            if i < 50:  # Need enough data for indicators
                continue

            # Check if rebalance day
            if self._should_rebalance(current_date, rebalance_frequency, i):
                self._rebalance_portfolio(current_date, portfolio_data, tickers)

            # Calculate portfolio value
            self._update_portfolio_value(current_date, portfolio_data)

        # Calculate performance metrics
        results = self._calculate_performance_metrics()

        self.dm.close()
        return results

    def _get_common_dates(
        self, portfolio_data: Dict[str, pd.DataFrame]
    ) -> pd.DatetimeIndex:
        """Get common dates across all stocks"""
        all_dates = None
        for data in portfolio_data.values():
            if all_dates is None:
                all_dates = data.index
            else:
                all_dates = all_dates.intersection(data.index)
        return all_dates.sort_values()

    def _should_rebalance(
        self, current_date: pd.Timestamp, frequency: str, day_index: int
    ) -> bool:
        """Check if should rebalance on this date"""
        if frequency == "daily":
            return True
        elif frequency == "weekly":
            return current_date.dayofweek == 0  # Monday
        elif frequency == "monthly":
            return current_date.day <= 7 and current_date.dayofweek == 0  # First Monday
        return False

    def _rebalance_portfolio(
        self,
        current_date: pd.Timestamp,
        portfolio_data: Dict[str, pd.DataFrame],
        tickers: List[str],
    ):
        """Rebalance portfolio based on signals"""

        # Generate signals for current date
        signals = []
        for ticker in tickers:
            if ticker in portfolio_data:
                # Get data up to current date
                historical_data = portfolio_data[ticker].loc[:current_date]
                if len(historical_data) >= 50:
                    signal = self.signal_gen.generate_signal(ticker, historical_data)
                    if signal:
                        signals.append(signal)
                        self.signals_history.append(
                            {
                                "date": current_date,
                                "ticker": ticker,
                                "signal": signal.signal_type.value,
                                "confidence": signal.confidence,
                            }
                        )

        # Execute trades based on signals
        self._execute_signals(current_date, signals, portfolio_data)

    def _execute_signals(
        self,
        current_date: pd.Timestamp,
        signals: List[TradingSignal],
        portfolio_data: Dict[str, pd.DataFrame],
    ):
        """Execute trades based on signals"""

        buy_signals = [
            s
            for s in signals
            if s.signal_type in [SignalType.BUY, SignalType.STRONG_BUY]
        ]
        sell_signals = [
            s
            for s in signals
            if s.signal_type in [SignalType.SELL, SignalType.STRONG_SELL]
        ]

        # Execute sells first
        for signal in sell_signals:
            if signal.ticker in self.positions and self.positions[signal.ticker] > 0:
                self._execute_sell(current_date, signal, portfolio_data)

        # Execute buys
        if buy_signals:
            # Allocate cash equally among buy signals
            available_cash = self.cash * 0.95  # Keep 5% cash buffer
            cash_per_position = available_cash / len(buy_signals)

            for signal in buy_signals:
                if cash_per_position > 100:  # Minimum trade size
                    self._execute_buy(
                        current_date, signal, cash_per_position, portfolio_data
                    )

    def _execute_buy(
        self,
        current_date: pd.Timestamp,
        signal: TradingSignal,
        amount: float,
        portfolio_data: Dict[str, pd.DataFrame],
    ):
        """Execute buy order"""
        ticker = signal.ticker
        price = portfolio_data[ticker].loc[current_date, "Close"]

        shares_to_buy = int(amount / price)
        if shares_to_buy > 0:
            cost = shares_to_buy * price + self.commission

            if cost <= self.cash:
                self.cash -= cost
                self.positions[ticker] = self.positions.get(ticker, 0) + shares_to_buy

                self.trades.append(
                    {
                        "date": current_date,
                        "ticker": ticker,
                        "action": "BUY",
                        "shares": shares_to_buy,
                        "price": price,
                        "total": cost,
                        "signal_confidence": signal.confidence,
                    }
                )

    def _execute_sell(
        self,
        current_date: pd.Timestamp,
        signal: TradingSignal,
        portfolio_data: Dict[str, pd.DataFrame],
    ):
        """Execute sell order"""
        ticker = signal.ticker
        price = portfolio_data[ticker].loc[current_date, "Close"]

        shares_to_sell = self.positions[ticker]
        proceeds = shares_to_sell * price - self.commission

        self.cash += proceeds
        self.positions[ticker] = 0

        self.trades.append(
            {
                "date": current_date,
                "ticker": ticker,
                "action": "SELL",
                "shares": shares_to_sell,
                "price": price,
                "total": proceeds,
                "signal_confidence": signal.confidence,
            }
        )

    def _update_portfolio_value(
        self, current_date: pd.Timestamp, portfolio_data: Dict[str, pd.DataFrame]
    ):
        """Update total portfolio value"""
        total_value = self.cash

        for ticker, shares in self.positions.items():
            if shares > 0 and ticker in portfolio_data:
                price = portfolio_data[ticker].loc[current_date, "Close"]
                total_value += shares * price

        self.portfolio_value.append(
            {
                "date": current_date,
                "value": total_value,
                "cash": self.cash,
                "positions_value": total_value - self.cash,
            }
        )

    def _calculate_performance_metrics(self) -> Dict:
        """Calculate backtest performance metrics"""
        if not self.portfolio_value:
            return {"error": "No portfolio values calculated"}

        df = pd.DataFrame(self.portfolio_value)
        df["returns"] = df["value"].pct_change()

        final_value = df["value"].iloc[-1]
        total_return = (final_value - self.initial_capital) / self.initial_capital

        # Annualized metrics
        days = len(df)
        annual_return = (1 + total_return) ** (252 / days) - 1
        annual_volatility = df["returns"].std() * np.sqrt(252)

        # Sharpe ratio
        sharpe_ratio = annual_return / annual_volatility if annual_volatility > 0 else 0

        # Maximum drawdown
        cumulative = (1 + df["returns"]).cumprod()
        rolling_max = cumulative.expanding().max()
        drawdowns = (cumulative - rolling_max) / rolling_max
        max_drawdown = drawdowns.min()

        # Win rate
        profitable_trades = len(
            [t for t in self.trades if t["action"] == "SELL" and t["total"] > 0]
        )
        total_trades = len([t for t in self.trades if t["action"] == "SELL"])
        win_rate = profitable_trades / total_trades if total_trades > 0 else 0

        return {
            "initial_capital": self.initial_capital,
            "final_value": final_value,
            "total_return": total_return,
            "annual_return": annual_return,
            "annual_volatility": annual_volatility,
            "sharpe_ratio": sharpe_ratio,
            "max_drawdown": max_drawdown,
            "win_rate": win_rate,
            "total_trades": len(self.trades),
            "signals_generated": len(self.signals_history),
            "portfolio_history": df.to_dict("records"),
            "trades": self.trades,
            "signals": self.signals_history,
        }


def run_quick_backtest():
    """Run a quick backtest with default parameters"""
    logging.basicConfig(level=logging.INFO)

    # Use subset of portfolio for quick test
    test_tickers = ["AAPL", "MSFT", "GOOGL", "VTI"]

    engine = BacktestEngine(initial_capital=10000)

    # Backtest last year
    end_date = datetime.now().strftime("%Y-%m-%d")
    start_date = (datetime.now() - timedelta(days=365)).strftime("%Y-%m-%d")

    results = engine.run_backtest(
        tickers=test_tickers,
        start_date=start_date,
        end_date=end_date,
        rebalance_frequency="weekly",
    )

    print("\n=== BACKTEST RESULTS ===")
    print(f"Initial Capital: ${results['initial_capital']:,.2f}")
    print(f"Final Value: ${results['final_value']:,.2f}")
    print(f"Total Return: {results['total_return']:.2%}")
    print(f"Annual Return: {results['annual_return']:.2%}")
    print(f"Annual Volatility: {results['annual_volatility']:.2%}")
    print(f"Sharpe Ratio: {results['sharpe_ratio']:.2f}")
    print(f"Max Drawdown: {results['max_drawdown']:.2%}")
    print(f"Win Rate: {results['win_rate']:.2%}")
    print(f"Total Trades: {results['total_trades']}")
    print(f"Signals Generated: {results['signals_generated']}")

    return results


def main():
    """Main backtest function with command line arguments"""
    parser = argparse.ArgumentParser(description="Run trading strategy backtest")
    parser.add_argument(
        "--tickers",
        nargs="+",
        default=["AAPL", "MSFT", "GOOGL", "VTI"],
        help="Stock tickers to backtest",
    )
    parser.add_argument(
        "--start-date",
        type=str,
        default=(datetime.now() - timedelta(days=365)).strftime("%Y-%m-%d"),
        help="Start date (YYYY-MM-DD)",
    )
    parser.add_argument(
        "--end-date",
        type=str,
        default=datetime.now().strftime("%Y-%m-%d"),
        help="End date (YYYY-MM-DD)",
    )
    parser.add_argument("--capital", type=float, default=10000, help="Initial capital")
    parser.add_argument(
        "--frequency",
        choices=["daily", "weekly", "monthly"],
        default="weekly",
        help="Rebalancing frequency",
    )
    parser.add_argument("--output", type=str, help="Output file for results (JSON)")

    args = parser.parse_args()

    # Setup logging
    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
    )

    # Run backtest
    engine = BacktestEngine(initial_capital=args.capital)

    try:
        results = engine.run_backtest(
            tickers=args.tickers,
            start_date=args.start_date,
            end_date=args.end_date,
            rebalance_frequency=args.frequency,
        )

        # Print results
        print("\n=== BACKTEST RESULTS ===")
        print(f"Period: {args.start_date} to {args.end_date}")
        print(f"Tickers: {', '.join(args.tickers)}")
        print(f"Initial Capital: ${results['initial_capital']:,.2f}")
        print(f"Final Value: ${results['final_value']:,.2f}")
        print(f"Total Return: {results['total_return']:.2%}")
        print(f"Annual Return: {results['annual_return']:.2%}")
        print(f"Annual Volatility: {results['annual_volatility']:.2%}")
        print(f"Sharpe Ratio: {results['sharpe_ratio']:.2f}")
        print(f"Max Drawdown: {results['max_drawdown']:.2%}")
        print(f"Win Rate: {results['win_rate']:.2%}")
        print(f"Total Trades: {results['total_trades']}")

        # Save results if output file specified
        if args.output:
            import json

            with open(args.output, "w") as f:
                # Convert datetime objects to strings for JSON serialization
                json_results = results.copy()
                for item in json_results.get("trades", []):
                    if "date" in item:
                        item["date"] = item["date"].isoformat()
                for item in json_results.get("signals", []):
                    if "date" in item:
                        item["date"] = item["date"].isoformat()
                for item in json_results.get("portfolio_history", []):
                    if "date" in item:
                        item["date"] = item["date"].isoformat()

                json.dump(json_results, f, indent=2)
            print(f"\nResults saved to {args.output}")

        return 0

    except Exception as e:
        print(f"Backtest failed: {e}")
        return 1


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
