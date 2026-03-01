"""Tests for the /ws WebSocket endpoint."""

import pytest
from fastapi.testclient import TestClient
from app.auth.service import create_access_token
from tests.conftest import _TEST_SECRET


class TestWebSocket:
    def test_ws_rejects_missing_token(self, client):
        with pytest.raises(Exception):
            with client.websocket_connect("/ws"):
                pass

    def test_ws_rejects_invalid_token(self, client):
        with pytest.raises(Exception):
            with client.websocket_connect("/ws?token=bad"):
                pass

    def test_ws_connects_with_valid_token(self, client, test_user):
        token = create_access_token(
            test_user.id, test_user.role.name, _TEST_SECRET, 60
        )
        with client.websocket_connect(f"/ws?token={token}") as ws:
            # Connection succeeded — just close gracefully
            pass
