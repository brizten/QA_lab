from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING, Any

from sqlalchemy import DateTime, Enum as SqlEnum, ForeignKey, JSON, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.test_case import TestCase
    from app.models.test_run_step import TestRunStep
    from app.models.user import User


class TestRunStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"


class TestRun(Base):
    __tablename__ = "test_runs"

    id: Mapped[int] = mapped_column(primary_key=True)
    test_case_id: Mapped[int] = mapped_column(
        ForeignKey("test_cases.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    initiated_by_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    status: Mapped[TestRunStatus] = mapped_column(
        SqlEnum(TestRunStatus, name="test_run_status"),
        default=TestRunStatus.PENDING,
        nullable=False,
        index=True,
    )
    parameters: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    result: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    celery_task_id: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    test_case: Mapped[TestCase] = relationship(back_populates="test_runs")
    initiated_by: Mapped[User] = relationship(back_populates="test_runs")
    steps: Mapped[list[TestRunStep]] = relationship(
        back_populates="test_run",
        cascade="all, delete-orphan",
        order_by="TestRunStep.step_order",
    )
