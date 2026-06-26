from datetime import datetime, timezone
from typing import Any

from app.db.database import SessionLocal
from app.models.test_run import TestRun, TestRunStatus
from app.runner.context import TestContext
from app.runner.registry import get_test_by_code
from app.workers.celery_app import celery_app


@celery_app.task(name="app.workers.tasks.run_test_case")
def run_test_case(test_run_id: int) -> dict[str, int | str]:
    """Run a registered test case class and persist the report details."""
    db = SessionLocal()
    try:
        test_run = db.get(TestRun, test_run_id)
        if test_run is None:
            return {"test_run_id": test_run_id, "status": "not_found"}

        _mark_run_started(db, test_run)

        test_case_code = test_run.test_case.code
        test = get_test_by_code(test_case_code)
        if test is None:
            error_message = f"Runner test class is not registered for code: {test_case_code}"
            _mark_run_finished(
                db=db,
                test_run=test_run,
                status=TestRunStatus.BROKEN,
                result={
                    "message": "Runner test class not found",
                    "test_case_code": test_case_code,
                },
                error_message=error_message,
            )
            return {"test_run_id": test_run_id, "status": test_run.status.value}

        context = TestContext(
            test_run_id=test_run.id,
            params=test_run.parameters,
            environment=test_run.environment,
            db=db,
        )
        result = test.run(context)
        _mark_run_finished(
            db=db,
            test_run=test_run,
            status=TestRunStatus.PASSED,
            result=result or {"message": "Test completed successfully"},
        )
        return {"test_run_id": test_run_id, "status": test_run.status.value}
    except AssertionError as exc:
        db.rollback()
        failed_test_run = db.get(TestRun, test_run_id)
        if failed_test_run is not None:
            error_message = str(exc) or "Test assertion failed"
            _mark_run_finished(
                db=db,
                test_run=failed_test_run,
                status=TestRunStatus.FAILED,
                result={"message": "Test failed", "error": error_message},
                error_message=error_message,
            )
            return {"test_run_id": test_run_id, "status": failed_test_run.status.value}
        return {"test_run_id": test_run_id, "status": "not_found"}
    except Exception as exc:
        db.rollback()
        broken_test_run = db.get(TestRun, test_run_id)
        if broken_test_run is not None:
            error_message = str(exc) or "Unexpected test runner error"
            _mark_run_finished(
                db=db,
                test_run=broken_test_run,
                status=TestRunStatus.BROKEN,
                result={"message": "Test execution broken", "error": error_message},
                error_message=error_message,
            )
            return {"test_run_id": test_run_id, "status": broken_test_run.status.value}
        return {"test_run_id": test_run_id, "status": "not_found"}
    finally:
        db.close()


def _mark_run_started(db, test_run: TestRun) -> None:
    test_run.status = TestRunStatus.RUNNING
    test_run.started_at = datetime.now(timezone.utc)
    test_run.finished_at = None
    test_run.duration_ms = None
    test_run.result = None
    test_run.error_message = None
    db.commit()


def _mark_run_finished(
    db,
    test_run: TestRun,
    status: TestRunStatus,
    result: dict[str, Any] | None = None,
    error_message: str | None = None,
) -> None:
    if test_run.started_at is None:
        test_run.started_at = datetime.now(timezone.utc)

    test_run.status = status
    test_run.result = result
    test_run.error_message = error_message
    test_run.finished_at = datetime.now(timezone.utc)
    test_run.duration_ms = _duration_ms(test_run.started_at, test_run.finished_at)
    db.commit()


def _duration_ms(started_at: datetime, finished_at: datetime) -> int:
    if started_at.tzinfo is None:
        started_at = started_at.replace(tzinfo=timezone.utc)
    if finished_at.tzinfo is None:
        finished_at = finished_at.replace(tzinfo=timezone.utc)
    return int((finished_at - started_at).total_seconds() * 1000)
