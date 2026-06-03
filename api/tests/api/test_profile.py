from httpx import AsyncClient


async def test_setup_and_get_profile(async_client: AsyncClient) -> None:
    setup = await async_client.post("/setup", json={
        "firstname": "Lucas",
        "date_of_birth": "1990-01-15",
        "strategy": "BALANCED",
        "goals": "Build wealth",
    })

    assert setup.status_code == 201
    body = setup.json()
    assert body["firstname"] == "Lucas"
    assert body["age"] >= 18

    profile = await async_client.get("/profile")
    assert profile.status_code == 200
    assert profile.json()["id"] == body["id"]


async def test_setup_twice_returns_409(async_client: AsyncClient) -> None:
    payload = {
        "firstname": "Lucas",
        "date_of_birth": "1990-01-15",
        "strategy": "BALANCED",
        "goals": "Build wealth",
    }
    await async_client.post("/setup", json=payload)

    response = await async_client.post("/setup", json=payload)
    assert response.status_code == 409


async def test_profile_before_setup_returns_404(async_client: AsyncClient) -> None:
    response = await async_client.get("/profile")
    assert response.status_code == 404


async def test_update_profile(async_client: AsyncClient) -> None:
    await async_client.post("/setup", json={
        "firstname": "Lucas",
        "date_of_birth": "1990-01-15",
        "strategy": "BALANCED",
        "goals": "Old goals",
    })

    response = await async_client.put("/profile", json={"goals": "New goals"})
    assert response.status_code == 200
    assert response.json()["goals"] == "New goals"
