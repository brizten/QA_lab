from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status

from app.api.deps import REPORT_READ_ROLES, TEST_RUN_CREATE_ROLES, DbSession, require_roles
from app.models.test_run import TestRun
from app.models.user import User
from app.schemas.test_run import TestRunCreate, TestRunRead
from app.services.access_service import (
    TestCaseRunForbiddenError,
    TestRunAccessForbiddenError,
    get_visible_test_run,
    list_visible_test_runs,
)
from app.services.test_run_service import (
    TaskQueueError,
    TestCaseNotFoundError,
    create_test_run,
)


router = APIRouter(prefix="/test-runs", tags=["test-runs"])


@router.get("/", response_model=list[TestRunRead])
def list_test_runs(
    db: DbSession,
    current_user: Annotated[User, Depends(require_roles(*REPORT_READ_ROLES))],
) -> list[TestRun]:
    return list_visible_test_runs(db, current_user)


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


@router.post("/", response_model=TestRunRead, status_code=status.HTTP_201_CREATED)
def queue_test_run(
    payload: TestRunCreate,
    db: DbSession,
    current_user: Annotated[User, Depends(require_roles(*TEST_RUN_CREATE_ROLES))],
) -> TestRun:
    try:
        return create_test_run(db, payload, current_user)
    except TestCaseNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except TestCaseRunForbiddenError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
    except TaskQueueError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Test run was created but could not be queued",
        ) from exc
