from httpx import AsyncClient


async def test_list_indices_empty(async_client: AsyncClient) -> None:
    response = await async_client.get("/indices")

    assert response.status_code == 200
    assert response.json() == []


async def test_create_and_get_index(async_client: AsyncClient) -> None:
    create_response = await async_client.post(
        "/indices",
        json={"name": "CAC 40", "isin": "FR0003500008"},
    )

    assert create_response.status_code == 201
    body = create_response.json()
    assert body["name"] == "CAC 40"
    assert body["isin"] == "FR0003500008"

    get_response = await async_client.get(f"/indices/{body['id']}")
    assert get_response.status_code == 200
    assert get_response.json()["id"] == body["id"]


async def test_duplicate_isin_returns_409(async_client: AsyncClient) -> None:
    payload = {"name": "CAC 40", "isin": "FR0003500008"}
    await async_client.post("/indices", json=payload)

    response = await async_client.post(
        "/indices",
        json={"name": "CAC 40 Duplicate", "isin": "FR0003500008"},
    )

    assert response.status_code == 409
