from datetime import datetime, timezone

from app.db.database import SessionLocal
from app.models.test_run import TestRun, TestRunStatus
from app.workers.celery_app import celery_app


@celery_app.task(name="app.workers.tasks.execute_test_run")
def execute_test_run(test_run_id: int) -> dict[str, int | str]:
    """Persist a placeholder result until a real test runner is integrated."""
    db = SessionLocal()
    try:
        test_run = db.get(TestRun, test_run_id)
        if test_run is None:
            return {"test_run_id": test_run_id, "status": "not_found"}

        test_run.status = TestRunStatus.RUNNING
        test_run.started_at = datetime.now(timezone.utc)
        db.commit()

        test_run.status = TestRunStatus.PASSED
        test_run.result = {"message": "Test runner is not implemented yet"}
        test_run.finished_at = datetime.now(timezone.utc)
        test_run.duration_ms = int(
            (test_run.finished_at - test_run.started_at).total_seconds() * 1000
        )
        db.commit()

        return {"test_run_id": test_run_id, "status": test_run.status.value}
    except Exception:
        db.rollback()
        failed_test_run = db.get(TestRun, test_run_id)
        if failed_test_run is not None:
            failed_test_run.status = TestRunStatus.FAILED
            failed_test_run.result = {"message": "Worker execution failed"}
            failed_test_run.error_message = "Worker execution failed"
            failed_test_run.finished_at = datetime.now(timezone.utc)
            if failed_test_run.started_at is not None:
                failed_test_run.duration_ms = int(
                    (failed_test_run.finished_at - failed_test_run.started_at).total_seconds()
                    * 1000
                )
            db.commit()
        raise
    finally:
        db.close()
