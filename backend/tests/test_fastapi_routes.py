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

    def test_list_signals_with_ticker_filter(self, client, auth_headers):
        resp = client.get(
            "/api/v1/signals?ticker=AAPL", headers=auth_headers
        )
        assert resp.status_code == 200

    def test_list_signals_with_type_filter(self, client, auth_headers):
        resp = client.get(
            "/api/v1/signals?signal_type=BUY", headers=auth_headers
        )
        assert resp.status_code == 200

    def test_list_signals_with_confidence_filter(self, client, auth_headers):
        resp = client.get(
            "/api/v1/signals?min_confidence=0.5", headers=auth_headers
        )
        assert resp.status_code == 200

    def test_signals_by_ticker(self, client, auth_headers):
        resp = client.get("/api/v1/signals/AAPL", headers=auth_headers)
        assert resp.status_code == 200

    def test_generate_signals_requires_admin(self, client, auth_headers):
        # Regular user should get 403
        resp = client.post("/api/v1/signals/generate", headers=auth_headers)
        assert resp.status_code == 403

    def test_generate_signals_as_admin(self, client, admin_headers):
        # Admin triggers generation — Celery may not be running so expect 202 or 500
        resp = client.post("/api/v1/signals/generate", headers=admin_headers)
        assert resp.status_code in (202, 500)


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

    def test_update_position_not_found(self, client, auth_headers):
        resp = client.put(
            "/api/v1/portfolio/positions/999999",
            json={"shares": 15.0},
            headers=auth_headers,
        )
        assert resp.status_code == 404

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

    def test_delete_position_not_found(self, client, auth_headers):
        resp = client.delete(
            "/api/v1/portfolio/positions/999999",
            headers=auth_headers,
        )
        assert resp.status_code == 404

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

    def test_create_user_as_admin(self, client, admin_headers):
        resp = client.post(
            "/api/v1/admin/users?username=newuser&email=new@test.com&password=NewPass123&role=user",
            headers=admin_headers,
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["username"] == "newuser"
        assert data["role"] == "user"

    def test_create_user_duplicate(self, client, admin_headers):
        # First create
        client.post(
            "/api/v1/admin/users?username=dupuser&email=dup@test.com&password=DupPass123&role=user",
            headers=admin_headers,
        )
        # Second create — should conflict
        resp = client.post(
            "/api/v1/admin/users?username=dupuser&email=dup@test.com&password=DupPass123&role=user",
            headers=admin_headers,
        )
        assert resp.status_code == 409

    def test_create_user_weak_password(self, client, admin_headers):
        resp = client.post(
            "/api/v1/admin/users?username=weakpw&email=weak@test.com&password=weak&role=user",
            headers=admin_headers,
        )
        assert resp.status_code == 400

    def test_create_user_invalid_role(self, client, admin_headers):
        resp = client.post(
            "/api/v1/admin/users?username=badrole&email=role@test.com&password=RolePass123&role=superadmin",
            headers=admin_headers,
        )
        assert resp.status_code == 400

    def test_deactivate_user_as_admin(self, client, admin_headers):
        # Create a user to deactivate
        resp = client.post(
            "/api/v1/admin/users?username=deactuser&email=deact@test.com&password=DeactPass123&role=user",
            headers=admin_headers,
        )
        user_id = resp.json()["id"]

        resp = client.delete(
            f"/api/v1/admin/users/{user_id}",
            headers=admin_headers,
        )
        assert resp.status_code == 200
        assert "deactivated" in resp.json()["detail"]

    def test_deactivate_user_not_found(self, client, admin_headers):
        resp = client.delete(
            "/api/v1/admin/users/999999",
            headers=admin_headers,
        )
        assert resp.status_code == 404

    def test_system_status_requires_admin(self, client, auth_headers):
        resp = client.get("/api/v1/admin/system", headers=auth_headers)
        assert resp.status_code == 403

    def test_system_status_as_admin(self, client, admin_headers):
        resp = client.get("/api/v1/admin/system", headers=admin_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert "cpu_percent" in data
