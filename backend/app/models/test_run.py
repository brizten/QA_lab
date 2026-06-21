from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING, Any

from sqlalchemy import DateTime, Enum as SqlEnum, ForeignKey, JSON, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base_class import Base

if TYPE_CHECKING:
    from app.models.test_case import TestCase
    from app.models.test_run_step import TestRunStep
    from app.models.user import User


class TestRunStatus(str, Enum):
    QUEUED = "QUEUED"
    RUNNING = "RUNNING"
    PASSED = "PASSED"
    FAILED = "FAILED"
    BROKEN = "BROKEN"
    CANCELLED = "CANCELLED"
    TIMEOUT = "TIMEOUT"


class TestRun(Base):
    __tablename__ = "test_runs"

    id: Mapped[int] = mapped_column(primary_key=True)
    test_case_id: Mapped[int] = mapped_column(
        ForeignKey("test_cases.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    started_by_user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    environment: Mapped[str] = mapped_column(
        String(128), default="local", server_default="local", nullable=False
    )
    status: Mapped[TestRunStatus] = mapped_column(
        SqlEnum(TestRunStatus, name="test_run_status"),
        default=TestRunStatus.QUEUED,
        server_default=TestRunStatus.QUEUED.value,
        nullable=False,
        index=True,
    )
    parameters: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    result: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    error_message: Mapped[str | None] = mapped_column(String(2000), nullable=True)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    duration_ms: Mapped[int | None] = mapped_column(nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    test_case: Mapped[TestCase] = relationship(back_populates="test_runs")
    started_by_user: Mapped[User] = relationship(back_populates="started_test_runs")
    steps: Mapped[list[TestRunStep]] = relationship(
        back_populates="test_run",
        cascade="all, delete-orphan",
    )
