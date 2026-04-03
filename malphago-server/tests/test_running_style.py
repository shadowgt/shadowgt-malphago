"""각질 분류 서비스 테스트"""

import pytest
from app.services.running_style import (
    RunningStyle,
    classify_single_race,
    analyze_running_style,
    _parse_corner,
)
from app.models.race_timing import RaceTiming


class TestParseCorner:
    def test_normal(self):
        assert _parse_corner("3") == 3

    def test_padded(self):
        assert _parse_corner("02") == 2

    def test_none(self):
        assert _parse_corner(None) is None

    def test_empty(self):
        assert _parse_corner("") is None


class TestClassifySingleRace:
    def _make_timing(self, c1, c2, c3, c4, s1f=None, g1f=None):
        t = RaceTiming()
        t.corner_1 = str(c1) if c1 else None
        t.corner_2 = str(c2) if c2 else None
        t.corner_3 = str(c3) if c3 else None
        t.corner_4 = str(c4) if c4 else None
        t.s1f = s1f
        t.g1f = g1f
        return t

    def test_front_runner(self):
        """선두에서 달리면 도주"""
        timing = self._make_timing(1, 1, 1, 1)
        style = classify_single_race(timing, total_entries=8)
        assert style == RunningStyle.FRONT_RUNNER

    def test_stalker(self):
        """3위 그룹에서 달리며 후반 가속 → 선행"""
        timing = self._make_timing(3, 3, 2, 2, s1f=12.5, g1f=11.8)
        style = classify_single_race(timing, total_entries=8)
        assert style == RunningStyle.STALKER

    def test_closer(self):
        """후방에서 출발하여 전진 → 추입"""
        timing = self._make_timing(7, 6, 5, 3)
        style = classify_single_race(timing, total_entries=8)
        assert style == RunningStyle.CLOSER

    def test_mid_pack(self):
        """중간에서 전진 → 선입"""
        timing = self._make_timing(5, 5, 4, 3)
        style = classify_single_race(timing, total_entries=8)
        assert style == RunningStyle.MID_PACK

    def test_no_corner_data(self):
        timing = self._make_timing(None, None, None, None)
        style = classify_single_race(timing, total_entries=8)
        assert style == RunningStyle.UNKNOWN

    def test_insufficient_entries(self):
        timing = self._make_timing(1, 1, 1, 1)
        style = classify_single_race(timing, total_entries=1)
        assert style == RunningStyle.UNKNOWN


@pytest.mark.asyncio
async def test_analyze_running_style_no_data(db_session):
    """데이터 없는 말"""
    analysis = await analyze_running_style(db_session, horse_id=999)
    assert analysis.style == RunningStyle.UNKNOWN
    assert analysis.sample_count == 0


@pytest.mark.asyncio
async def test_analyze_running_style_with_timing(seeded_session):
    """타이밍 데이터가 있는 경우 분석"""
    from app.models.race_timing import RaceTiming as RT

    # 번개호(id=1)에 타이밍 데이터 추가
    t1 = RT(entry_id=1, corner_1="1", corner_2="1", corner_3="1", corner_4="1", s1f=12.0, g1f=12.5)
    t2 = RT(entry_id=4, corner_1="1", corner_2="2", corner_3="1", corner_4="1", s1f=12.1, g1f=12.3)
    seeded_session.add_all([t1, t2])
    await seeded_session.commit()

    analysis = await analyze_running_style(seeded_session, horse_id=1, recent_n=5)
    assert analysis.sample_count == 2
    assert analysis.style == RunningStyle.FRONT_RUNNER
    assert analysis.consistency > 0.5
    assert analysis.avg_corner_position > 0
