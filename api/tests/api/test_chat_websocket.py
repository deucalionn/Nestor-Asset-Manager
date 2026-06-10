import json
from unittest.mock import AsyncMock, MagicMock, patch

from nam_api.main import app
from starlette.testclient import TestClient


def test_chat_websocket_relays_agentic_stream() -> None:
    async def mock_aiter_lines():
        yield json.dumps({"type": "token", "content": "Hi"})
        yield json.dumps({"type": "done", "thread_id": "thread-1"})

    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.aiter_lines = mock_aiter_lines

    mock_stream_ctx = MagicMock()
    mock_stream_ctx.__aenter__ = AsyncMock(return_value=mock_response)
    mock_stream_ctx.__aexit__ = AsyncMock(return_value=None)

    mock_client = MagicMock()
    mock_client.stream = MagicMock(return_value=mock_stream_ctx)
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=None)

    with patch("nam_api.websocket.chat.httpx.AsyncClient", return_value=mock_client):
        with TestClient(app) as client:
            with client.websocket_connect("/ws/chat") as websocket:
                websocket.send_text(json.dumps({"content": "Hello"}))
                first = json.loads(websocket.receive_text())
                second = json.loads(websocket.receive_text())

    assert first["type"] == "token"
    assert first["content"] == "Hi"
    assert second["type"] == "done"
    assert second["thread_id"] == "thread-1"


def test_chat_websocket_errors_when_agentic_stream_truncated() -> None:
    async def mock_aiter_lines():
        yield json.dumps({"type": "status", "status": "thinking"})

    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.aiter_lines = mock_aiter_lines

    mock_stream_ctx = MagicMock()
    mock_stream_ctx.__aenter__ = AsyncMock(return_value=mock_response)
    mock_stream_ctx.__aexit__ = AsyncMock(return_value=None)

    mock_client = MagicMock()
    mock_client.stream = MagicMock(return_value=mock_stream_ctx)
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=None)

    with patch("nam_api.websocket.chat.httpx.AsyncClient", return_value=mock_client):
        with TestClient(app) as client:
            with client.websocket_connect("/ws/chat") as websocket:
                websocket.send_text(json.dumps({"content": "Hello"}))
                first = json.loads(websocket.receive_text())
                second = json.loads(websocket.receive_text())

    assert first["type"] == "status"
    assert second["type"] == "error"
    assert "interrompu" in second["message"]
