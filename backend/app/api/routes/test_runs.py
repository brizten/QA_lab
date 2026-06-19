from fastapi import APIRouter, HTTPException, status
from sqlalchemy import select

from app.api.deps import CurrentUser, DbSession
from app.models.test_run import TestRun
from app.schemas.test_run import TestRunCreate, TestRunRead
from app.services.test_run_service import (
    TaskQueueError,
    TestCaseNotFoundError,
    create_test_run,
)


router = APIRouter(prefix="/test-runs", tags=["test-runs"])


@router.get("/", response_model=list[TestRunRead])
def list_test_runs(db: DbSession, current_user: CurrentUser) -> list[TestRun]:
    return list(
        db.scalars(
            select(TestRun)
            .where(TestRun.initiated_by_id == current_user.id)
            .order_by(TestRun.created_at.desc())
        )
    )


@router.get("/{test_run_id}", response_model=TestRunRead)
def get_test_run(test_run_id: int, db: DbSession, current_user: CurrentUser) -> TestRun:
    test_run = db.get(TestRun, test_run_id)
    if test_run is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Test run not found")
    if test_run.initiated_by_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Test run access denied")
    return test_run


@router.post("/", response_model=TestRunRead, status_code=status.HTTP_201_CREATED)
def queue_test_run(
    payload: TestRunCreate, db: DbSession, current_user: CurrentUser
) -> TestRun:
    try:
        return create_test_run(db, payload, current_user.id)
    except TestCaseNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except TaskQueueError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Test run was created but could not be queued",
        ) from exc
