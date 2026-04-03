"""통계 관련 Pydantic 스키마"""

from pydantic import BaseModel


class RecentRaceSchema(BaseModel):
    race_date: str | None = None
    race_number: int | None = None
    distance: int | None = None
    ranking: int | None = None
    horse_weight: int | None = None
    odds_win: float | None = None


class DistanceBreakdownSchema(BaseModel):
    distance: str
    runs: int
    wins: int
    top3: int
    win_rate: float


class HorseStatsSchema(BaseModel):
    horse_id: int
    name: str | None = None
    origin: str | None = None
    gender: str | None = None
    total_record: str = "0-0-0-0"
    win_rate: float = 0.0
    top3_rate: float = 0.0
    distance_breakdown: list[DistanceBreakdownSchema] = []
    recent_races: list[RecentRaceSchema] = []


class TrackBreakdownSchema(BaseModel):
    track: str
    runs: int
    wins: int
    win_rate: float


class JockeyStatsSchema(BaseModel):
    jockey_id: int
    name: str | None = None
    total_record: str = "0-0-0-0"
    win_rate: float = 0.0
    top3_rate: float = 0.0
    recent_30_form: float = 0.0
    distance_breakdown: list[DistanceBreakdownSchema] = []
    track_breakdown: list[TrackBreakdownSchema] = []


class EntryChangeSchema(BaseModel):
    id: int
    race_id: int
    entry_id: int | None = None
    change_type: str
    field_name: str | None = None
    old_value: str | None = None
    new_value: str | None = None
    detected_at: str | None = None


class SyncDeltaSchema(BaseModel):
    races: list[dict] = []
    change_logs: list[EntryChangeSchema] = []
