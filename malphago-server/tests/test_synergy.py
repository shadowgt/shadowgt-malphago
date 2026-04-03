"""시너지 분석 서비스 테스트"""

import pytest
import pytest_asyncio

from app.services.synergy import calculate_synergy, calculate_race_synergies


@pytest.mark.asyncio
async def test_calculate_synergy_basic(seeded_session):
    """기수-조교사 시너지 기본 계산"""
    report = await calculate_synergy(seeded_session, jockey_id=1, trainer_id=1)

    assert report.jockey_name == "김동수"
    assert report.trainer_name == "이영호"
    # 김동수: 3 entries (id=1 rank=1, id=3 rank=5, id=4 rank=2)
    assert report.jockey_total_runs == 3
    # top3: id=1 (rank=1), id=4 (rank=2) → 2
    assert report.jockey_top3_count == 2
    assert report.best_record_rate == pytest.approx(66.67, abs=0.1)


@pytest.mark.asyncio
async def test_calculate_synergy_trainer_rate(seeded_session):
    """기수-조교사 조합 입상률"""
    report = await calculate_synergy(seeded_session, jockey_id=1, trainer_id=1)

    # top3 with trainer_id=1: id=1 (trainer=1), id=4 (trainer=1) → 2/2
    assert report.best_record_trainer_rate == pytest.approx(100.0)
    assert report.jockey_trainer_runs == 2


@pytest.mark.asyncio
async def test_calculate_synergy_high_dividend(seeded_session):
    """이변 입상률 (인기 4위 이하에서 3위이내)"""
    report = await calculate_synergy(seeded_session, jockey_id=1, trainer_id=1)

    # 김동수 entries:
    #   id=1: rank=1, favor=2 → NOT high dividend (favor <= 3)
    #   id=3: rank=5 → NOT top3
    #   id=4: rank=2, favor=1 → NOT high dividend (favor <= 3)
    assert report.high_dividend_record_rate == pytest.approx(0.0)


@pytest.mark.asyncio
async def test_calculate_synergy_with_horse(seeded_session):
    """말-기수 직접 조합 시너지"""
    report = await calculate_synergy(
        seeded_session, jockey_id=1, trainer_id=1, horse_id=1
    )

    assert report.horse_name == "번개호"
    # horse=1 + jockey=1: entries id=1 (rank=1), id=4 (rank=2) → 2 runs, 2 top3
    assert report.horse_jockey_total_runs == 2
    assert report.horse_jockey_synergy_rate == pytest.approx(100.0)


@pytest.mark.asyncio
async def test_calculate_synergy_trainer_win_rate(seeded_session):
    """조교사 승률"""
    report = await calculate_synergy(seeded_session, jockey_id=1, trainer_id=1)

    # trainer_id=1: entries id=1 (rank=1), id=4 (rank=2) → 1 win / 2 total
    assert report.trainer_win_rate == pytest.approx(50.0)


@pytest.mark.asyncio
async def test_calculate_race_synergies(seeded_session):
    """경주 전체 시너지 일괄 계산"""
    reports = await calculate_race_synergies(seeded_session, race_id=1)

    # race 1 has 3 entries
    assert len(reports) == 3
    # Each report should have jockey/trainer names
    names = {r.jockey_name for r in reports}
    assert "김동수" in names
    assert "박재현" in names


@pytest.mark.asyncio
async def test_calculate_synergy_no_data(db_session):
    """데이터 없는 기수/조교사"""
    report = await calculate_synergy(db_session, jockey_id=999, trainer_id=999)

    assert report.jockey_total_runs == 0
    assert report.best_record_rate == 0.0
    assert report.trainer_win_rate == 0.0
