from sqlalchemy import Boolean, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class Jockey(Base):
    __tablename__ = "jockey"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(30), index=True)
    is_apprentice: Mapped[bool] = mapped_column(Boolean, default=False)  # 수습기수 여부
