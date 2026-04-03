from datetime import date

from sqlalchemy import Date, ForeignKey, Integer, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class Race(Base):
    __tablename__ = "race"

    id: Mapped[int] = mapped_column(primary_key=True)
    track_id: Mapped[int] = mapped_column(ForeignKey("track.id"), index=True)
    race_date: Mapped[date] = mapped_column(Date, index=True)
    race_number: Mapped[int] = mapped_column(Integer)  # 회차 (1R, 2R...)
    race_name: Mapped[str | None] = mapped_column(String(100))
    race_level: Mapped[str | None] = mapped_column(String(20))  # 등급 (1, 2, 3...)
    distance: Mapped[int | None] = mapped_column(Integer)  # 거리 (m)
    surface: Mapped[str | None] = mapped_column(String(10))  # 주로 (잔디/모래)
    weather: Mapped[str | None] = mapped_column(String(10))  # 날씨
    moisture: Mapped[str | None] = mapped_column(String(10))  # 함수율
    total_entries: Mapped[int | None] = mapped_column(Integer)  # 출주두수
    prize_1st: Mapped[int | None] = mapped_column(Integer)
    prize_2nd: Mapped[int | None] = mapped_column(Integer)
    prize_3rd: Mapped[int | None] = mapped_column(Integer)
    prize_4th: Mapped[int | None] = mapped_column(Integer)
    prize_5th: Mapped[int | None] = mapped_column(Integer)
    race_time: Mapped[str | None] = mapped_column(String(10))  # 경주기록

    track = relationship("Track")
    entries = relationship("RaceEntry", back_populates="race")

    __table_args__ = (
        # 경마장 + 날짜 + 회차 = 유니크
        {"comment": "Unique: (track_id, race_date, race_number)"},
    )
