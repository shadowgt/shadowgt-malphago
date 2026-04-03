"""예측/시너지 관련 Pydantic 스키마"""

from pydantic import BaseModel, ConfigDict


class PredictionSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    entry_id: int
    total_score: float
    predicted_rank: int
    confidence: float | None = None
    factors: str | None = None  # JSON string
    model_version: str | None = None
    actual_rank: int | None = None


class PredictionRunResponse(BaseModel):
    race_id: int
    predictions: list[dict]


class SynergySchema(BaseModel):
    jockey_name: str = ""
    trainer_name: str = ""
    horse_name: str = ""
    best_record_rate: float = 0.0
    best_record_trainer_rate: float = 0.0
    high_dividend_record_rate: float = 0.0
    high_dividend_record_trainer_rate: float = 0.0
    horse_jockey_synergy_rate: float = 0.0
    horse_jockey_total_runs: int = 0
    trainer_win_rate: float = 0.0
    jockey_total_runs: int = 0


class SynergyBriefSchema(BaseModel):
    jockey_name: str = ""
    trainer_name: str = ""
    horse_name: str = ""
    best_record_rate: float = 0.0
    best_record_trainer_rate: float = 0.0
    high_dividend_record_rate: float = 0.0
    high_dividend_record_trainer_rate: float = 0.0
    horse_jockey_synergy_rate: float = 0.0
    horse_jockey_total_runs: int = 0
