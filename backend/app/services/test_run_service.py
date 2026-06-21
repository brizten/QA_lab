from sqlalchemy.orm import Session

from app.models.test_case import TestCase
from app.models.test_run import TestRun, TestRunStatus
from app.models.user import User
from app.schemas.test_run import TestRunCreate
from app.services.access_service import ensure_test_case_can_be_run
from app.workers.tasks import execute_test_run


class TestCaseNotFoundError(Exception):
    pass


class TaskQueueError(Exception):
    pass


def create_test_run(db: Session, payload: TestRunCreate, started_by_user: User) -> TestRun:
    test_case = db.get(TestCase, payload.test_case_id)
    if test_case is None:
        raise TestCaseNotFoundError("Test case not found")
    ensure_test_case_can_be_run(test_case, started_by_user)

    test_run = TestRun(
        test_case_id=payload.test_case_id,
        started_by_user_id=started_by_user.id,
        environment=payload.environment,
        parameters=payload.parameters,
        status=TestRunStatus.QUEUED,
    )
    db.add(test_run)
    db.commit()
    db.refresh(test_run)

    try:
        task = execute_test_run.delay(test_run.id)
    except Exception as exc:
        test_run.status = TestRunStatus.FAILED
        test_run.result = {"message": "The task could not be queued"}
        db.commit()
        db.refresh(test_run)
        raise TaskQueueError() from exc

    return test_run
