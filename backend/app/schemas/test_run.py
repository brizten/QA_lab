from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from app.models.test_run import TestRunStatus
from app.models.test_run_step import TestRunStepStatus


class TestRunCreate(BaseModel):
    test_case_code: str = Field(min_length=1, max_length=100)
    environment: str = Field(default="local", min_length=1, max_length=128)
    parameters: dict[str, Any] = Field(default_factory=dict)


class TestRunQueuedRead(BaseModel):
    run_id: int
    status: TestRunStatus


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


class TestRunReportRunRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    status: TestRunStatus
    environment: str
    parameters: dict[str, Any]
    result: dict[str, Any] | None
    error_message: str | None
    started_at: datetime | None
    finished_at: datetime | None
    duration_ms: int | None


class TestRunReportTestCaseRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    code: str
    name: str
    tags: list[str]


class TestRunReportModuleRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    code: str
    name: str


class TestRunReportStartedByRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    email: str
    full_name: str | None


class TestRunReportStepRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    status: TestRunStepStatus
    duration_ms: int | None
    error_message: str | None
    request_json: dict[str, Any] | None
    response_json: dict[str, Any] | None


class TestRunReportRead(BaseModel):
    run: TestRunReportRunRead
    test_case: TestRunReportTestCaseRead
    module: TestRunReportModuleRead
    started_by: TestRunReportStartedByRead
    steps: list[TestRunReportStepRead]
