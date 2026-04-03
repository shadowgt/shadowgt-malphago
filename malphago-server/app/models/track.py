from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class Track(Base):
    __tablename__ = "track"

    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String(1), unique=True)  # S=서울, B=부산, J=제주
    name: Mapped[str] = mapped_column(String(10))
    name_en: Mapped[str] = mapped_column(String(20))
