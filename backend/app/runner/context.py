from __future__ import annotations

from datetime import datetime, timezone
from types import TracebackType
from typing import Any

from sqlalchemy.orm import Session

from app.models.test_run_step import TestRunStep, TestRunStepStatus


_UNSET = object()


class TestContext:
    def __init__(
        self,
        test_run_id: int,
        params: dict[str, Any],
        environment: str,
        db: Session,
    ) -> None:
        self.test_run_id = test_run_id
        self.params = params
        self.environment = environment
        self.db = db

    def step(
        self,
        name: str,
        request_json: dict[str, Any] | None = None,
    ) -> TestStep:
        return TestStep(context=self, name=name, request_json=request_json)


class TestStep:
    def __init__(
        self,
        context: TestContext,
        name: str,
        request_json: dict[str, Any] | None = None,
    ) -> None:
        self.context = context
        self.name = name
        self.request_json = request_json
        self.step: TestRunStep | None = None

    def __enter__(self) -> TestStep:
        started_at = datetime.now(timezone.utc)
        self.step = TestRunStep(
            test_run_id=self.context.test_run_id,
            name=self.name,
            status=TestRunStepStatus.RUNNING,
            started_at=started_at,
            request_json=self.request_json,
        )
        self.context.db.add(self.step)
        self.context.db.commit()
        self.context.db.refresh(self.step)
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        traceback: TracebackType | None,
    ) -> bool:
        if exc_type is None:
            if self.step is not None and self.step.status == TestRunStepStatus.RUNNING:
                self.set_status(TestRunStepStatus.PASSED)
            return False

        status = (
            TestRunStepStatus.FAILED
            if issubclass(exc_type, AssertionError)
            else TestRunStepStatus.BROKEN
        )
        self.set_status(status, error_message=str(exc) or exc_type.__name__)
        return False

    def set_status(
        self,
        status: TestRunStepStatus,
        error_message: str | None = None,
        request_json: dict[str, Any] | None | object = _UNSET,
        response_json: dict[str, Any] | None | object = _UNSET,
    ) -> None:
        if self.step is None:
            raise RuntimeError("Step has not been started")

        self.step.status = status
        if error_message is not None:
            self.step.error_message = error_message
        if request_json is not _UNSET:
            self.step.request_json = request_json
        if response_json is not _UNSET:
            self.step.response_json = response_json

        if status != TestRunStepStatus.RUNNING:
            finished_at = datetime.now(timezone.utc)
            self.step.finished_at = finished_at
            started_at = self.step.started_at or finished_at
            self.step.duration_ms = _duration_ms(started_at, finished_at)

        self.context.db.commit()

    def save_request_json(self, request_json: dict[str, Any] | None) -> None:
        self.set_status(TestRunStepStatus.RUNNING, request_json=request_json)

    def save_response_json(self, response_json: dict[str, Any] | None) -> None:
        self.set_status(TestRunStepStatus.RUNNING, response_json=response_json)

    def pass_step(self, response_json: dict[str, Any] | None = None) -> None:
        self.set_status(TestRunStepStatus.PASSED, response_json=response_json)

    def fail_step(self, error_message: str) -> None:
        self.set_status(TestRunStepStatus.FAILED, error_message=error_message)

    def break_step(self, error_message: str) -> None:
        self.set_status(TestRunStepStatus.BROKEN, error_message=error_message)

    def skip_step(self, error_message: str | None = None) -> None:
        self.set_status(TestRunStepStatus.SKIPPED, error_message=error_message)


def _duration_ms(started_at: datetime, finished_at: datetime) -> int:
    if started_at.tzinfo is None:
        started_at = started_at.replace(tzinfo=timezone.utc)
    if finished_at.tzinfo is None:
        finished_at = finished_at.replace(tzinfo=timezone.utc)
    return int((finished_at - started_at).total_seconds() * 1000)
