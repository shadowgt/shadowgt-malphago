"""예측 서비스 테스트"""

import pytest

from app.services.prediction import (
    WEIGHTS,
    PredictionFactors,
    _calc_gate_position,
    _calc_rest_period,
    _calc_horse_win_rate,
    _calc_distance_aptitude,
    _calc_form_index,
    _calc_jockey_win_rate,
    predict_entry,
    predict_race,
)
from app.models.race_entry import RaceEntry
from app.models.race import Race


class TestWeights:
    def test_weights_sum_to_one(self):
        assert abs(sum(WEIGHTS.values()) - 1.0) < 1e-10

    def test_all_factors_have_weights(self):
        factors = PredictionFactors()
        for key in WEIGHTS:
            assert hasattr(factors, key), f"PredictionFactors missing: {key}"


class TestGatePosition:
    def test_inner_gate_advantage(self):
        """안쪽 마번이 높은 점수"""
        s1 = _calc_gate_position(1, 8)
        s8 = _calc_gate_position(8, 8)
        assert s1 > s8

    def test_none_returns_default(self):
        assert _calc_gate_position(None, 8) == 50.0
        assert _calc_gate_position(1, None) == 50.0


class TestRestPeriod:
    def test_optimal_range(self):
        assert _calc_rest_period(14) == 80.0
        assert _calc_rest_period(28) == 80.0
        assert _calc_rest_period(42) == 80.0

    def test_short_rest(self):
        assert _calc_rest_period(7) == 65.0

    def test_long_rest(self):
        assert _calc_rest_period(60) == 60.0

    def test_very_long_rest(self):
        assert _calc_rest_period(120) == 35.0

    def test_none_returns_default(self):
        assert _calc_rest_period(None) == 50.0


@pytest.mark.asyncio
async def test_horse_win_rate(seeded_session):
    """말 승률: 번개호 id=1 → 2 entries, rank 1 and 2 → top3=2 → 100%"""
    rate = await _calc_horse_win_rate(seeded_session, horse_id=1)
    assert rate == pytest.approx(100.0)


@pytest.mark.asyncio
async def test_horse_win_rate_no_data(seeded_session):
    rate = await _calc_horse_win_rate(seeded_session, horse_id=999)
    assert rate == 50.0


@pytest.mark.asyncio
async def test_distance_aptitude(seeded_session):
    """번개호 at 1400m: race1(1400m, rank=1), race2(1200m, rank=2)
    ±200m range → both count → 2 entries, 2 top3 → 100%"""
    rate = await _calc_distance_aptitude(seeded_session, horse_id=1, target_distance=1400)
    assert rate == pytest.approx(100.0)


@pytest.mark.asyncio
async def test_distance_aptitude_no_match(seeded_session):
    """번개호 at 2000m: no entries within ±200m → 40.0"""
    rate = await _calc_distance_aptitude(seeded_session, horse_id=1, target_distance=2000)
    assert rate == 40.0


@pytest.mark.asyncio
async def test_form_index(seeded_session):
    """번개호: ordered desc by id → id=4 (rank=2, score=80, w=5), id=1 (rank=1, score=100, w=4)
    → (400 + 400) / 9 ≈ 88.9"""
    form = await _calc_form_index(seeded_session, horse_id=1)
    assert form == pytest.approx(88.9, abs=0.1)


@pytest.mark.asyncio
async def test_jockey_win_rate(seeded_session):
    """김동수: 3 entries, 1 win (id=1) → rate=1/3 → scaled ×500 ≈ 166.7 → capped 100"""
    rate = await _calc_jockey_win_rate(seeded_session, jockey_id=1)
    assert rate == 100.0  # capped


@pytest.mark.asyncio
async def test_predict_entry(seeded_session):
    """단일 출주마 예측"""
    entry = await seeded_session.get(RaceEntry, 1)
    race = await seeded_session.get(Race, 1)
    total, factors = await predict_entry(seeded_session, entry, race)

    assert 0 < total <= 100
    assert isinstance(factors, PredictionFactors)
    assert factors.horse_win_rate > 0


@pytest.mark.asyncio
async def test_predict_race(seeded_session):
    """경주 전체 예측"""
    results = await predict_race(seeded_session, race_id=1)

    assert len(results) == 3
    # Check sorted by rank
    ranks = [r["predicted_rank"] for r in results]
    assert ranks == [1, 2, 3]
    # Scores descending
    scores = [r["total_score"] for r in results]
    assert scores == sorted(scores, reverse=True)


@pytest.mark.asyncio
async def test_predict_race_not_found(seeded_session):
    results = await predict_race(seeded_session, race_id=999)
    assert results == []
