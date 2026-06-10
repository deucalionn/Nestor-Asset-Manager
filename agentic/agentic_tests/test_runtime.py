from contextlib import asynccontextmanager

from nam_agentic.main import _wire_runtime, create_app
from nam_agentic.runner import (
    _StreamState,
    _libelle_outil,
    _looks_like_plan_preamble,
    _needs_synthesis_nudge,
    _prepare_user_text,
    _sanitize_stream_token,
)
from nam_agentic.schemas.chat import ChatStreamEvent
from nam_agentic.schemas.events import EventType
from nam_agentic.services.event_handler import EventHandler
from starlette.testclient import TestClient


class StubRunner:
    async def stream_events(self, *_args, **_kwargs):
        yield ChatStreamEvent(type="status", status="thinking")
        yield ChatStreamEvent(type="status", status="writing")
        yield ChatStreamEvent(type="token", content="Hello")
        yield ChatStreamEvent(type="token", content=" Nestor")


def test_health() -> None:
    from nam_agentic.main import app

    with TestClient(app) as client:
        response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["service"] == "nam-agentic"


def test_events_accepted() -> None:
    from nam_agentic.main import app

    async def noop_handle(_event) -> None:
        return None

    with TestClient(app) as client:
        client.app.state.event_handler.handle = noop_handle
        response = client.post(
            "/events",
            json={
                "type": EventType.NEWS_INGEST_SESSION,
                "payload": {"market": "EU"},
            },
        )
    assert response.status_code == 202
    assert response.json()["status"] == "accepted"


def test_chat_stream_ndjson() -> None:
    runner = StubRunner()
    handler = EventHandler(agent_runner=runner)  # type: ignore[arg-type]
    app = create_app()

    @asynccontextmanager
    async def stub_lifespan(application):
        _wire_runtime(application, runner, handler)
        yield

    app.router.lifespan_context = stub_lifespan

    with TestClient(app) as client:
        response = client.post("/chat/stream", json={"content": "Bonjour"})

    assert response.status_code == 200
    lines = [line for line in response.text.splitlines() if line.strip()]
    assert any("token" in line for line in lines)
    assert any("done" in line for line in lines)


def test_sanitize_stream_token_strips_tool_dump_prefix() -> None:
    raw = (
        "yahoo_symbol='STLAM.MI' items=[YahooNewsItem(title='Tilray')] count=5 "
        "resolved_from_db=TrueJ'ai effectué les recherches"
    )
    cleaned = _sanitize_stream_token(raw)
    assert cleaned == "J'ai effectué les recherches"


def test_sanitize_stream_token_keeps_text_when_no_prose_boundary() -> None:
    raw = "PositionItem(name='ENGI') — allocation défensive recommandée."
    cleaned = _sanitize_stream_token(raw)
    assert cleaned == raw


def test_needs_synthesis_nudge_after_expert_tasks() -> None:
    state = _StreamState(task_rounds=2)
    preamble = (
        "Afin de procéder à cette analyse complète, je vais commencer par établir un plan."
    )
    assert _needs_synthesis_nudge(preamble, state) is True
    assert _needs_synthesis_nudge("", state) is True
    synthesis = "Votre portefeuille est bien diversifié. Pour les 300 €, je recommande ..."
    assert _needs_synthesis_nudge(synthesis, state) is False


def test_needs_synthesis_nudge_after_tools_without_task() -> None:
    state = _StreamState(tool_rounds=3)
    assert _needs_synthesis_nudge("", state) is True
    assert _needs_synthesis_nudge("Réponse finale actionnable.", state) is False


def test_looks_like_plan_preamble() -> None:
    assert _looks_like_plan_preamble("Afin de procéder, je vais établir un plan d'action") is True
    assert _looks_like_plan_preamble("Votre portefeuille présente une surpondération tech.") is False


def test_prepare_user_text_strips_uuid_and_latex() -> None:
    raw = (
        "Analyse persistée UUID('439a4786-3f38-4edd-bf3e-68770e2dbf53'). "
        "Profil $\\text{GROWTH}$ sur 20 ans."
    )
    cleaned = _prepare_user_text(raw)
    assert cleaned is not None
    assert "UUID" not in cleaned
    assert "439a4786" not in cleaned
    assert "GROWTH" in cleaned
    assert "$" not in cleaned


def test_libelle_outil_for_subagent() -> None:
    label = _libelle_outil(
        {"name": "task", "args": {"subagent_type": "macro-strategist", "description": "x"}}
    )
    assert label == "Analyse macro en cours"
