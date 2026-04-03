"""API 엔드포인트 테스트"""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_health(client: AsyncClient):
    resp = await client.get("/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"


@pytest.mark.asyncio
async def test_list_races(client: AsyncClient):
    resp = await client.get("/api/races")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 2


@pytest.mark.asyncio
async def test_list_races_by_track(client: AsyncClient):
    resp = await client.get("/api/races", params={"track": "S"})
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 2  # both races are track_id=1 (Seoul)


@pytest.mark.asyncio
async def test_list_races_by_date(client: AsyncClient):
    resp = await client.get("/api/races", params={"date": "2025-04-19"})
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 1
    assert data[0]["race_number"] == 3


@pytest.mark.asyncio
async def test_get_race(client: AsyncClient):
    resp = await client.get("/api/races/1")
    assert resp.status_code == 200
    data = resp.json()
    assert data["distance"] == 1400


@pytest.mark.asyncio
async def test_get_race_entries(client: AsyncClient):
    resp = await client.get("/api/races/1/entries")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 3
    # Should be ordered by horse_number
    numbers = [e["horse_number"] for e in data]
    assert numbers == sorted(numbers)


@pytest.mark.asyncio
async def test_get_synergy(client: AsyncClient):
    resp = await client.get(
        "/api/synergy", params={"jockeyId": 1, "trainerId": 1, "horseId": 1}
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "best_record_rate" in data
    assert data["jockey_name"] == "김동수"


@pytest.mark.asyncio
async def test_get_race_synergies(client: AsyncClient):
    resp = await client.get("/api/synergy/race/1")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 3


@pytest.mark.asyncio
async def test_run_prediction(client: AsyncClient):
    resp = await client.post("/api/predictions/race/1/run")
    assert resp.status_code == 200
    data = resp.json()
    assert data["race_id"] == 1
    preds = data["predictions"]
    assert len(preds) == 3
    assert preds[0]["predicted_rank"] == 1


@pytest.mark.asyncio
async def test_get_predictions_after_run(client: AsyncClient):
    # First run prediction
    await client.post("/api/predictions/race/1/run")
    # Then get
    resp = await client.get("/api/predictions/race/1")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 3
