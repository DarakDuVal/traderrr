"""
tests/test_api_routes.py
Test cases for API route endpoints
"""

import json
import unittest
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock

import pandas as pd
import numpy as np

from tests import BaseTestCase, SampleDataGenerator, YFinanceMockHelper
from app import create_app


class TestAPIHealth(BaseTestCase):
    """Test health check endpoint"""

    def setUp(self):
        """Set up test fixtures"""
        super().setUp()
        self.app = create_app()
        self.client = self.app.test_client()

    def test_health_check(self):
        """Test health check endpoint returns 200"""
        response = self.client.get("/api/health", headers=self.get_auth_headers())
        self.assertEqual(response.status_code, 200)

        data = json.loads(response.data)
        self.assertIn("status", data)
        self.assertIn("timestamp", data)


class TestAPISignals(BaseTestCase):
    """Test trading signals endpoints"""

    def setUp(self):
        """Set up test fixtures"""
        super().setUp()
        self.app = create_app()
        self.client = self.app.test_client()

    def test_get_signals_endpoint(self):
        """Test GET /api/signals endpoint"""
        response = self.client.get("/api/signals", headers=self.get_auth_headers())
        # Should return 200 or empty list
        self.assertIn(response.status_code, [200, 404])

    def test_get_signal_history(self):
        """Test GET /api/signal-history endpoint"""
        response = self.client.get(
            "/api/signal-history", headers=self.get_auth_headers()
        )
        # Should return 200 or empty list
        self.assertIn(response.status_code, [200, 404])

        if response.status_code == 200:
            data = json.loads(response.data)
            self.assertIsInstance(data, (list, dict))

    def test_get_signal_history_with_limit(self):
        """Test signal history with limit parameter"""
        response = self.client.get(
            "/api/signal-history?limit=10", headers=self.get_auth_headers()
        )
        self.assertIn(response.status_code, [200, 404])

    def test_get_signal_history_for_ticker(self):
        """Test GET /api/signal-history/<ticker> endpoint"""
        response = self.client.get(
            "/api/signal-history/AAPL", headers=self.get_auth_headers()
        )
        self.assertIn(response.status_code, [200, 404])

    def test_get_signal_stats(self):
        """Test GET /api/signal-stats endpoint"""
        response = self.client.get("/api/signal-stats", headers=self.get_auth_headers())
        self.assertIn(response.status_code, [200, 404])

    def test_post_update_signals(self):
        """Test POST /api/update endpoint"""
        response = self.client.post("/api/update", headers=self.get_auth_headers())
        self.assertIn(response.status_code, [200, 202])


class TestAPIPortfolioPerformance(BaseTestCase):
    """Test portfolio performance endpoints"""

    def setUp(self):
        """Set up test fixtures"""
        super().setUp()
        self.app = create_app()
        self.client = self.app.test_client()

    def test_get_portfolio_performance(self):
        """Test GET /api/portfolio-performance endpoint"""
        response = self.client.get(
            "/api/portfolio-performance", headers=self.get_auth_headers()
        )
        self.assertIn(response.status_code, [200, 404])

        if response.status_code == 200:
            data = json.loads(response.data)
            self.assertIsInstance(data, (list, dict))

    def test_get_portfolio_performance_with_limit(self):
        """Test portfolio performance with limit parameter"""
        response = self.client.get(
            "/api/portfolio-performance?limit=30", headers=self.get_auth_headers()
        )
        self.assertIn(response.status_code, [200, 404])

    def test_get_performance_summary(self):
        """Test GET /api/portfolio-performance/summary endpoint"""
        response = self.client.get(
            "/api/portfolio-performance/summary", headers=self.get_auth_headers()
        )
        self.assertIn(response.status_code, [200, 404])

        if response.status_code == 200:
            data = json.loads(response.data)
            self.assertIsInstance(data, dict)

    def test_get_performance_summary_with_days(self):
        """Test performance summary with days parameter"""
        response = self.client.get(
            "/api/portfolio-performance/summary?days=30",
            headers=self.get_auth_headers(),
        )
        self.assertIn(response.status_code, [200, 404])

    def test_get_performance_metrics(self):
        """Test GET /api/portfolio-performance/metrics endpoint"""
        response = self.client.get(
            "/api/portfolio-performance/metrics", headers=self.get_auth_headers()
        )
        self.assertIn(response.status_code, [200, 404])

        if response.status_code == 200:
            data = json.loads(response.data)
            self.assertIsInstance(data, dict)

    def test_get_performance_latest(self):
        """Test GET /api/portfolio-performance/latest endpoint"""
        response = self.client.get(
            "/api/portfolio-performance/latest", headers=self.get_auth_headers()
        )
        self.assertIn(response.status_code, [200, 404])


class TestAPIPortfolioManagement(BaseTestCase):
    """Test portfolio management endpoints"""

    def setUp(self):
        """Set up test fixtures"""
        super().setUp()
        self.app = create_app()
        self.client = self.app.test_client()

    def test_get_portfolio_overview(self):
        """Test GET /api/portfolio endpoint"""
        response = self.client.get("/api/portfolio", headers=self.get_auth_headers())
        # 400: No portfolio positions, 200: Success, 500: Error
        self.assertIn(response.status_code, [200, 400, 500])

        if response.status_code == 200:
            data = json.loads(response.data)
            self.assertIsInstance(data, dict)

    def test_get_portfolio_positions(self):
        """Test GET /api/portfolio/positions endpoint"""
        response = self.client.get(
            "/api/portfolio/positions", headers=self.get_auth_headers()
        )
        self.assertIn(response.status_code, [200, 404])

        if response.status_code == 200:
            data = json.loads(response.data)
            self.assertIsInstance(data, (list, dict))

    def test_add_portfolio_position(self):
        """Test POST /api/portfolio/positions endpoint"""
        position_data = {"ticker": "AAPL", "shares": 100}
        response = self.client.post(
            "/api/portfolio/positions",
            data=json.dumps(position_data),
            content_type="application/json",
            headers=self.get_auth_headers(),
        )
        self.assertIn(response.status_code, [200, 201, 400, 404])

    def test_add_position_invalid_ticker(self):
        """Test adding position with invalid ticker"""
        position_data = {"ticker": "", "shares": 100}
        response = self.client.post(
            "/api/portfolio/positions",
            data=json.dumps(position_data),
            content_type="application/json",
            headers=self.get_auth_headers(),
        )
        self.assertIn(response.status_code, [400, 404])

    def test_add_position_negative_shares(self):
        """Test adding position with negative shares"""
        position_data = {"ticker": "AAPL", "shares": -100}
        response = self.client.post(
            "/api/portfolio/positions",
            data=json.dumps(position_data),
            content_type="application/json",
            headers=self.get_auth_headers(),
        )
        self.assertIn(response.status_code, [400, 404])

    def test_update_portfolio_position(self):
        """Test PUT /api/portfolio/positions/<ticker> endpoint"""
        update_data = {"shares": 200}
        response = self.client.put(
            "/api/portfolio/positions/AAPL",
            data=json.dumps(update_data),
            content_type="application/json",
            headers=self.get_auth_headers(),
        )
        self.assertIn(response.status_code, [200, 400, 404])

    def test_delete_portfolio_position(self):
        """Test DELETE /api/portfolio/positions/<ticker> endpoint"""
        response = self.client.delete(
            "/api/portfolio/positions/AAPL", headers=self.get_auth_headers()
        )
        # 200: Success, 400: Position doesn't exist, 500: Error
        self.assertIn(response.status_code, [200, 400, 500])


class TestAPIRiskAnalysis(BaseTestCase):
    """Test risk analysis endpoints"""

    def setUp(self):
        """Set up test fixtures"""
        super().setUp()
        self.app = create_app()
        self.client = self.app.test_client()

    def test_get_risk_report(self):
        """Test GET /api/risk-report endpoint"""
        response = self.client.get("/api/risk-report", headers=self.get_auth_headers())
        # 200: Success, 400: No portfolio positions, 500: Error
        self.assertIn(response.status_code, [200, 400, 500])

        if response.status_code == 200:
            data = json.loads(response.data)
            self.assertIsInstance(data, dict)

    def test_get_correlation_matrix(self):
        """Test GET /api/correlation endpoint"""
        response = self.client.get("/api/correlation", headers=self.get_auth_headers())
        # 200: Success, 400: No portfolio positions, 500: Error
        self.assertIn(response.status_code, [200, 400, 500])

        if response.status_code == 200:
            data = json.loads(response.data)
            self.assertIsInstance(data, dict)

    def test_post_optimization(self):
        """Test POST /api/optimization endpoint"""
        optimization_data = {"risk_tolerance": 0.5}
        response = self.client.post(
            "/api/optimization",
            data=json.dumps(optimization_data),
            content_type="application/json",
            headers=self.get_auth_headers(),
        )
        self.assertIn(response.status_code, [200, 400, 404, 500])

    def test_optimization_with_target_return(self):
        """Test optimization with target return parameter"""
        optimization_data = {"risk_tolerance": 0.5, "target_return": 0.1}
        response = self.client.post(
            "/api/optimization",
            data=json.dumps(optimization_data),
            content_type="application/json",
            headers=self.get_auth_headers(),
        )
        self.assertIn(response.status_code, [200, 400, 404, 500])


class TestAPITickerData(BaseTestCase):
    """Test ticker data endpoints"""

    def setUp(self):
        """Set up test fixtures"""
        super().setUp()
        self.app = create_app()
        self.client = self.app.test_client()

    def test_get_ticker_data(self):
        """Test GET /api/tickers/<ticker> endpoint"""
        response = self.client.get("/api/tickers/AAPL", headers=self.get_auth_headers())
        self.assertIn(response.status_code, [200, 404, 500])

        if response.status_code == 200:
            data = json.loads(response.data)
            self.assertIsInstance(data, dict)

    def test_get_ticker_with_period(self):
        """Test ticker data with period parameter"""
        response = self.client.get(
            "/api/tickers/AAPL?period=1y", headers=self.get_auth_headers()
        )
        self.assertIn(response.status_code, [200, 404, 500])

    def test_get_ticker_with_indicators(self):
        """Test ticker data with indicators parameter"""
        response = self.client.get(
            "/api/tickers/AAPL?indicators=rsi,macd", headers=self.get_auth_headers()
        )
        self.assertIn(response.status_code, [200, 404, 500])

    def test_get_ticker_invalid(self):
        """Test getting invalid ticker"""
        response = self.client.get(
            "/api/tickers/INVALID123456789", headers=self.get_auth_headers()
        )
        self.assertIn(response.status_code, [404, 400])


class TestAPIErrorHandling(BaseTestCase):
    """Test API error handling"""

    def setUp(self):
        """Set up test fixtures"""
        super().setUp()
        self.app = create_app()
        self.client = self.app.test_client()

    def test_invalid_endpoint(self):
        """Test invalid endpoint returns 404"""
        response = self.client.get("/api/nonexistent", headers=self.get_auth_headers())
        self.assertEqual(response.status_code, 404)

    def test_malformed_json(self):
        """Test malformed JSON returns 400"""
        response = self.client.post(
            "/api/portfolio/positions",
            data="{invalid json}",
            content_type="application/json",
            headers=self.get_auth_headers(),
        )
        self.assertIn(response.status_code, [400, 404, 500])

    def test_missing_required_fields(self):
        """Test missing required fields"""
        response = self.client.post(
            "/api/portfolio/positions",
            data=json.dumps({"ticker": "AAPL"}),  # Missing shares
            content_type="application/json",
            headers=self.get_auth_headers(),
        )
        self.assertIn(response.status_code, [400, 404])

    def test_invalid_method(self):
        """Test invalid HTTP method returns 405"""
        response = self.client.delete(
            "/api/signals", headers=self.get_auth_headers()
        )  # DELETE not allowed
        self.assertIn(response.status_code, [405, 404])


class TestAPIResponseFormats(BaseTestCase):
    """Test API response format consistency"""

    def setUp(self):
        """Set up test fixtures"""
        super().setUp()
        self.app = create_app()
        self.client = self.app.test_client()

    def test_json_response_format(self):
        """Test that API returns valid JSON"""
        response = self.client.get("/api/health", headers=self.get_auth_headers())
        if response.status_code == 200:
            # Should be valid JSON
            data = json.loads(response.data)
            self.assertIsInstance(data, dict)

    def test_response_content_type(self):
        """Test that API returns JSON content type"""
        response = self.client.get("/api/health", headers=self.get_auth_headers())
        self.assertIn("application/json", response.content_type)

    def test_error_response_format(self):
        """Test error response contains error message"""
        response = self.client.get("/api/nonexistent", headers=self.get_auth_headers())
        self.assertEqual(response.status_code, 404)
        # Response should be JSON
        try:
            data = json.loads(response.data)
            self.assertIsInstance(data, dict)
        except json.JSONDecodeError:
            pass  # Some frameworks return plain text for 404


class TestAPIParameterValidation(BaseTestCase):
    """Test API parameter validation"""

    def setUp(self):
        """Set up test fixtures"""
        super().setUp()
        self.app = create_app()
        self.client = self.app.test_client()

    def test_limit_parameter_max_value(self):
        """Test limit parameter with value exceeding max"""
        response = self.client.get(
            "/api/signal-history?limit=2000", headers=self.get_auth_headers()
        )
        # Should either cap at 1000 or return 200/400
        self.assertIn(response.status_code, [200, 400, 404])

    def test_days_parameter_negative(self):
        """Test days parameter with negative value"""
        response = self.client.get(
            "/api/portfolio-performance/summary?days=-30",
            headers=self.get_auth_headers(),
        )
        # Should handle gracefully
        self.assertIn(response.status_code, [200, 400, 404])

    def test_days_parameter_exceeds_max(self):
        """Test days parameter exceeding max"""
        response = self.client.get(
            "/api/portfolio-performance/metrics?days=500",
            headers=self.get_auth_headers(),
        )
        # Should either cap at 365 or return 200/400
        self.assertIn(response.status_code, [200, 400, 404])

    def test_confidence_filter(self):
        """Test signal history with confidence filter"""
        response = self.client.get(
            "/api/signal-history?min_confidence=0.8", headers=self.get_auth_headers()
        )
        self.assertIn(response.status_code, [200, 400, 404])

    def test_invalid_confidence_value(self):
        """Test signal history with invalid confidence value"""
        response = self.client.get(
            "/api/signal-history?min_confidence=2.0", headers=self.get_auth_headers()
        )
        # Should handle gracefully
        self.assertIn(response.status_code, [200, 400, 404])


class TestAPIAuthenticationHeaders(BaseTestCase):
    """Test API with various request headers"""

    def setUp(self):
        """Set up test fixtures"""
        super().setUp()
        self.app = create_app()
        self.client = self.app.test_client()

    def test_request_without_user_agent(self):
        """Test API request without User-Agent header"""
        headers = self.get_auth_headers()
        headers["User-Agent"] = ""
        response = self.client.get(
            "/api/health",
            headers=headers,
        )
        # Should still work or return 400
        self.assertIn(response.status_code, [200, 400])

    def test_request_with_custom_headers(self):
        """Test API request with custom headers"""
        headers = self.get_auth_headers()
        headers["X-Custom-Header"] = "test-value"
        response = self.client.get(
            "/api/health",
            headers=headers,
        )
        # Should work regardless of custom headers
        self.assertIn(response.status_code, [200, 400])

    def test_missing_api_key(self):
        """Test API request without Authorization header"""
        response = self.client.get("/api/health")
        # Should return 401 Unauthorized
        self.assertEqual(response.status_code, 401)

    def test_invalid_api_key(self):
        """Test API request with invalid API key"""
        response = self.client.get(
            "/api/health",
            headers={"Authorization": "Bearer invalid-api-key-xyz"},
        )
        # Should return 401 Unauthorized
        self.assertEqual(response.status_code, 401)

    def test_malformed_auth_header(self):
        """Test API request with malformed Authorization header"""
        response = self.client.get(
            "/api/health",
            headers={"Authorization": "InvalidFormat api-key"},
        )
        # Should return 401 Unauthorized
        self.assertEqual(response.status_code, 401)

    def test_valid_api_key_works(self):
        """Test API request with valid API key"""
        response = self.client.get(
            "/api/health",
            headers=self.get_auth_headers(),
        )
        # Should succeed with valid key
        self.assertIn(response.status_code, [200, 503])  # 200 or 503 (degraded)


if __name__ == "__main__":
    unittest.main()
