"""
Ingestion tracking and data health log model.
"""

from datetime import datetime

from sqlalchemy import DateTime, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from backend.app.db.base import Base


class IngestionLog(Base):
    __tablename__ = "ingestion_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    source: Mapped[str] = mapped_column(String(50), default="data.gov.in", nullable=False)
    fetch_timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        index=True,
    )
    records_fetched: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    records_upserted: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    records_failed: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # Status: 'success', 'failure', 'stale_warning'
    status: Mapped[str] = mapped_column(String(30), default="success", nullable=False)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
