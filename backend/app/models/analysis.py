from typing import Any, Dict, Optional
from sqlalchemy import JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column
from app.models.base import Base, TimestampMixin, UUIDMixin


class AnalysisRun(Base, UUIDMixin, TimestampMixin):
    """Represents a multi-agent stock analysis execution run."""

    __tablename__ = "analysis_runs"

    ticker: Mapped[str] = mapped_column(String(16), index=True, nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="pending", index=True, nullable=False)
    parameters: Mapped[Dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    result_summary: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    def __repr__(self) -> str:
        return f"<AnalysisRun(id={self.id}, ticker='{self.ticker}', status='{self.status}')>"
