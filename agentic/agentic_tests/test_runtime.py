from contextlib import asynccontextmanager

from nam_agentic.main import _wire_runtime, create_app
from langchain_core.messages import AIMessage, HumanMessage, ToolMessage

from nam_agentic.runner import (
    _StreamState,
    _libelle_outil,
    _needs_delegation_nudge,
    _needs_synthesis_nudge,
)
from nam_agentic.services.chat_messages import (
    MIN_POST_TASK_SYNTHESIS_CHARS,
    sanitize_stream_token,
    sanitize_user_text,
    text_claims_missing_market_data_access,
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
    cleaned = sanitize_stream_token(raw)
    assert cleaned == "J'ai effectué les recherches"


def test_sanitize_stream_token_keeps_text_when_no_prose_boundary() -> None:
    raw = "PositionItem(name='ENGI') — allocation défensive recommandée."
    cleaned = sanitize_stream_token(raw)
    assert cleaned == raw


def test_needs_synthesis_nudge_after_expert_tasks() -> None:
    state = _StreamState(task_rounds=2)
    messages: list = []
    assert _needs_synthesis_nudge("", state, messages) is True
    synthesis = "Your portfolio is well diversified. I suggest holding current allocations."
    assert _needs_synthesis_nudge(synthesis, state, messages) is True


def test_needs_synthesis_nudge_skipped_for_long_report() -> None:
    state = _StreamState(task_rounds=1, last_task_result_chars=8000)
    report = "x" * 2100
    messages: list = []
    assert _needs_synthesis_nudge(report, state, messages) is False


def test_needs_synthesis_nudge_after_short_post_task_stub() -> None:
    state = _StreamState(task_rounds=1, last_task_result_chars=5000)
    stub = (
        "I am orchestrating the full analysis now. Please give me a moment "
        "while I compile the comprehensive report."
    )
    assert _needs_synthesis_nudge(stub, state, []) is True


def test_needs_synthesis_nudge_on_async_wait_fiction_followup() -> None:
    state = _StreamState(task_rounds=0)
    fiction = (
        "Je suis en attente de la restitution du sous-agent sector-analyst. "
        "Je ne peux rien faire de plus tant que je n'ai pas reçu les données."
    )
    messages = [
        HumanMessage(content="Analyse STM"),
        AIMessage(content="", tool_calls=[{"name": "task", "args": {}, "id": "1"}]),
        ToolMessage(content="Rapport détaillé STM." * 100, tool_call_id="1", name="task"),
        AIMessage(content="Please give me a moment while I compile the report."),
        HumanMessage(content="alors ? ça prend pas 2h ?"),
    ]
    assert _needs_synthesis_nudge(fiction, state, messages) is True


def test_needs_synthesis_nudge_skipped_without_task() -> None:
    state = _StreamState(tool_rounds=3)
    messages: list = []
    assert _needs_synthesis_nudge("", state, messages) is False
    assert _needs_synthesis_nudge("Réponse finale actionnable.", state, messages) is False


def test_needs_delegation_nudge_when_empty_without_task() -> None:
    state = _StreamState(tool_rounds=2, tools_called={"get_user_context"})
    assert _needs_delegation_nudge("", state) is True
    assert _needs_delegation_nudge("Synthèse complète.", state) is False


def test_needs_delegation_nudge_skipped_after_task() -> None:
    state = _StreamState(task_rounds=1)
    assert _needs_delegation_nudge("", state) is False


def test_needs_delegation_nudge_when_pm_claims_no_price_api() -> None:
    state = _StreamState(task_rounds=0)
    fiction = (
        "Je ne peux pas vous fournir de prix en temps réel. "
        "Je n'ai pas d'API de données de marché en temps réel."
    )
    assert _needs_delegation_nudge(fiction, state) is True


def test_needs_delegation_nudge_skipped_after_substantive_non_fiction_reply() -> None:
    state = _StreamState(task_rounds=0)
    assert _needs_delegation_nudge("Le marché US est fermé ce soir.", state) is False


def test_text_claims_missing_market_data_access_import() -> None:
    assert text_claims_missing_market_data_access("no real-time market data API") is True


def test_prepare_user_text_strips_uuid_and_latex() -> None:
    raw = (
        "Analyse persistée UUID('439a4786-3f38-4edd-bf3e-68770e2dbf53'). "
        "Profil $\\text{GROWTH}$ sur 20 ans."
    )
    cleaned = sanitize_user_text(raw)
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
