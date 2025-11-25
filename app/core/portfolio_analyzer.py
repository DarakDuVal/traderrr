"""
app/core/portfolio_analyzer.py - Advanced portfolio analysis and risk management
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Tuple, Optional
from datetime import datetime, timedelta
import logging
from dataclasses import dataclass
from scipy import stats
from scipy.optimize import minimize


@dataclass
class PortfolioMetrics:
    total_value: float
    daily_return: float
    volatility: float
    sharpe_ratio: float
    max_drawdown: float
    beta: float
    alpha: float
    value_at_risk: float
    expected_shortfall: float
    correlation_risk: float


@dataclass
class PositionRisk:
    ticker: str
    position_size: float
    weight: float
    daily_var: float
    contribution_to_risk: float
    liquidity_score: float
    concentration_risk: float


class PortfolioAnalyzer:
    """
    Comprehensive portfolio analysis with risk metrics and optimization
    """

    def __init__(self, risk_free_rate: float = 0.02):
        self.risk_free_rate = risk_free_rate
        self.logger = logging.getLogger(__name__)

    def analyze_portfolio(
        self,
        portfolio_data: Dict[str, pd.DataFrame],
        portfolio_weights: Dict[str, float],
        benchmark_ticker: str = "SPY",
    ) -> PortfolioMetrics:
        """
        Comprehensive portfolio analysis

        Args:
            portfolio_data: Dict mapping ticker to price DataFrame
            portfolio_weights: Dict mapping ticker to portfolio weight
            benchmark_ticker: Benchmark for beta calculation

        Returns:
            PortfolioMetrics object
        """
        try:
            # Align all data to common dates
            aligned_data = self._align_portfolio_data(portfolio_data)

            if aligned_data.empty:
                raise ValueError("No aligned data available")

            # Calculate portfolio returns
            portfolio_returns = self._calculate_portfolio_returns(
                aligned_data, portfolio_weights
            )

            # Get benchmark returns
            benchmark_returns = None
            if benchmark_ticker in aligned_data.columns:
                benchmark_returns = aligned_data[benchmark_ticker].pct_change().dropna()

            # Calculate metrics
            metrics = self._calculate_portfolio_metrics(
                portfolio_returns, benchmark_returns
            )

            return metrics

        except Exception as e:
            self.logger.error(f"Portfolio analysis error: {e}")
            raise

    def calculate_position_risks(
        self,
        portfolio_data: Dict[str, pd.DataFrame],
        portfolio_weights: Dict[str, float],
        portfolio_value: float,
    ) -> List[PositionRisk]:
        """Calculate risk metrics for individual positions"""
        position_risks = []

        try:
            aligned_data = self._align_portfolio_data(portfolio_data)
            returns_data = aligned_data.pct_change().dropna()

            for ticker, weight in portfolio_weights.items():
                if ticker not in returns_data.columns:
                    continue

                position_size = portfolio_value * weight
                ticker_returns = returns_data[ticker]

                # Calculate VaR (95% confidence)
                daily_var = np.percentile(ticker_returns, 5) * position_size

                # Liquidity score (based on volume and volatility)
                liquidity_score = self._calculate_liquidity_score(
                    portfolio_data.get(ticker)
                )

                # Concentration risk
                concentration_risk = self._calculate_concentration_risk(weight)

                # Contribution to portfolio risk
                portfolio_returns = self._calculate_portfolio_returns(
                    aligned_data, portfolio_weights
                )
                contribution_to_risk = self._calculate_risk_contribution(
                    ticker_returns, portfolio_returns, weight
                )

                position_risk = PositionRisk(
                    ticker=ticker,
                    position_size=position_size,
                    weight=weight,
                    daily_var=daily_var,
                    contribution_to_risk=contribution_to_risk,
                    liquidity_score=liquidity_score,
                    concentration_risk=concentration_risk,
                )

                position_risks.append(position_risk)

            # Sort by risk contribution
            position_risks.sort(key=lambda x: x.contribution_to_risk, reverse=True)

            return position_risks

        except Exception as e:
            self.logger.error(f"Position risk calculation error: {e}")
            return []

    def optimize_portfolio(
        self,
        portfolio_data: Dict[str, pd.DataFrame],
        current_weights: Dict[str, float],
        target_return: Optional[float] = None,
        risk_tolerance: float = 0.15,
    ) -> Dict[str, float]:
        """
        Portfolio optimization using Modern Portfolio Theory

        Args:
            portfolio_data: Historical price data
            current_weights: Current portfolio weights
            target_return: Target annual return (if None, maximize Sharpe ratio)
            risk_tolerance: Maximum acceptable volatility

        Returns:
            Optimized portfolio weights
        """
        try:
            aligned_data = self._align_portfolio_data(portfolio_data)
            returns_data = aligned_data.pct_change().dropna()

            if len(returns_data) < 30:
                self.logger.warning("Insufficient data for optimization")
                return current_weights

            # Calculate expected returns and covariance matrix
            expected_returns = returns_data.mean() * 252  # Annualized
            cov_matrix = returns_data.cov() * 252  # Annualized

            # Number of assets
            n_assets = len(expected_returns)
            tickers = list(expected_returns.index)

            # Optimization constraints
            constraints = [
                {"type": "eq", "fun": lambda x: np.sum(x) - 1.0},  # Weights sum to 1
            ]

            # Add target return constraint if specified
            if target_return is not None:
                constraints.append(
                    {
                        "type": "eq",
                        "fun": lambda x: np.dot(x, expected_returns) - target_return,
                    }
                )

            # Bounds for weights (0% to 30% per asset to avoid concentration)
            bounds = [(0.0, 0.3) for _ in range(n_assets)]

            # Initial guess (equal weights)
            x0 = np.array([1.0 / n_assets] * n_assets)

            if target_return is None:
                # Maximize Sharpe ratio
                def objective(weights):
                    portfolio_return = np.dot(weights, expected_returns)
                    portfolio_vol = np.sqrt(
                        np.dot(weights, np.dot(cov_matrix, weights))
                    )
                    return -(portfolio_return - self.risk_free_rate) / portfolio_vol

            else:
                # Minimize variance
                def objective(weights):
                    return np.dot(weights, np.dot(cov_matrix, weights))

            # Add risk tolerance constraint
            def risk_constraint(weights):
                portfolio_vol = np.sqrt(np.dot(weights, np.dot(cov_matrix, weights)))
                return risk_tolerance - portfolio_vol

            constraints.append({"type": "ineq", "fun": risk_constraint})

            # Perform optimization
            result = minimize(
                objective, x0, method="SLSQP", bounds=bounds, constraints=constraints
            )

            if result.success:
                optimized_weights = dict(zip(tickers, result.x))
                # Filter out negligible weights
                optimized_weights = {
                    ticker: weight
                    for ticker, weight in optimized_weights.items()
                    if weight > 0.01
                }

                self.logger.info("Portfolio optimization successful")
                return optimized_weights
            else:
                self.logger.warning(
                    "Portfolio optimization failed, returning current weights"
                )
                return current_weights

        except Exception as e:
            self.logger.error(f"Portfolio optimization error: {e}")
            return current_weights

    def calculate_correlation_matrix(
        self, portfolio_data: Dict[str, pd.DataFrame]
    ) -> pd.DataFrame:
        """Calculate correlation matrix for portfolio assets"""
        try:
            aligned_data = self._align_portfolio_data(portfolio_data)
            returns_data = aligned_data.pct_change().dropna()

            correlation_matrix = returns_data.corr()
            return correlation_matrix

        except Exception as e:
            self.logger.error(f"Correlation calculation error: {e}")
            return pd.DataFrame()

    def generate_risk_report(
        self,
        portfolio_data: Dict[str, pd.DataFrame],
        portfolio_weights: Dict[str, float],
        portfolio_value: float,
    ) -> Dict:
        """Generate comprehensive risk report"""
        try:
            # Portfolio-level metrics
            portfolio_metrics = self.analyze_portfolio(
                portfolio_data, portfolio_weights
            )

            # Position-level risks
            position_risks = self.calculate_position_risks(
                portfolio_data, portfolio_weights, portfolio_value
            )

            # Correlation analysis
            correlation_matrix = self.calculate_correlation_matrix(portfolio_data)

            # Sector concentration
            sector_concentration = self._analyze_sector_concentration(portfolio_weights)

            # Stress testing
            stress_scenarios = self._run_stress_tests(portfolio_data, portfolio_weights)

            # Risk recommendations
            recommendations = self._generate_risk_recommendations(
                portfolio_metrics, position_risks, correlation_matrix
            )

            report = {
                "timestamp": datetime.now().isoformat(),
                "portfolio_metrics": {
                    "total_value": portfolio_metrics.total_value,
                    "daily_return": portfolio_metrics.daily_return,
                    "volatility": portfolio_metrics.volatility,
                    "sharpe_ratio": portfolio_metrics.sharpe_ratio,
                    "max_drawdown": portfolio_metrics.max_drawdown,
                    "value_at_risk": portfolio_metrics.value_at_risk,
                    "expected_shortfall": portfolio_metrics.expected_shortfall,
                },
                "position_risks": [
                    {
                        "ticker": pos.ticker,
                        "weight": pos.weight,
                        "daily_var": pos.daily_var,
                        "contribution_to_risk": pos.contribution_to_risk,
                        "liquidity_score": pos.liquidity_score,
                        "concentration_risk": pos.concentration_risk,
                    }
                    for pos in position_risks
                ],
                "correlation_summary": {
                    "average_correlation": correlation_matrix.values[
                        np.triu_indices_from(correlation_matrix.values, k=1)
                    ].mean(),
                    "max_correlation": correlation_matrix.values[
                        np.triu_indices_from(correlation_matrix.values, k=1)
                    ].max(),
                    "highly_correlated_pairs": self._find_highly_correlated_pairs(
                        correlation_matrix
                    ),
                },
                "sector_concentration": sector_concentration,
                "stress_scenarios": stress_scenarios,
                "recommendations": recommendations,
            }

            return report

        except Exception as e:
            self.logger.error(f"Risk report generation error: {e}")
            return {"error": str(e)}

    def _align_portfolio_data(
        self, portfolio_data: Dict[str, pd.DataFrame]
    ) -> pd.DataFrame:
        """Align portfolio data to common date index"""
        price_data = {}

        for ticker, data in portfolio_data.items():
            if "Close" in data.columns and not data.empty:
                price_data[ticker] = data["Close"]

        if not price_data:
            return pd.DataFrame()

        aligned_df = pd.DataFrame(price_data)
        aligned_df = aligned_df.dropna()  # Remove rows with any NaN values

        return aligned_df

    def _calculate_portfolio_returns(
        self, aligned_data: pd.DataFrame, weights: Dict[str, float]
    ) -> pd.Series:
        """Calculate portfolio returns"""
        returns_data = aligned_data.pct_change().dropna()

        # Align weights with available data
        available_tickers = [
            ticker for ticker in weights.keys() if ticker in returns_data.columns
        ]
        total_weight = sum(weights[ticker] for ticker in available_tickers)

        if total_weight == 0:
            raise ValueError("No valid weights for available tickers")

        # Normalize weights
        normalized_weights = {
            ticker: weights[ticker] / total_weight for ticker in available_tickers
        }

        # Calculate weighted returns
        portfolio_returns = pd.Series(0.0, index=returns_data.index)
        for ticker, weight in normalized_weights.items():
            portfolio_returns += returns_data[ticker] * weight

        return portfolio_returns

    def _calculate_portfolio_metrics(
        self,
        portfolio_returns: pd.Series,
        benchmark_returns: Optional[pd.Series] = None,
    ) -> PortfolioMetrics:
        """Calculate comprehensive portfolio metrics"""

        # Basic metrics
        daily_return = portfolio_returns.mean()
        volatility = portfolio_returns.std() * np.sqrt(252)  # Annualized
        annual_return = daily_return * 252

        # Sharpe ratio
        sharpe_ratio = (
            (annual_return - self.risk_free_rate) / volatility if volatility > 0 else 0
        )

        # Maximum drawdown
        cumulative_returns = (1 + portfolio_returns).cumprod()
        rolling_max = cumulative_returns.expanding().max()
        drawdowns = (cumulative_returns - rolling_max) / rolling_max
        max_drawdown = drawdowns.min()

        # Value at Risk (95% confidence)
        value_at_risk = np.percentile(portfolio_returns, 5)

        # Expected Shortfall (Conditional VaR)
        expected_shortfall = portfolio_returns[
            portfolio_returns <= value_at_risk
        ].mean()

        # Beta and Alpha (if benchmark available)
        beta = 0.0
        alpha = 0.0
        if benchmark_returns is not None and len(benchmark_returns) > 30:
            # Align returns
            aligned_returns = pd.DataFrame(
                {"portfolio": portfolio_returns, "benchmark": benchmark_returns}
            ).dropna()

            if len(aligned_returns) > 30:
                beta, alpha_intercept, r_value, p_value, std_err = stats.linregress(
                    aligned_returns["benchmark"], aligned_returns["portfolio"]
                )
                alpha = alpha_intercept * 252  # Annualized

        # Correlation risk (average correlation with other assets)
        correlation_risk = 0.5  # Placeholder - would need broader market data

        return PortfolioMetrics(
            total_value=0.0,  # To be set externally
            daily_return=daily_return,
            volatility=volatility,
            sharpe_ratio=sharpe_ratio,
            max_drawdown=max_drawdown,
            beta=beta,
            alpha=alpha,
            value_at_risk=value_at_risk,
            expected_shortfall=expected_shortfall,
            correlation_risk=correlation_risk,
        )

    def _calculate_liquidity_score(self, price_data: Optional[pd.DataFrame]) -> float:
        """Calculate liquidity score based on volume and price volatility"""
        if price_data is None or price_data.empty or "Volume" not in price_data.columns:
            return 0.5  # Neutral score

        try:
            # Average daily volume (higher is more liquid)
            avg_volume = price_data["Volume"].mean()
            volume_score = min(1.0, avg_volume / 1000000)  # Normalize to millions

            # Price stability (lower volatility is more liquid)
            price_volatility = price_data["Close"].pct_change().std()
            stability_score = max(0.0, 1.0 - price_volatility * 50)  # Scale volatility

            # Combine scores
            liquidity_score = volume_score * 0.6 + stability_score * 0.4
            return np.clip(liquidity_score, 0.0, 1.0)

        except Exception:
            return 0.5

    def _calculate_concentration_risk(self, weight: float) -> float:
        """Calculate concentration risk for a position"""
        # Risk increases exponentially with weight
        if weight < 0.05:
            return 0.1  # Low risk
        elif weight < 0.10:
            return 0.3  # Medium risk
        elif weight < 0.20:
            return 0.6  # High risk
        else:
            return 1.0  # Very high risk

    def _calculate_risk_contribution(
        self, asset_returns: pd.Series, portfolio_returns: pd.Series, weight: float
    ) -> float:
        """Calculate asset's contribution to portfolio risk"""
        try:
            # Calculate correlation with portfolio
            correlation = asset_returns.corr(portfolio_returns)

            # Asset volatility
            asset_vol = asset_returns.std()

            # Portfolio volatility
            portfolio_vol = portfolio_returns.std()

            # Marginal contribution to risk
            marginal_contribution = correlation * asset_vol / portfolio_vol

            # Risk contribution = weight * marginal contribution
            risk_contribution = weight * marginal_contribution

            return risk_contribution

        except Exception:
            return 0.0

    def _analyze_sector_concentration(
        self, portfolio_weights: Dict[str, float]
    ) -> Dict:
        """Analyze sector concentration (simplified mapping)"""
        # Simplified sector mapping - in production, use proper sector data
        sector_mapping = {
            "AAPL": "Technology",
            "MSFT": "Technology",
            "GOOGL": "Technology",
            "META": "Technology",
            "NVDA": "Technology",
            "JPM": "Financial",
            "BAC": "Financial",
            "PG": "Consumer Staples",
            "JNJ": "Healthcare",
            "KO": "Consumer Staples",
            "VTI": "Diversified",
            "SPY": "Diversified",
            "SIEGY": "Industrial",
            "VWAGY": "Auto",
            "SYIEY": "Consumer Goods",
            "BYDDY": "Auto",
            "QTUM": "Technology",
            "QBTS": "Technology",
        }

        sector_weights = {}
        for ticker, weight in portfolio_weights.items():
            sector = sector_mapping.get(ticker, "Other")
            sector_weights[sector] = sector_weights.get(sector, 0) + weight

        # Calculate concentration risk
        max_sector_weight = max(sector_weights.values()) if sector_weights else 0
        concentration_risk = (
            "High"
            if max_sector_weight > 0.4
            else "Medium" if max_sector_weight > 0.25 else "Low"
        )

        return {
            "sector_weights": sector_weights,
            "max_sector_weight": max_sector_weight,
            "concentration_risk": concentration_risk,
        }

    def _run_stress_tests(
        self,
        portfolio_data: Dict[str, pd.DataFrame],
        portfolio_weights: Dict[str, float],
    ) -> Dict:
        """Run stress test scenarios"""
        try:
            aligned_data = self._align_portfolio_data(portfolio_data)
            portfolio_returns = self._calculate_portfolio_returns(
                aligned_data, portfolio_weights
            )

            scenarios = {
                "market_crash_10": np.percentile(portfolio_returns, 1)
                * 10,  # 1% worst day * 10
                "market_crash_20": np.percentile(portfolio_returns, 1)
                * 20,  # 1% worst day * 20
                "high_volatility": portfolio_returns.std() * 3,  # 3-sigma move
                "correlation_breakdown": portfolio_returns.std()
                * 2,  # 2-sigma with correlation increase
            }

            return scenarios

        except Exception as e:
            self.logger.error(f"Stress test error: {e}")
            return {}

    def _find_highly_correlated_pairs(
        self, correlation_matrix: pd.DataFrame
    ) -> List[Dict]:
        """Find highly correlated asset pairs"""
        highly_correlated = []

        try:
            for i in range(len(correlation_matrix.columns)):
                for j in range(i + 1, len(correlation_matrix.columns)):
                    corr = correlation_matrix.iloc[i, j]
                    if abs(corr) > 0.7:  # High correlation threshold
                        highly_correlated.append(
                            {
                                "asset1": correlation_matrix.columns[i],
                                "asset2": correlation_matrix.columns[j],
                                "correlation": corr,
                            }
                        )

        except Exception as e:
            self.logger.error(f"Correlation analysis error: {e}")

        return highly_correlated

    def _generate_risk_recommendations(
        self,
        portfolio_metrics: PortfolioMetrics,
        position_risks: List[PositionRisk],
        correlation_matrix: pd.DataFrame,
    ) -> List[str]:
        """Generate risk management recommendations"""
        recommendations = []

        # Volatility check
        if portfolio_metrics.volatility > 0.25:
            recommendations.append(
                "Portfolio volatility is high. Consider reducing position sizes or adding defensive assets."
            )

        # Sharpe ratio check
        if portfolio_metrics.sharpe_ratio < 0.5:
            recommendations.append(
                "Sharpe ratio is low. Review asset selection and consider rebalancing."
            )

        # Maximum drawdown check
        if portfolio_metrics.max_drawdown < -0.20:
            recommendations.append(
                "Maximum drawdown exceeds 20%. Implement stronger risk controls."
            )

        # Concentration risk
        high_concentration_positions = [
            pos for pos in position_risks if pos.concentration_risk > 0.6
        ]
        if high_concentration_positions:
            tickers = [pos.ticker for pos in high_concentration_positions]
            recommendations.append(
                f"High concentration risk in: {', '.join(tickers)}. Consider reducing position sizes."
            )

        # Liquidity risk
        low_liquidity_positions = [
            pos for pos in position_risks if pos.liquidity_score < 0.3
        ]
        if low_liquidity_positions:
            tickers = [pos.ticker for pos in low_liquidity_positions]
            recommendations.append(
                f"Low liquidity in: {', '.join(tickers)}. Monitor for exit opportunities."
            )

        # Correlation risk
        if not correlation_matrix.empty:
            avg_correlation = correlation_matrix.values[
                np.triu_indices_from(correlation_matrix.values, k=1)
            ].mean()
            if avg_correlation > 0.6:
                recommendations.append(
                    "High average correlation detected. Increase diversification across uncorrelated assets."
                )

        # Default recommendation
        if not recommendations:
            recommendations.append(
                "Portfolio risk profile appears balanced. Continue monitoring."
            )

        return recommendations
