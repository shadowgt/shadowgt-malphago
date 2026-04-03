from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class EntryChangeLog(Base):
    """기수/말 변경 이력"""

    __tablename__ = "entry_change_log"

    id: Mapped[int] = mapped_column(primary_key=True)
    race_id: Mapped[int] = mapped_column(ForeignKey("race.id"), index=True)
    entry_id: Mapped[int | None] = mapped_column(ForeignKey("race_entry.id"))

    change_type: Mapped[str] = mapped_column(String(20))  # jockey_change, horse_scratch, weight_change
    field_name: Mapped[str] = mapped_column(String(30))  # 변경된 필드명
    old_value: Mapped[str | None] = mapped_column(Text)
    new_value: Mapped[str | None] = mapped_column(Text)
    source: Mapped[str] = mapped_column(String(10), default="auto")  # auto / manual
    detected_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
