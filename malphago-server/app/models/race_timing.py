from sqlalchemy import ForeignKey, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class RaceTiming(Base):
    """구간 기록 - 서울(코너순위) / 부산(구간별 기록) 통합"""

    __tablename__ = "race_timing"

    id: Mapped[int] = mapped_column(primary_key=True)
    entry_id: Mapped[int] = mapped_column(ForeignKey("race_entry.id"), unique=True)

    # 서울 - 코너 통과순위
    corner_1: Mapped[str | None] = mapped_column(String(5))
    corner_2: Mapped[str | None] = mapped_column(String(5))
    corner_3: Mapped[str | None] = mapped_column(String(5))
    corner_4: Mapped[str | None] = mapped_column(String(5))

    # 공통 기록
    s1f: Mapped[float | None] = mapped_column(Numeric(5, 2))  # S1F (초반 1F)
    g3f: Mapped[float | None] = mapped_column(Numeric(5, 2))  # G3F (끝 3F)
    g1f: Mapped[float | None] = mapped_column(Numeric(5, 2))  # G1F (끝 1F)
    record_full: Mapped[str | None] = mapped_column(String(20))  # 전체 기록

    # 부산 - 구간별 기록
    split_10_8f: Mapped[float | None] = mapped_column(Numeric(5, 2))  # 10~8F
    split_8_6f: Mapped[float | None] = mapped_column(Numeric(5, 2))  # 8~6F
    split_6_4f: Mapped[float | None] = mapped_column(Numeric(5, 2))  # 6~4F
    split_4_2f: Mapped[float | None] = mapped_column(Numeric(5, 2))  # 4~2F
    split_2f_g: Mapped[float | None] = mapped_column(Numeric(5, 2))  # 2F~G
    split_3f_g: Mapped[float | None] = mapped_column(Numeric(5, 2))  # 3F~G
    split_1f_g: Mapped[float | None] = mapped_column(Numeric(5, 2))  # 1F~G
    final_time: Mapped[str | None] = mapped_column(String(10))  # 최종 기록

    entry = relationship("RaceEntry", back_populates="timing")
