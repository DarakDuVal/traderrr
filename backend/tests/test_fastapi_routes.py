"""Tests for /api/v1/ route endpoints (signals, portfolio, risk, admin)."""

import pytest


class TestSignalsRoutes:
    def test_list_signals_requires_auth(self, client):
        resp = client.get("/api/v1/signals")
        assert resp.status_code in (401, 403)

    def test_list_signals_authenticated(self, client, auth_headers):
        resp = client.get("/api/v1/signals", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert "signals" in data
        assert "total" in data

    def test_signals_by_ticker(self, client, auth_headers):
        resp = client.get("/api/v1/signals/AAPL", headers=auth_headers)
        assert resp.status_code == 200

    def test_generate_signals_requires_admin(self, client, auth_headers):
        # Regular user should get 403
        resp = client.post("/api/v1/signals/generate", headers=auth_headers)
        assert resp.status_code == 403


class TestPortfolioRoutes:
    def test_get_portfolio_requires_auth(self, client):
        resp = client.get("/api/v1/portfolio")
        assert resp.status_code in (401, 403)

    def test_get_portfolio_empty(self, client, auth_headers):
        resp = client.get("/api/v1/portfolio", headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json() == []

    def test_add_position(self, client, auth_headers):
        resp = client.post(
            "/api/v1/portfolio/positions",
            json={"ticker": "AAPL", "shares": 10.0},
            headers=auth_headers,
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["ticker"] == "AAPL"
        assert data["shares"] == 10.0

    def test_update_position(self, client, auth_headers):
        # First create
        resp = client.post(
            "/api/v1/portfolio/positions",
            json={"ticker": "MSFT", "shares": 5.0},
            headers=auth_headers,
        )
        pos_id = resp.json()["id"]

        # Then update
        resp = client.put(
            f"/api/v1/portfolio/positions/{pos_id}",
            json={"shares": 15.0},
            headers=auth_headers,
        )
        assert resp.status_code == 200
        assert resp.json()["shares"] == 15.0

    def test_delete_position(self, client, auth_headers):
        # Create
        resp = client.post(
            "/api/v1/portfolio/positions",
            json={"ticker": "GOOGL", "shares": 3.0},
            headers=auth_headers,
        )
        pos_id = resp.json()["id"]

        # Delete
        resp = client.delete(
            f"/api/v1/portfolio/positions/{pos_id}",
            headers=auth_headers,
        )
        assert resp.status_code == 204

    def test_get_performance(self, client, auth_headers):
        resp = client.get("/api/v1/portfolio/performance", headers=auth_headers)
        assert resp.status_code == 200


class TestRiskRoutes:
    def test_risk_metrics(self, client, auth_headers):
        resp = client.get("/api/v1/risk/metrics", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert "var_95" in data

    def test_correlation(self, client, auth_headers):
        resp = client.get("/api/v1/risk/correlation", headers=auth_headers)
        assert resp.status_code == 200

    def test_stress_test(self, client, auth_headers):
        resp = client.post(
            "/api/v1/risk/stress-test",
            json={
                "scenario": "market_crash",
                "market_change": -0.20,
                "volatility_multiplier": 2.0,
            },
            headers=auth_headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["scenario"] == "market_crash"


class TestAdminRoutes:
    def test_list_users_requires_admin(self, client, auth_headers):
        # Regular user should get 403
        resp = client.get("/api/v1/admin/users", headers=auth_headers)
        assert resp.status_code == 403

    def test_list_users_as_admin(self, client, admin_headers):
        resp = client.get("/api/v1/admin/users", headers=admin_headers)
        assert resp.status_code == 200
        users = resp.json()
        assert isinstance(users, list)
        assert len(users) >= 1

    def test_system_status_requires_admin(self, client, auth_headers):
        resp = client.get("/api/v1/admin/system", headers=auth_headers)
        assert resp.status_code == 403

    def test_system_status_as_admin(self, client, admin_headers):
        resp = client.get("/api/v1/admin/system", headers=admin_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert "cpu_percent" in data
