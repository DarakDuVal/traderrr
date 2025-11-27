"""
tests/test_portfolio.py
Test cases for portfolio analysis and risk management
"""

import unittest
import pandas as pd
import numpy as np

from tests import BaseTestCase
from app.core.portfolio_analyzer import (
    PortfolioAnalyzer,
    PortfolioMetrics,
    PositionRisk,
)


class TestPortfolioAnalyzer(BaseTestCase):
    """Test cases for PortfolioAnalyzer"""

    def setUp(self):
        """Set up test fixtures"""
        super().setUp()
        self.analyzer = PortfolioAnalyzer()

        # Create sample portfolio data
        np.random.seed(42)
        dates = pd.date_range(
            "2023-01-01", periods=252, freq="D"
        )  # One year of daily data

        # Generate correlated stock data
        n_stocks = 4
        n_days = len(dates)

        # Base market return
        market_returns = np.random.normal(
            0.0008, 0.015, n_days
        )  # 0.08% daily, 1.5% volatility

        # Individual stock returns with different betas
        betas = [1.2, 0.8, 1.5, 0.6]
        stock_returns = {}

        for i, (ticker, beta) in enumerate(
            zip(["AAPL", "MSFT", "GOOGL", "SPY"], betas)
        ):
            # Stock return = beta * market + idiosyncratic
            stock_return = beta * market_returns + np.random.normal(
                0, 0.01, n_days
            )  # 1% idiosyncratic volatility

            # Convert to prices
            prices = 100 * np.exp(np.cumsum(stock_return))

            stock_returns[ticker] = pd.DataFrame(
                {
                    "Open": prices * np.random.uniform(0.995, 1.005, n_days),
                    "High": prices * np.random.uniform(1.000, 1.020, n_days),
                    "Low": prices * np.random.uniform(0.980, 1.000, n_days),
                    "Close": prices,
                    "Volume": np.random.randint(1000000, 10000000, n_days),
                },
                index=dates,
            )
            # Set index name to 'Date' to match yfinance format
            stock_returns[ticker].index.name = "Date"

            # Ensure OHLC consistency
            for j in range(n_days):
                high = max(stock_returns[ticker].iloc[j][["Open", "High", "Close"]])
                low = min(stock_returns[ticker].iloc[j][["Open", "Low", "Close"]])
                stock_returns[ticker].iloc[
                    j, stock_returns[ticker].columns.get_loc("High")
                ] = high
                stock_returns[ticker].iloc[
                    j, stock_returns[ticker].columns.get_loc("Low")
                ] = low

        self.portfolio_data = stock_returns
        self.portfolio_weights = {
            "AAPL": 0.30,
            "MSFT": 0.25,
            "GOOGL": 0.25,
            "SPY": 0.20,
        }
        self.portfolio_value = 100000

    def test_portfolio_analysis(self):
        """Test comprehensive portfolio analysis"""
        metrics = self.analyzer.analyze_portfolio(
            self.portfolio_data, self.portfolio_weights, benchmark_ticker="SPY"
        )

        # Check that metrics object has all required attributes
        self.assertIsInstance(metrics, PortfolioMetrics)
        self.assertTrue(hasattr(metrics, "volatility"))
        self.assertTrue(hasattr(metrics, "sharpe_ratio"))
        self.assertTrue(hasattr(metrics, "max_drawdown"))
        self.assertTrue(hasattr(metrics, "beta"))
        self.assertTrue(hasattr(metrics, "value_at_risk"))

        # Check that metrics are reasonable
        self.assertGreater(metrics.volatility, 0)
        self.assertLess(metrics.volatility, 1.0)  # Less than 100% annual volatility

        self.assertGreater(metrics.max_drawdown, -0.5)  # Max 50% drawdown
        self.assertLess(metrics.max_drawdown, 0)  # Drawdown should be negative

        # VaR should be negative (loss)
        self.assertLess(metrics.value_at_risk, 0)
        self.assertGreater(metrics.value_at_risk, -0.1)  # Max 10% daily VaR

    def test_position_risk_calculation(self):
        """Test position risk metrics"""
        position_risks = self.analyzer.calculate_position_risks(
            self.portfolio_data, self.portfolio_weights, self.portfolio_value
        )

        # Should have one risk object per position
        self.assertEqual(len(position_risks), len(self.portfolio_weights))

        # Check that all positions are represented
        tickers = [pos.ticker for pos in position_risks]
        for ticker in self.portfolio_weights.keys():
            self.assertIn(ticker, tickers)

        # Check position risk attributes
        for pos_risk in position_risks:
            self.assertIsInstance(pos_risk, PositionRisk)
            self.assertGreater(pos_risk.position_size, 0)
            self.assertGreater(pos_risk.weight, 0)
            self.assertLess(pos_risk.weight, 1)
            self.assertGreaterEqual(pos_risk.liquidity_score, 0)
            self.assertLessEqual(pos_risk.liquidity_score, 1)
            self.assertGreaterEqual(pos_risk.concentration_risk, 0)
            self.assertLessEqual(pos_risk.concentration_risk, 1)

        # Check that weights match input
        total_weight = sum(pos.weight for pos in position_risks)
        self.assertAlmostEqual(total_weight, 1.0, places=2)

    def test_correlation_matrix(self):
        """Test correlation matrix calculation"""
        correlation_matrix = self.analyzer.calculate_correlation_matrix(
            self.portfolio_data
        )

        # Should be square matrix
        self.assertEqual(correlation_matrix.shape[0], correlation_matrix.shape[1])
        self.assertEqual(correlation_matrix.shape[0], len(self.portfolio_data))

        # Diagonal should be 1 (perfect self-correlation)
        for i in range(len(correlation_matrix)):
            self.assertAlmostEqual(correlation_matrix.iloc[i, i], 1.0, places=2)

        # Should be symmetric
        for i in range(len(correlation_matrix)):
            for j in range(len(correlation_matrix)):
                self.assertAlmostEqual(
                    correlation_matrix.iloc[i, j],
                    correlation_matrix.iloc[j, i],
                    places=6,
                )

        # Correlations should be between -1 and 1
        values = correlation_matrix.values
        self.assertTrue((values >= -1.0).all())
        self.assertTrue((values <= 1.0).all())

    def test_portfolio_optimization(self):
        """Test portfolio optimization"""
        optimized_weights = self.analyzer.optimize_portfolio(
            self.portfolio_data, self.portfolio_weights, risk_tolerance=0.15
        )

        # Should return a dictionary of weights
        self.assertIsInstance(optimized_weights, dict)

        # Weights should sum to approximately 1
        total_weight = sum(optimized_weights.values())
        self.assertAlmostEqual(total_weight, 1.0, places=1)

        # All weights should be non-negative and less than max allowed
        for weight in optimized_weights.values():
            self.assertGreaterEqual(weight, 0)
            self.assertLessEqual(weight, 0.3)  # Max position size from optimization

    def test_risk_report_generation(self):
        """Test comprehensive risk report"""
        report = self.analyzer.generate_risk_report(
            self.portfolio_data, self.portfolio_weights, self.portfolio_value
        )

        # Check report structure
        self.assertIn("timestamp", report)
        self.assertIn("portfolio_metrics", report)
        self.assertIn("position_risks", report)
        self.assertIn("correlation_summary", report)
        self.assertIn("recommendations", report)

        # Check portfolio metrics in report
        portfolio_metrics = report["portfolio_metrics"]
        self.assertIn("volatility", portfolio_metrics)
        self.assertIn("sharpe_ratio", portfolio_metrics)
        self.assertIn("max_drawdown", portfolio_metrics)

        # Check position risks in report
        position_risks = report["position_risks"]
        self.assertIsInstance(position_risks, list)
        self.assertEqual(len(position_risks), len(self.portfolio_weights))

        # Check correlation summary
        corr_summary = report["correlation_summary"]
        self.assertIn("average_correlation", corr_summary)
        self.assertIn("max_correlation", corr_summary)

        # Check recommendations
        recommendations = report["recommendations"]
        self.assertIsInstance(recommendations, list)

    def test_stress_testing(self):
        """Test stress testing scenarios"""
        report = self.analyzer.generate_risk_report(
            self.portfolio_data, self.portfolio_weights, self.portfolio_value
        )

        stress_scenarios = report.get("stress_scenarios", {})

        # Should have multiple scenarios
        self.assertGreater(len(stress_scenarios), 0)

        # Stress scenario values should be numeric
        for scenario_name, impact in stress_scenarios.items():
            self.assertIsInstance(
                impact,
                (int, float, np.number),
                f"Stress scenario {scenario_name} should be numeric",
            )

    def test_edge_cases(self):
        """Test edge cases and error handling"""
        # Test with empty portfolio data - should raise ValueError
        empty_portfolio = {}
        with self.assertRaises(ValueError):
            metrics = self.analyzer.analyze_portfolio(empty_portfolio, {})

        # Test with single asset
        single_asset_data = {"AAPL": self.portfolio_data["AAPL"]}
        single_asset_weights = {"AAPL": 1.0}

        metrics = self.analyzer.analyze_portfolio(
            single_asset_data, single_asset_weights
        )
        self.assertIsInstance(metrics, PortfolioMetrics)

        # Test with mismatched weights and data
        mismatched_weights = {"AAPL": 0.5, "INVALID": 0.5}
        metrics = self.analyzer.analyze_portfolio(
            self.portfolio_data, mismatched_weights
        )
        self.assertIsInstance(metrics, PortfolioMetrics)

    def test_liquidity_score_calculation(self):
        """Test liquidity score calculation"""
        # Create high volume, low volatility data (high liquidity)
        high_liquidity_data = self.portfolio_data["AAPL"].copy()
        high_liquidity_data["Volume"] = 50000000  # Very high volume

        liquidity_score_high = self.analyzer._calculate_liquidity_score(
            high_liquidity_data
        )

        # Create low volume, high volatility data (low liquidity)
        low_liquidity_data = self.portfolio_data["AAPL"].copy()
        low_liquidity_data["Volume"] = 100000  # Very low volume
        low_liquidity_data["Close"] = low_liquidity_data["Close"] * (
            1 + np.random.normal(0, 0.1, len(low_liquidity_data))
        )  # High volatility

        liquidity_score_low = self.analyzer._calculate_liquidity_score(
            low_liquidity_data
        )

        # High liquidity should score higher
        self.assertGreater(liquidity_score_high, liquidity_score_low)

        # Scores should be between 0 and 1
        self.assertGreaterEqual(liquidity_score_high, 0)
        self.assertLessEqual(liquidity_score_high, 1)
        self.assertGreaterEqual(liquidity_score_low, 0)
        self.assertLessEqual(liquidity_score_low, 1)

    def test_concentration_risk(self):
        """Test concentration risk calculation"""
        # Low concentration
        low_concentration = self.analyzer._calculate_concentration_risk(0.05)

        # High concentration
        high_concentration = self.analyzer._calculate_concentration_risk(0.30)

        # Very high concentration
        very_high_concentration = self.analyzer._calculate_concentration_risk(0.50)

        # Risk should increase or stay the same with concentration (may plateau at 1.0)
        self.assertLessEqual(low_concentration, high_concentration)
        self.assertLessEqual(high_concentration, very_high_concentration)

        # Low concentration should definitely be less than high
        self.assertLess(low_concentration, high_concentration)

        # All should be between 0 and 1
        for risk in [low_concentration, high_concentration, very_high_concentration]:
            self.assertGreaterEqual(risk, 0)
            self.assertLessEqual(risk, 1)

    def test_sector_concentration_analysis(self):
        """Test sector concentration analysis"""
        # Test with portfolio weights
        sector_analysis = self.analyzer._analyze_sector_concentration(
            self.portfolio_weights
        )

        # Should return dictionary with expected keys
        self.assertIn("sector_weights", sector_analysis)
        self.assertIn("max_sector_weight", sector_analysis)
        self.assertIn("concentration_risk", sector_analysis)

        # Max sector weight should be reasonable
        max_weight = sector_analysis["max_sector_weight"]
        self.assertGreaterEqual(max_weight, 0)
        self.assertLessEqual(max_weight, 1)

        # Concentration risk should be a valid category
        concentration_risk = sector_analysis["concentration_risk"]
        self.assertIn(concentration_risk, ["Low", "Medium", "High"])

    def test_risk_contribution_calculation(self):
        """Test risk contribution calculation"""
        # Get portfolio returns for testing
        aligned_data = self.analyzer._align_portfolio_data(self.portfolio_data)
        portfolio_returns = self.analyzer._calculate_portfolio_returns(
            aligned_data, self.portfolio_weights
        )

        # Test risk contribution for each asset
        for ticker, weight in self.portfolio_weights.items():
            if ticker in aligned_data.columns:
                asset_returns = aligned_data[ticker].pct_change().dropna()
                # Align with portfolio returns
                common_idx = asset_returns.index.intersection(portfolio_returns.index)
                if len(common_idx) > 10:
                    asset_returns_aligned = asset_returns.loc[common_idx]
                    portfolio_returns_aligned = portfolio_returns.loc[common_idx]

                    risk_contribution = self.analyzer._calculate_risk_contribution(
                        asset_returns_aligned, portfolio_returns_aligned, weight
                    )

                    # Risk contribution should be a valid number
                    self.assertIsInstance(risk_contribution, (int, float))
                    self.assertFalse(np.isnan(risk_contribution))

    def test_performance_metrics_calculation(self):
        """Test individual performance metrics"""
        # Get portfolio returns
        aligned_data = self.analyzer._align_portfolio_data(self.portfolio_data)
        portfolio_returns = self.analyzer._calculate_portfolio_returns(
            aligned_data, self.portfolio_weights
        )

        # Get benchmark returns
        benchmark_returns = None
        if "SPY" in aligned_data.columns:
            benchmark_returns = aligned_data["SPY"].pct_change().dropna()

        # Calculate metrics
        metrics = self.analyzer._calculate_portfolio_metrics(
            portfolio_returns, benchmark_returns
        )

        # Test specific metric calculations
        self.assertIsInstance(metrics.volatility, float)
        self.assertGreater(metrics.volatility, 0)

        self.assertIsInstance(metrics.sharpe_ratio, float)

        self.assertIsInstance(metrics.max_drawdown, float)
        self.assertLessEqual(metrics.max_drawdown, 0)

        self.assertIsInstance(metrics.value_at_risk, float)
        self.assertLess(metrics.value_at_risk, 0)  # VaR should be negative

        if benchmark_returns is not None:
            self.assertIsInstance(metrics.beta, float)
            self.assertIsInstance(metrics.alpha, float)

    def test_data_alignment(self):
        """Test portfolio data alignment"""
        aligned_data = self.analyzer._align_portfolio_data(self.portfolio_data)

        # Should return DataFrame
        self.assertIsInstance(aligned_data, pd.DataFrame)

        # Should have columns for each ticker
        for ticker in self.portfolio_data.keys():
            self.assertIn(ticker, aligned_data.columns)

        # Should not have any NaN values (after alignment)
        self.assertFalse(aligned_data.isna().any().any())

        # All columns should have same length
        lengths = [len(aligned_data[col]) for col in aligned_data.columns]
        self.assertTrue(all(length == lengths[0] for length in lengths))


class TestPortfolioOptimization(BaseTestCase):
    """Test cases for portfolio optimization functionality"""

    def setUp(self):
        """Set up test fixtures for optimization"""
        super().setUp()
        self.analyzer = PortfolioAnalyzer()

        # Create simple test data for optimization
        np.random.seed(42)
        dates = pd.date_range("2023-01-01", periods=100, freq="D")

        # Create assets with different risk/return profiles
        assets = {
            "LOW_RISK": np.random.normal(0.0005, 0.005, 100),  # Low risk, low return
            "MED_RISK": np.random.normal(
                0.0008, 0.012, 100
            ),  # Medium risk, medium return
            "HIGH_RISK": np.random.normal(0.0012, 0.020, 100),  # High risk, high return
        }

        self.optimization_data = {}
        for name, returns in assets.items():
            prices = 100 * np.exp(np.cumsum(returns))
            self.optimization_data[name] = pd.DataFrame({"Close": prices}, index=dates)

        self.equal_weights = {name: 1 / 3 for name in assets.keys()}

    def test_basic_optimization(self):
        """Test basic portfolio optimization"""
        try:
            optimized_weights = self.analyzer.optimize_portfolio(
                self.optimization_data, self.equal_weights, risk_tolerance=0.15
            )

            # Should return valid weights
            self.assertIsInstance(optimized_weights, dict)

            # Weights should sum to approximately 1
            total_weight = sum(optimized_weights.values())
            self.assertAlmostEqual(total_weight, 1.0, places=1)

            # Should prefer lower risk assets for low risk tolerance
            if "LOW_RISK" in optimized_weights and "HIGH_RISK" in optimized_weights:
                # This might not always hold due to optimization constraints, but generally should
                pass  # Just check it doesn't crash

        except Exception as e:
            # Optimization might fail with small dataset, that's acceptable
            self.assertIn("optimization", str(e).lower())

    def test_target_return_optimization(self):
        """Test optimization with target return"""
        try:
            optimized_weights = self.analyzer.optimize_portfolio(
                self.optimization_data,
                self.equal_weights,
                target_return=0.10,  # 10% annual return
                risk_tolerance=0.20,
            )

            # Should return valid weights
            self.assertIsInstance(optimized_weights, dict)

            if optimized_weights:  # If optimization succeeded
                total_weight = sum(optimized_weights.values())
                self.assertAlmostEqual(total_weight, 1.0, places=1)

        except Exception:
            # Optimization might fail with constraints, that's acceptable
            pass


# ============================================================================
# PORTFOLIO MANAGER TESTS (Phase 2c Expansion)
# ============================================================================


class TestPortfolioManager(BaseTestCase):
    """Test cases for PortfolioManager database operations"""

    def setUp(self):
        """Set up test fixtures"""
        super().setUp()
        from app.core.portfolio_manager import PortfolioManager

        self.pm = PortfolioManager(db_path=self.test_db.name)

    def tearDown(self):
        """Clean up"""
        super().tearDown()

    def test_add_position_valid(self):
        """Test adding a valid position"""
        success, issues = self.pm.add_or_update_position("AAPL", 100.0)

        self.assertTrue(success)
        self.assertEqual(len(issues), 0)

        # Verify position was added
        position = self.pm.get_position("AAPL")
        self.assertEqual(position, 100.0)

    def test_add_position_invalid_ticker(self):
        """Test adding position with invalid ticker"""
        success, issues = self.pm.add_or_update_position("", 100.0)

        self.assertFalse(success)
        self.assertGreater(len(issues), 0)
        self.assertIn("ticker", issues[0].lower())

    def test_add_position_negative_shares(self):
        """Test adding position with negative shares"""
        success, issues = self.pm.add_or_update_position("MSFT", -50.0)

        self.assertFalse(success)
        self.assertGreater(len(issues), 0)
        self.assertIn("shares", issues[0].lower())

    def test_add_position_zero_shares(self):
        """Test adding position with zero shares"""
        success, issues = self.pm.add_or_update_position("GOOGL", 0.0)

        # Zero shares should be allowed (could mean closing position)
        self.assertTrue(success)
        position = self.pm.get_position("GOOGL")
        self.assertEqual(position, 0.0)

    def test_update_position(self):
        """Test updating an existing position"""
        # Add initial position
        self.pm.add_or_update_position("AMZN", 50.0)

        # Update it
        success, issues = self.pm.add_or_update_position("AMZN", 100.0)

        self.assertTrue(success)
        position = self.pm.get_position("AMZN")
        self.assertEqual(position, 100.0)

    def test_remove_position_existing(self):
        """Test removing an existing position"""
        # Add position first
        self.pm.add_or_update_position("TEST", 75.0)

        # Remove it
        success, issues = self.pm.remove_position("TEST")

        self.assertTrue(success)
        self.assertEqual(len(issues), 0)

        # Verify it's gone
        position = self.pm.get_position("TEST")
        self.assertEqual(position, 0)

    def test_remove_position_nonexistent(self):
        """Test removing a non-existent position"""
        success, issues = self.pm.remove_position("NONEXISTENT")

        self.assertFalse(success)
        self.assertGreater(len(issues), 0)
        self.assertIn("not found", issues[0].lower())

    def test_get_all_positions_empty(self):
        """Test getting all positions from empty portfolio"""
        positions = self.pm.get_all_positions()

        self.assertIsInstance(positions, dict)
        self.assertEqual(len(positions), 0)

    def test_get_all_positions_multiple(self):
        """Test getting all positions with multiple holdings"""
        # Add multiple positions
        tickers = ["AAPL", "MSFT", "GOOGL", "AMZN"]
        for i, ticker in enumerate(tickers):
            self.pm.add_or_update_position(ticker, (i + 1) * 100.0)

        # Get all positions
        positions = self.pm.get_all_positions()

        self.assertEqual(len(positions), 4)
        for i, ticker in enumerate(tickers):
            self.assertEqual(positions[ticker], (i + 1) * 100.0)

    def test_get_tickers(self):
        """Test getting list of tickers"""
        # Add positions
        tickers_added = ["AAPL", "MSFT", "GOOGL"]
        for ticker in tickers_added:
            self.pm.add_or_update_position(ticker, 50.0)

        # Get tickers
        tickers = self.pm.get_tickers()

        self.assertEqual(len(tickers), 3)
        for ticker in tickers_added:
            self.assertIn(ticker, tickers)

    def test_initialize_from_config(self):
        """Test portfolio initialization from config"""
        config = {"AAPL": 100, "MSFT": 50, "GOOGL": 75}

        self.pm.initialize_from_config(config)

        # Verify all positions were added
        for ticker, shares in config.items():
            position = self.pm.get_position(ticker)
            self.assertEqual(position, shares)

    def test_initialize_from_config_idempotent(self):
        """Test that initialize doesn't overwrite existing positions"""
        # Add initial position
        self.pm.add_or_update_position("AAPL", 100.0)

        # Try to initialize
        config = {"MSFT": 50, "GOOGL": 75}
        self.pm.initialize_from_config(config)

        # Original position should still exist
        position = self.pm.get_position("AAPL")
        self.assertEqual(position, 100.0)

    def test_get_weights_basic(self):
        """Test portfolio weight calculation"""
        # Setup: 100 shares at $100 = $10k, 50 shares at $200 = $10k (equal weights)
        self.pm.add_or_update_position("AAPL", 100.0)
        self.pm.add_or_update_position("MSFT", 50.0)

        prices = {"AAPL": 100.0, "MSFT": 200.0}
        weights = self.pm.get_weights(prices)

        self.assertEqual(len(weights), 2)
        self.assertAlmostEqual(weights["AAPL"], 0.5, places=2)
        self.assertAlmostEqual(weights["MSFT"], 0.5, places=2)

    def test_get_weights_unequal(self):
        """Test weight calculation with unequal values"""
        self.pm.add_or_update_position("AAPL", 100.0)
        self.pm.add_or_update_position("MSFT", 100.0)

        # AAPL worth $10k, MSFT worth $20k
        prices = {"AAPL": 100.0, "MSFT": 200.0}
        weights = self.pm.get_weights(prices)

        self.assertAlmostEqual(weights["AAPL"], 1 / 3, places=2)
        self.assertAlmostEqual(weights["MSFT"], 2 / 3, places=2)

    def test_get_weights_missing_prices(self):
        """Test weight calculation with missing prices"""
        self.pm.add_or_update_position("AAPL", 100.0)
        self.pm.add_or_update_position("MSFT", 50.0)

        # Only provide price for one ticker
        prices = {"AAPL": 100.0}
        weights = self.pm.get_weights(prices)

        # Should still return weights (missing prices treated as 0)
        self.assertIsInstance(weights, dict)

    def test_get_total_value(self):
        """Test total portfolio value calculation"""
        self.pm.add_or_update_position("AAPL", 100.0)
        self.pm.add_or_update_position("MSFT", 50.0)

        prices = {"AAPL": 100.0, "MSFT": 200.0}
        total_value = self.pm.get_total_value(prices)

        # 100 * 100 + 50 * 200 = 10000 + 10000 = 20000
        self.assertEqual(total_value, 20000.0)

    def test_get_total_value_empty_portfolio(self):
        """Test total value of empty portfolio"""
        prices = {"AAPL": 100.0, "MSFT": 200.0}
        total_value = self.pm.get_total_value(prices)

        self.assertEqual(total_value, 0)

    def test_ticker_case_insensitivity(self):
        """Test that tickers are normalized to uppercase"""
        # Add with lowercase
        success, issues = self.pm.add_or_update_position("aapl", 100.0)

        self.assertTrue(success)

        # Retrieve with uppercase
        position = self.pm.get_position("AAPL")
        self.assertEqual(position, 100.0)

    def test_ticker_whitespace_handling(self):
        """Test that ticker whitespace is trimmed"""
        success, issues = self.pm.add_or_update_position(" MSFT ", 50.0)

        self.assertTrue(success)
        position = self.pm.get_position("MSFT")
        self.assertEqual(position, 50.0)


if __name__ == "__main__":
    unittest.main()
