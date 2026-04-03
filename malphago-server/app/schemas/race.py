"""경주 관련 Pydantic 스키마"""

from datetime import date, datetime

from pydantic import BaseModel, ConfigDict


class TrackSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    code: str
    name: str
    name_en: str | None = None


class RaceSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    track_id: int
    race_date: date
    race_number: int
    race_name: str | None = None
    race_level: str | None = None
    distance: int | None = None
    surface: str | None = None
    weather: str | None = None
    moisture: str | None = None
    total_entries: int | None = None
    prize_1st: int | None = None
    prize_2nd: int | None = None
    prize_3rd: int | None = None
    race_time: str | None = None


class RaceEntrySchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    race_id: int
    horse_id: int
    jockey_id: int | None = None
    trainer_id: int | None = None
    horse_number: int | None = None
    ranking: int | None = None
    favor_ranking: int | None = None
    rating: int | None = None
    weight: str | None = None
    horse_weight: int | None = None
    horse_weight_change: int | None = None
    race_interval: int | None = None
    finish_margin: str | None = None
    odds_win: float | None = None
    odds_place: float | None = None
    equipment: str | None = None


class RaceEntryDetailSchema(RaceEntrySchema):
    """출주마 상세 (관계 포함)"""
    horse_name: str | None = None
    jockey_name: str | None = None
    trainer_name: str | None = None


class TimingSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    entry_id: int
    corner_1: str | None = None
    corner_2: str | None = None
    corner_3: str | None = None
    corner_4: str | None = None
    s1f: str | None = None
    g3f: str | None = None
    g1f: str | None = None
    final_time: str | None = None
