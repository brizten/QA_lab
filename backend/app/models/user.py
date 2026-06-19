from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, DateTime, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.module import Module
    from app.models.test_case import TestCase
    from app.models.test_run import TestRun


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(320), unique=True, index=True)
    hashed_password: Mapped[str] = mapped_column(String(255))
    full_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    modules: Mapped[list[Module]] = relationship(
        back_populates="owner", cascade="all, delete-orphan"
    )
    test_cases: Mapped[list[TestCase]] = relationship(back_populates="created_by")
    test_runs: Mapped[list[TestRun]] = relationship(back_populates="initiated_by")
