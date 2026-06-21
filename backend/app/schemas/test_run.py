from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from app.models.test_run import TestRunStatus
from app.models.test_run_step import TestRunStepStatus


class TestRunCreate(BaseModel):
    test_case_id: int
    environment: str = Field(default="local", min_length=1, max_length=128)
    parameters: dict[str, Any] = Field(default_factory=dict)


class TestRunStepRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    status: TestRunStepStatus
    started_at: datetime | None
    finished_at: datetime | None
    duration_ms: int | None
    error_message: str | None
    request_json: dict[str, Any] | None
    response_json: dict[str, Any] | None
    created_at: datetime
    updated_at: datetime


class TestRunRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    test_case_id: int
    started_by_user_id: int
    environment: str
    status: TestRunStatus
    parameters: dict[str, Any]
    result: dict[str, Any] | None
    error_message: str | None
    started_at: datetime | None
    finished_at: datetime | None
    duration_ms: int | None
    created_at: datetime
    updated_at: datetime
    steps: list[TestRunStepRead] = Field(default_factory=list)
