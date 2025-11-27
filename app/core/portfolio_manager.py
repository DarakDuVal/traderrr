"""
app/core/portfolio_manager.py - Portfolio position management with database
"""

import sqlite3
from typing import Dict, List, Tuple


class PortfolioManager:
    """Manages portfolio positions in the database"""

    def __init__(self, db_path: str):
        self.db_path = db_path

    def _get_connection(self) -> sqlite3.Connection:
        """Get database connection"""
        return sqlite3.connect(self.db_path)

    def add_or_update_position(
        self, ticker: str, shares: float
    ) -> Tuple[bool, List[str]]:
        """Add or update a portfolio position. Returns (success, issues)"""
        # Validate input
        issues = []

        if not isinstance(ticker, str) or not ticker.strip():
            issues.append("Invalid ticker")
            return False, issues

        if not isinstance(shares, (int, float)) or shares < 0:
            issues.append("Shares must be a non-negative number")
            return False, issues

        ticker = ticker.upper().strip()

        try:
            conn = self._get_connection()
            cursor = conn.cursor()

            # Use INSERT OR REPLACE for upsert behavior (ticker is PRIMARY KEY)
            cursor.execute(
                """
                INSERT OR REPLACE INTO portfolio_positions (ticker, shares, updated_at)
                VALUES (?, ?, CURRENT_TIMESTAMP)
                """,
                (ticker, float(shares)),
            )

            conn.commit()
            conn.close()
            return True, []

        except Exception as e:
            return False, [f"Database error: {str(e)}"]

    def remove_position(self, ticker: str) -> Tuple[bool, List[str]]:
        """Remove a portfolio position. Returns (success, issues)"""
        ticker = ticker.upper().strip()

        try:
            conn = self._get_connection()
            cursor = conn.cursor()

            cursor.execute(
                "DELETE FROM portfolio_positions WHERE ticker = ?", (ticker,)
            )
            if cursor.rowcount == 0:
                conn.close()
                return False, [f"Position {ticker} not found"]

            conn.commit()
            conn.close()
            return True, []

        except Exception as e:
            return False, [f"Database error: {str(e)}"]

    def get_all_positions(self) -> Dict[str, float]:
        """Get all portfolio positions as {ticker: shares}"""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()

            cursor.execute(
                "SELECT ticker, shares FROM portfolio_positions ORDER BY ticker"
            )
            positions = {row[0]: row[1] for row in cursor.fetchall()}

            conn.close()
            return positions

        except Exception as e:
            print(f"Error getting positions: {e}")
            return {}

    def get_position(self, ticker: str) -> float:
        """Get shares for a specific ticker. Returns 0 if not found."""
        ticker = ticker.upper().strip()

        try:
            conn = self._get_connection()
            cursor = conn.cursor()

            cursor.execute(
                "SELECT shares FROM portfolio_positions WHERE ticker = ?", (ticker,)
            )
            result = cursor.fetchone()
            conn.close()

            return result[0] if result else 0

        except Exception as e:
            print(f"Error getting position: {e}")
            return 0

    def get_tickers(self) -> List[str]:
        """Get list of all tickers in portfolio"""
        positions = self.get_all_positions()
        return list(positions.keys())

    def initialize_from_config(self, initial_positions: Dict[str, float]) -> None:
        """Initialize portfolio with positions from config.json (one-time setup)"""
        # Only initialize if no positions exist
        if self.get_all_positions():
            print("Portfolio already initialized, skipping")
            return

        for ticker, shares in initial_positions.items():
            self.add_or_update_position(ticker, shares)

        print(f"Initialized portfolio with {len(initial_positions)} positions")

    def get_weights(self, current_prices: Dict[str, float]) -> Dict[str, float]:
        """Calculate current portfolio weights from positions and prices"""
        positions = self.get_all_positions()

        if not positions or not current_prices:
            return {}

        # Calculate values
        values = {
            ticker: shares * current_prices.get(ticker, 0)
            for ticker, shares in positions.items()
        }

        total_value = sum(values.values())

        if total_value <= 0:
            return {ticker: 0 for ticker in positions}

        return {ticker: value / total_value for ticker, value in values.items()}

    def get_total_value(self, current_prices: Dict[str, float]) -> float:
        """Calculate total portfolio value from positions and prices"""
        positions = self.get_all_positions()

        if not positions or not current_prices:
            return 0

        return sum(
            shares * current_prices.get(ticker, 0)
            for ticker, shares in positions.items()
        )
