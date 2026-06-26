from datetime import datetime, timezone

from app.db.database import SessionLocal
from app.models.test_run import TestRun, TestRunStatus
from app.models.test_run_step import TestRunStep, TestRunStepStatus
from app.workers.celery_app import celery_app


@celery_app.task(name="app.workers.tasks.run_test_case")
def run_test_case(test_run_id: int) -> dict[str, int | str]:
    """Run a mock test case execution and persist the report details."""
    db = SessionLocal()
    try:
        test_run = db.get(TestRun, test_run_id)
        if test_run is None:
            return {"test_run_id": test_run_id, "status": "not_found"}

        _mark_run_started(db, test_run)

        _create_completed_step(
            db=db,
            test_run_id=test_run.id,
            name="Validate input parameters",
            status=TestRunStepStatus.PASSED,
            request_json=test_run.parameters,
            response_json={"message": "Input parameters accepted"},
        )

        if test_run.parameters.get("force_fail") is True:
            _create_completed_step(
                db=db,
                test_run_id=test_run.id,
                name="Execute mock test logic",
                status=TestRunStepStatus.FAILED,
                error_message="Forced failure for testing",
            )
            _mark_run_finished(
                db=db,
                test_run=test_run,
                status=TestRunStatus.FAILED,
                error_message="Forced failure for testing",
            )
            return {"test_run_id": test_run_id, "status": test_run.status.value}

        _create_completed_step(
            db=db,
            test_run_id=test_run.id,
            name="Execute mock test logic",
            status=TestRunStepStatus.PASSED,
            response_json={"message": "Mock logic executed"},
        )
        _create_completed_step(
            db=db,
            test_run_id=test_run.id,
            name="Save mock result",
            status=TestRunStepStatus.PASSED,
            response_json={"message": "Mock result saved"},
        )
        _mark_run_finished(
            db=db,
            test_run=test_run,
            status=TestRunStatus.PASSED,
            result={"message": "Mock test completed successfully"},
        )

        return {"test_run_id": test_run_id, "status": test_run.status.value}
    except Exception as exc:
        db.rollback()
        broken_test_run = db.get(TestRun, test_run_id)
        if broken_test_run is not None:
            _mark_run_finished(
                db=db,
                test_run=broken_test_run,
                status=TestRunStatus.BROKEN,
                error_message=str(exc) or "Unexpected worker error",
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
    result: dict[str, str] | None = None,
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


def _create_completed_step(
    db,
    test_run_id: int,
    name: str,
    status: TestRunStepStatus,
    request_json: dict | None = None,
    response_json: dict | None = None,
    error_message: str | None = None,
) -> None:
    started_at = datetime.now(timezone.utc)
    finished_at = datetime.now(timezone.utc)
    step = TestRunStep(
        test_run_id=test_run_id,
        name=name,
        status=status,
        started_at=started_at,
        finished_at=finished_at,
        duration_ms=_duration_ms(started_at, finished_at),
        error_message=error_message,
        request_json=request_json,
        response_json=response_json,
    )
    db.add(step)
    db.commit()


def _duration_ms(started_at: datetime, finished_at: datetime) -> int:
    if started_at.tzinfo is None:
        started_at = started_at.replace(tzinfo=timezone.utc)
    if finished_at.tzinfo is None:
        finished_at = finished_at.replace(tzinfo=timezone.utc)
    return int((finished_at - started_at).total_seconds() * 1000)
