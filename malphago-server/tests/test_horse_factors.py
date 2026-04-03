"""Phase 2 신규 분석 요인 테스트"""

import pytest
from httpx import AsyncClient


# ──────────────── Horse Factors via Prediction ────────────────

@pytest.mark.asyncio
async def test_prediction_uses_new_factors(client: AsyncClient):
    """예측 실행 시 Phase 2 신규 요인이 포함되는지 확인"""
    resp = await client.post("/api/predictions/race/1/run")
    assert resp.status_code == 200
    data = resp.json()
    preds = data["predictions"]
    assert len(preds) > 0

    factors = preds[0]["factors"]
    # Phase 2 신규 요인 존재 확인
    assert "surface_aptitude" in factors
    assert "class_movement" in factors
    assert "running_style_match" in factors
    assert "horse_weight_factor" in factors
    assert "class_trick" in factors
    assert "jockey_fatigue" in factors

    # 모든 요인이 0~100 범위
    for key, value in factors.items():
        assert 0 <= value <= 100, f"{key}={value} out of range"


@pytest.mark.asyncio
async def test_model_version_v2(client: AsyncClient):
    """모델 버전이 v2로 업데이트되었는지 확인"""
    await client.post("/api/predictions/race/1/run")
    resp = await client.get("/api/predictions/race/1")
    assert resp.status_code == 200
    preds = resp.json()
    assert preds[0]["model_version"] == "weighted_linear_v2"


# ──────────────── Class Trick Detection API ────────────────

@pytest.mark.asyncio
async def test_class_trick_api(client: AsyncClient):
    """등급 꼼수 감지 API"""
    resp = await client.get("/api/analysis/horse/1/class-trick")
    assert resp.status_code == 200
    data = resp.json()
    assert "is_suspected" in data
    assert "score" in data
    assert "reason" in data
    assert isinstance(data["is_suspected"], bool)
    assert 0 <= data["score"] <= 100


# ──────────────── Unit-level factor tests ────────────────

@pytest.mark.asyncio
async def test_surface_aptitude_no_data(db_session):
    """주로적성 — 데이터 없을 때 기본값"""
    from app.services.horse_factors import calc_surface_aptitude
    score = await calc_surface_aptitude(db_session, 999, "잔디", None)
    assert score == 50.0


@pytest.mark.asyncio
async def test_class_movement_no_data(db_session):
    """등급이동 — 데이터 없을 때 기본값"""
    from app.services.horse_factors import calc_class_movement
    score = await calc_class_movement(db_session, 999, "국3")
    assert score == 50.0


@pytest.mark.asyncio
async def test_running_style_match_no_data(db_session):
    """각질매칭 — 데이터 없을 때 기본값"""
    from app.services.horse_factors import calc_running_style_matching
    score = await calc_running_style_matching(db_session, 999, None, 1400)
    assert score == 50.0


@pytest.mark.asyncio
async def test_horse_weight_factor_no_data(db_session):
    """마체중변동 — 데이터 없을 때 기본값"""
    from app.services.horse_factors import calc_horse_weight_factor
    score = await calc_horse_weight_factor(db_session, 999)
    assert score == 50.0


@pytest.mark.asyncio
async def test_jockey_fatigue_no_data(db_session):
    """기수피로도 — 데이터 없을 때 기본값"""
    from datetime import date
    from app.services.jockey_factors import calc_jockey_fatigue
    score = await calc_jockey_fatigue(db_session, 999, date(2025, 4, 19), 3, 1)
    assert score == 70.0


@pytest.mark.asyncio
async def test_jockey_fatigue_none_jockey(db_session):
    """기수피로도 — 기수 없을 때"""
    from datetime import date
    from app.services.jockey_factors import calc_jockey_fatigue
    score = await calc_jockey_fatigue(db_session, None, date(2025, 4, 19), 3, 1)
    assert score == 50.0


def test_apprentice_bonus():
    """수습기수 부담중량 보정"""
    from app.services.jockey_factors import calc_apprentice_bonus
    assert calc_apprentice_bonus("52") == 80.0
    assert calc_apprentice_bonus("57") == 45.0
    assert calc_apprentice_bonus(None) == 50.0


@pytest.mark.asyncio
async def test_class_trick_no_data(db_session):
    """등급꼼수 — 데이터 없을 때"""
    from app.services.class_trick_detector import detect_class_trick
    result = await detect_class_trick(db_session, 999)
    assert not result["is_suspected"]
    assert result["score"] == 0.0
