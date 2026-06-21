from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status

from app.api.deps import TEST_CASE_READ_ROLES, TEST_CASE_WRITE_ROLES, DbSession, require_roles
from app.models.module import Module
from app.models.test_case import TestCase
from app.models.user import User
from app.schemas.test_case import TestCaseCreate, TestCaseRead
from app.services.access_service import list_visible_test_cases


router = APIRouter(prefix="/test-cases", tags=["test-cases"])


@router.get("/", response_model=list[TestCaseRead])
def list_test_cases(
    db: DbSession,
    current_user: Annotated[User, Depends(require_roles(*TEST_CASE_READ_ROLES))],
) -> list[TestCase]:
    return list_visible_test_cases(db, current_user)


@router.post("/", response_model=TestCaseRead, status_code=status.HTTP_201_CREATED)
def create_test_case(
    payload: TestCaseCreate,
    db: DbSession,
    current_user: Annotated[User, Depends(require_roles(*TEST_CASE_WRITE_ROLES))],
) -> TestCase:
    module = db.get(Module, payload.module_id)
    if module is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Module not found")

    test_case = TestCase(**payload.model_dump(), owner_id=current_user.id)
    db.add(test_case)
    db.commit()
    db.refresh(test_case)
    return test_case
