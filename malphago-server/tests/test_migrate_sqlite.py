"""마이그레이션 스크립트 파싱 함수 테스트"""

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from scripts.migrate_sqlite import (
    parse_race_date_round,
    parse_date,
    parse_int,
    parse_float,
    parse_corners,
    parse_prize,
    parse_distance,
)


class TestParseRaceDateRound:
    def test_normal(self):
        result = parse_race_date_round("2020-02-15 / 9R| 디케이마루|...")
        assert result is not None
        date_str, rnd, _ = result
        assert date_str == "2020-02-15"
        assert rnd == 9

    def test_double_space(self):
        result = parse_race_date_round("2020-02-22  / 1R|1|논스톱위닝|...")
        assert result is not None
        assert result[0] == "2020-02-22"
        assert result[1] == 1

    def test_slash_date(self):
        result = parse_race_date_round("2020/02/22 / 3R|stuff")
        assert result is not None
        assert result[0] == "2020-02-22"
        assert result[1] == 3

    def test_invalid(self):
        assert parse_race_date_round("garbage") is None
        assert parse_race_date_round("") is None


class TestParseDate:
    def test_dash(self):
        from datetime import date
        assert parse_date("2020-02-15") == date(2020, 2, 15)

    def test_slash(self):
        from datetime import date
        assert parse_date("2020/02/22") == date(2020, 2, 22)

    def test_invalid(self):
        assert parse_date("nope") is None


class TestParseCorners:
    def test_full_corners(self):
        # 서울 1400m: 7개 숫자, 마지막 4개가 코너
        c1, c2, c3, c4 = parse_corners("6-   -   - 6- 5- 4- 1")
        assert c1 == "6"
        assert c2 == "5"
        assert c3 == "4"
        assert c4 == "1"

    def test_short_corners(self):
        # 1000m: 숫자가 4개만
        c1, c2, c3, c4 = parse_corners("3- 4- 5- 3")
        assert c1 == "3"
        assert c4 == "3"

    def test_three_corners(self):
        c1, c2, c3, c4 = parse_corners("5- 4- 3")
        assert c1 is None
        assert c2 == "5"
        assert c3 == "4"
        assert c4 == "3"

    def test_empty(self):
        assert parse_corners(None) == (None, None, None, None)
        assert parse_corners("") == (None, None, None, None)


class TestParsePrize:
    def test_normal(self):
        assert parse_prize("13,750,000원") == 13750000

    def test_none(self):
        assert parse_prize(None) is None
        assert parse_prize("") is None


class TestParseDistance:
    def test_with_m(self):
        assert parse_distance("1000M") == 1000

    def test_plain(self):
        assert parse_distance("1400") == 1400

    def test_none(self):
        assert parse_distance(None) is None


class TestParseInt:
    def test_normal(self):
        assert parse_int("5") == 5
        assert parse_int(" 12 ") == 12

    def test_none(self):
        assert parse_int(None) is None
        assert parse_int("") is None


class TestParseFloat:
    def test_normal(self):
        assert parse_float("13.9") == 13.9

    def test_empty(self):
        assert parse_float("") is None
        assert parse_float("  ") is None
        assert parse_float(None) is None
