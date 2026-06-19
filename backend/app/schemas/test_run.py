from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from app.models.test_run import TestRunStatus


class TestRunCreate(BaseModel):
    test_case_id: int
    parameters: dict[str, Any] = Field(default_factory=dict)


class TestRunStepRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    step_order: int
    name: str
    status: TestRunStatus
    input_data: dict[str, Any] | None
    output_data: dict[str, Any] | None
    error_message: str | None
    created_at: datetime
    finished_at: datetime | None


class TestRunRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    test_case_id: int
    initiated_by_id: int
    status: TestRunStatus
    parameters: dict[str, Any]
    result: dict[str, Any] | None
    celery_task_id: str | None
    started_at: datetime | None
    finished_at: datetime | None
    created_at: datetime
    steps: list[TestRunStepRead] = Field(default_factory=list)
