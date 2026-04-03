"""E2E 통합 테스트 — 미커버 API 엔드포인트 전체 테스트

기존 test_api.py가 커버하지 않는 15개 엔드포인트를 테스트.
"""

import pytest
from httpx import AsyncClient


# ──────────────── Horses API ────────────────

@pytest.mark.asyncio
async def test_get_horse(client: AsyncClient):
    resp = await client.get("/api/horses/1")
    assert resp.status_code == 200
    data = resp.json()
    assert data["name"] == "번개호"


@pytest.mark.asyncio
async def test_get_horse_not_found(client: AsyncClient):
    resp = await client.get("/api/horses/999")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_get_horse_stats(client: AsyncClient):
    resp = await client.get("/api/horses/1/stats")
    assert resp.status_code == 200
    data = resp.json()
    assert data["horse_id"] == 1
    assert data["name"] == "번개호"
    assert "total_record" in data
    assert "win_rate" in data
    assert "top3_rate" in data
    assert "distance_breakdown" in data
    assert "recent_races" in data
    # Horse 1 has 2 entries (race1: rank 1, race2: rank 2)
    assert data["win_rate"] > 0


@pytest.mark.asyncio
async def test_get_horse_stats_not_found(client: AsyncClient):
    resp = await client.get("/api/horses/999/stats")
    assert resp.status_code == 404


# ──────────────── Jockeys API ────────────────

@pytest.mark.asyncio
async def test_get_jockey(client: AsyncClient):
    resp = await client.get("/api/jockeys/1")
    assert resp.status_code == 200
    data = resp.json()
    assert data["name"] == "김동수"


@pytest.mark.asyncio
async def test_get_jockey_not_found(client: AsyncClient):
    resp = await client.get("/api/jockeys/999")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_get_jockey_stats(client: AsyncClient):
    resp = await client.get("/api/jockeys/1/stats")
    assert resp.status_code == 200
    data = resp.json()
    assert data["jockey_id"] == 1
    assert data["name"] == "김동수"
    assert "total_record" in data
    assert "win_rate" in data
    assert "distance_breakdown" in data
    assert "track_breakdown" in data
    assert "recent_30_form" in data


@pytest.mark.asyncio
async def test_get_jockey_stats_not_found(client: AsyncClient):
    resp = await client.get("/api/jockeys/999/stats")
    assert resp.status_code == 404


# ──────────────── Analysis API ────────────────

@pytest.mark.asyncio
async def test_get_horse_running_style(client: AsyncClient):
    resp = await client.get("/api/analysis/horse/1/running-style")
    assert resp.status_code == 200
    data = resp.json()
    assert data["horse_id"] == 1
    assert "style" in data
    assert "sample_count" in data


@pytest.mark.asyncio
async def test_get_race_running_styles(client: AsyncClient):
    resp = await client.get("/api/analysis/race/1/running-styles")
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)


# ──────────────── Notifications API ────────────────

@pytest.mark.asyncio
async def test_get_recent_changes_empty(client: AsyncClient):
    """변경 이력이 없을 때 빈 리스트 반환"""
    resp = await client.get("/api/notifications/changes")
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)
    assert len(data) == 0


@pytest.mark.asyncio
async def test_get_recent_changes_with_filters(client: AsyncClient):
    resp = await client.get(
        "/api/notifications/changes",
        params={"track": "S", "date": "2025-04-19", "limit": 10},
    )
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


@pytest.mark.asyncio
async def test_subscribe_to_changes(client: AsyncClient):
    resp = await client.post(
        "/api/notifications/subscribe",
        params={"fcm_token": "test_token_123"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "subscribed"
    assert data["topic"] == "race_changes"


@pytest.mark.asyncio
async def test_unsubscribe_from_changes(client: AsyncClient):
    resp = await client.delete(
        "/api/notifications/unsubscribe",
        params={"fcm_token": "test_token_123"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "unsubscribed"


# ──────────────── Sync API ────────────────

@pytest.mark.asyncio
async def test_sync_delta(client: AsyncClient):
    resp = await client.get(
        "/api/sync/delta",
        params={"since": "2025-01-01T00:00:00"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "races" in data
    assert "change_logs" in data
    # Seed data has 2 races
    assert len(data["races"]) == 2


@pytest.mark.asyncio
async def test_sync_delta_with_track(client: AsyncClient):
    resp = await client.get(
        "/api/sync/delta",
        params={"since": "2025-01-01T00:00:00", "track": "S"},
    )
    assert resp.status_code == 200


# ──────────────── Predictions Override API ────────────────

@pytest.mark.asyncio
async def test_override_prediction(client: AsyncClient):
    resp = await client.post(
        "/api/predictions/override",
        params={"race_id": 1, "entry_id": 1, "new_jockey_id": 2},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["race_id"] == 1
    assert data["entry_id"] == 1
    assert data["new_jockey_id"] == 2


# ──────────────── Cross-endpoint E2E Flow ────────────────

@pytest.mark.asyncio
async def test_full_race_analysis_flow(client: AsyncClient):
    """전체 경주 분석 플로우: 경주 조회 → 출주표 → 말/기수 통계 → 시너지 → 예측"""
    # 1. 경주 목록 조회
    races_resp = await client.get("/api/races")
    assert races_resp.status_code == 200
    races = races_resp.json()
    race_id = races[0]["id"]

    # 2. 출주표 조회
    entries_resp = await client.get(f"/api/races/{race_id}/entries")
    assert entries_resp.status_code == 200
    entries = entries_resp.json()
    assert len(entries) > 0

    horse_id = entries[0].get("horse_id")
    jockey_id = entries[0].get("jockey_id")

    # 3. 말 통계
    if horse_id:
        horse_resp = await client.get(f"/api/horses/{horse_id}/stats")
        assert horse_resp.status_code == 200

    # 4. 기수 통계
    if jockey_id:
        jockey_resp = await client.get(f"/api/jockeys/{jockey_id}/stats")
        assert jockey_resp.status_code == 200

    # 5. 시너지 분석
    synergy_resp = await client.get(f"/api/synergy/race/{race_id}")
    assert synergy_resp.status_code == 200

    # 6. 각질 분석
    styles_resp = await client.get(f"/api/analysis/race/{race_id}/running-styles")
    assert styles_resp.status_code == 200

    # 7. 예측 실행
    predict_resp = await client.post(f"/api/predictions/race/{race_id}/run")
    assert predict_resp.status_code == 200

    # 8. 예측 결과 조회
    results_resp = await client.get(f"/api/predictions/race/{race_id}")
    assert results_resp.status_code == 200
    assert len(results_resp.json()) > 0

    # 9. 동기화 데이터
    sync_resp = await client.get(
        "/api/sync/delta",
        params={"since": "2025-01-01T00:00:00"},
    )
    assert sync_resp.status_code == 200
