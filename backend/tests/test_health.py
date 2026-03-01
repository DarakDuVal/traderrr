"""Tests for the /health endpoint."""

import pytest


class TestHealth:
    def test_health_returns_200(self, client):
        resp = client.get("/health")
        assert resp.status_code == 200

    def test_health_response_shape(self, client):
        data = client.get("/health").json()
        assert "status" in data
        assert data["status"] == "ok"
        assert "db" in data
