from sqlalchemy import ForeignKey, Integer, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class RaceEntry(Base):
    """출주 기록 - 각 경주의 출전마 정보"""

    __tablename__ = "race_entry"

    id: Mapped[int] = mapped_column(primary_key=True)
    race_id: Mapped[int] = mapped_column(ForeignKey("race.id"), index=True)
    horse_id: Mapped[int] = mapped_column(ForeignKey("horse.id"), index=True)
    jockey_id: Mapped[int | None] = mapped_column(ForeignKey("jockey.id"), index=True)
    trainer_id: Mapped[int | None] = mapped_column(ForeignKey("trainer.id"))

    horse_number: Mapped[int | None] = mapped_column(Integer)  # 마번
    ranking: Mapped[int | None] = mapped_column(Integer)  # 순위 (결과)
    favor_ranking: Mapped[int | None] = mapped_column(Integer)  # 인기순위
    rating: Mapped[int | None] = mapped_column(Integer)  # 레이팅
    weight: Mapped[str | None] = mapped_column(String(10))  # 부담중량
    horse_weight: Mapped[int | None] = mapped_column(Integer)  # 마체중
    horse_weight_change: Mapped[int | None] = mapped_column(Integer)  # 마체중 증감
    race_interval: Mapped[int | None] = mapped_column(Integer)  # 출전간격 (일)
    finish_margin: Mapped[str | None] = mapped_column(String(20))  # 도착차
    odds_win: Mapped[float | None] = mapped_column(Numeric(8, 1))  # 단승배당
    odds_place: Mapped[float | None] = mapped_column(Numeric(8, 1))  # 연승배당
    equipment: Mapped[str | None] = mapped_column(String(50))  # 장구현황

    race = relationship("Race", back_populates="entries")
    horse = relationship("Horse")
    jockey = relationship("Jockey")
    trainer = relationship("Trainer")
    timing = relationship("RaceTiming", back_populates="entry", uselist=False)
