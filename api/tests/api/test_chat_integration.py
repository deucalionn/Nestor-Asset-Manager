"""API WebSocket → agentic /chat/stream integration (ASGI in-process, no TCP)."""

import json
from unittest.mock import patch

import httpx
from httpx import ASGITransport
from nam_agentic.main import create_app
from nam_agentic.schemas.chat import ChatStreamEvent
from nam_api.main import app as api_app
from starlette.testclient import TestClient


class StubChatRunner:
    async def stream_events(self, *_args, **_kwargs):
        yield ChatStreamEvent(type="status", status="thinking")
        yield ChatStreamEvent(type="token", content="Bonjour")
        yield ChatStreamEvent(type="status", status="writing")


def _agentic_stack():
    """Agentic FastAPI app + stub runner (no Postgres / lifespan required)."""
    runner = StubChatRunner()
    application = create_app()
    return application, runner


class AgenticHttpxClient(httpx.AsyncClient):
    """Routes HTTP to the in-process agentic ASGI app (replaces real TCP to :8001)."""

    def __init__(self, agentic_app, *args, **kwargs):
        transport = ASGITransport(app=agentic_app)
        super().__init__(transport=transport, base_url="http://agentic.test", *args, **kwargs)


def test_ws_chat_proxies_to_agentic_stream_end_to_end() -> None:
    agentic_app, runner = _agentic_stack()

    def httpx_client_factory(*args, **kwargs):
        return AgenticHttpxClient(agentic_app, *args, **kwargs)

    with patch("nam_agentic.routers.chat.get_agent_runner", return_value=runner):
        with patch("nam_api.websocket.chat.httpx.AsyncClient", side_effect=httpx_client_factory):
            with patch("nam_api.websocket.chat.settings") as mock_settings:
                mock_settings.agentic_url = "http://agentic.test"
                with TestClient(api_app) as client:
                    with client.websocket_connect("/ws/chat") as websocket:
                        websocket.send_text(json.dumps({"content": "Salut Nestor"}))
                        events = [json.loads(websocket.receive_text()) for _ in range(4)]

    types = [event["type"] for event in events]
    assert types == ["status", "token", "status", "done"]
    assert events[1]["content"] == "Bonjour"
    assert events[3]["thread_id"]


def test_ws_chat_two_messages_reuse_thread_id() -> None:
    agentic_app, runner = _agentic_stack()

    def httpx_client_factory(*args, **kwargs):
        return AgenticHttpxClient(agentic_app, *args, **kwargs)

    with patch("nam_agentic.routers.chat.get_agent_runner", return_value=runner):
        with patch("nam_api.websocket.chat.httpx.AsyncClient", side_effect=httpx_client_factory):
            with patch("nam_api.websocket.chat.settings") as mock_settings:
                mock_settings.agentic_url = "http://agentic.test"
                with TestClient(api_app) as client:
                    with client.websocket_connect("/ws/chat") as websocket:
                        websocket.send_text(json.dumps({"content": "Premier message"}))
                        first_batch = [
                            json.loads(websocket.receive_text()) for _ in range(4)
                        ]
                        thread_id = first_batch[-1]["thread_id"]

                        websocket.send_text(
                            json.dumps(
                                {"content": "Deuxième message", "thread_id": thread_id}
                            )
                        )
                        second_batch = [
                            json.loads(websocket.receive_text()) for _ in range(4)
                        ]

    assert first_batch[-1]["type"] == "done"
    assert second_batch[-1]["type"] == "done"
    assert second_batch[-1]["thread_id"] == thread_id
    assert second_batch[1]["content"] == "Bonjour"
