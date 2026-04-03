from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, Integer, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class Prediction(Base):
    """예측 결과"""

    __tablename__ = "prediction"

    id: Mapped[int] = mapped_column(primary_key=True)
    race_id: Mapped[int] = mapped_column(ForeignKey("race.id"), index=True)
    entry_id: Mapped[int] = mapped_column(ForeignKey("race_entry.id"))

    total_score: Mapped[float] = mapped_column(Float)
    predicted_rank: Mapped[int] = mapped_column(Integer)
    confidence: Mapped[float | None] = mapped_column(Float)
    factors_json: Mapped[str | None] = mapped_column(Text)  # 요인 분해 JSON
    model_version: Mapped[str | None] = mapped_column(Text)

    actual_rank: Mapped[int | None] = mapped_column(Integer)  # 실제 결과 (사후 기록)
    is_override: Mapped[bool] = mapped_column(default=False)  # 수동 기수 변경 예측 여부

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
