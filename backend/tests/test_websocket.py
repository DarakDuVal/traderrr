"""Tests for the /ws WebSocket endpoint."""

import pytest
from unittest.mock import patch
from app.auth.service import create_access_token
from tests.conftest import _TEST_SECRET
from config.settings import Settings


def _ws_test_settings():
    return Settings(
        DATABASE_URL="sqlite+aiosqlite:///dummy.db",
        SECRET_KEY=_TEST_SECRET,
        ENVIRONMENT="testing",
        REDIS_URL="redis://localhost:6379/0",
    )


class TestWebSocket:
    def test_ws_rejects_missing_token(self, client):
        with pytest.raises(Exception):
            with client.websocket_connect("/ws"):
                pass

    def test_ws_rejects_invalid_token(self, client):
        with pytest.raises(Exception):
            with client.websocket_connect("/ws?token=bad"):
                pass

    @patch("app.ws.router.get_settings", _ws_test_settings)
    def test_ws_connects_with_valid_token(self, client, test_user):
        token = create_access_token(
            test_user.id, test_user.role.name, _TEST_SECRET, 60
        )
        with client.websocket_connect(f"/ws?token={token}") as ws:
            # Connection succeeded — just close gracefully
            pass
