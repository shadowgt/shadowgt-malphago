from datetime import date

from sqlalchemy import Date, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class Horse(Base):
    __tablename__ = "horse"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(50), index=True)
    origin: Mapped[str | None] = mapped_column(String(20))  # 산지
    gender: Mapped[str | None] = mapped_column(String(5))  # 거/암/수
    birth_date: Mapped[date | None] = mapped_column(Date)
    color: Mapped[str | None] = mapped_column(String(20))
    owner: Mapped[str | None] = mapped_column(String(50))
    note: Mapped[str | None] = mapped_column(Text)
