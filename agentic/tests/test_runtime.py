import pytest
from httpx import ASGITransport, AsyncClient
from nam_agentic.main import app
from nam_agentic.schemas.events import EventType


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.mark.asyncio
async def test_health():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/health")
    assert response.status_code == 200
    assert response.json()["service"] == "nam-agentic"


@pytest.mark.asyncio
async def test_events_accepted():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        payload = {"market": "EU", "phase": "PRE_OPEN"}
        response = await client.post(
            "/events",
            json={"type": EventType.MARKET_SESSION, "payload": payload},
        )
    assert response.status_code == 202
    assert response.json()["status"] == "accepted"
