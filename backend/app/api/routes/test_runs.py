from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status

from app.api.deps import REPORT_READ_ROLES, TEST_RUN_CREATE_ROLES, DbSession, require_roles
from app.models.test_run import TestRun
from app.models.user import User
from app.schemas.test_run import TestRunCreate, TestRunQueuedRead, TestRunRead, TestRunReportRead
from app.services.access_service import (
    TestCaseRunForbiddenError,
    TestRunAccessForbiddenError,
    get_visible_test_run,
    list_visible_test_runs,
)
from app.services.test_run_service import (
    TestCaseNotFoundError,
    TestRunParametersValidationError,
    create_test_run,
)
from app.workers.tasks import run_test_case


router = APIRouter(prefix="/test-runs", tags=["test-runs"])


@router.get("", response_model=list[TestRunRead])
def list_test_runs(
    db: DbSession,
    current_user: Annotated[User, Depends(require_roles(*REPORT_READ_ROLES))],
) -> list[TestRun]:
    return list_visible_test_runs(db, current_user)


@router.get("/{test_run_id}/report", response_model=TestRunReportRead)
def get_test_run_report(
    test_run_id: int,
    db: DbSession,
    current_user: Annotated[User, Depends(require_roles(*REPORT_READ_ROLES))],
) -> TestRunReportRead:
    try:
        test_run = get_visible_test_run(db, test_run_id, current_user)
    except TestRunAccessForbiddenError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
    if test_run is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Test run not found")
    return TestRunReportRead(
        test_run=test_run,
        test_case=test_run.test_case,
        module=test_run.test_case.module,
        steps=test_run.steps,
        result=test_run.result,
        error_message=test_run.error_message,
    )


@router.get("/{test_run_id}", response_model=TestRunRead)
def get_test_run(
    test_run_id: int,
    db: DbSession,
    current_user: Annotated[User, Depends(require_roles(*REPORT_READ_ROLES))],
) -> TestRun:
    try:
        test_run = get_visible_test_run(db, test_run_id, current_user)
    except TestRunAccessForbiddenError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
    if test_run is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Test run not found")
    return test_run


@router.post("", response_model=TestRunQueuedRead, status_code=status.HTTP_201_CREATED)
def queue_test_run(
    payload: TestRunCreate,
    db: DbSession,
    current_user: Annotated[User, Depends(require_roles(*TEST_RUN_CREATE_ROLES))],
) -> TestRunQueuedRead:
    try:
        test_run = create_test_run(db, payload, current_user)
    except TestCaseNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except TestCaseRunForbiddenError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
    except TestRunParametersValidationError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail={"message": str(exc), "errors": exc.errors},
        ) from exc
    run_test_case.delay(test_run.id)
    return TestRunQueuedRead(run_id=test_run.id, status=test_run.status)
