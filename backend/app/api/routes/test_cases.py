from fastapi import APIRouter, HTTPException, status
from sqlalchemy import select

from app.api.deps import CurrentUser, DbSession
from app.models.module import Module
from app.models.test_case import TestCase
from app.schemas.test_case import TestCaseCreate, TestCaseRead


router = APIRouter(prefix="/test-cases", tags=["test-cases"])


@router.get("/", response_model=list[TestCaseRead])
def list_test_cases(db: DbSession, current_user: CurrentUser) -> list[TestCase]:
    return list(
        db.scalars(
            select(TestCase)
            .where(TestCase.owner_id == current_user.id)
            .order_by(TestCase.code)
        )
    )


@router.post("/", response_model=TestCaseRead, status_code=status.HTTP_201_CREATED)
def create_test_case(
    payload: TestCaseCreate, db: DbSession, current_user: CurrentUser
) -> TestCase:
    module = db.get(Module, payload.module_id)
    if module is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Module not found")

    test_case = TestCase(**payload.model_dump(), owner_id=current_user.id)
    db.add(test_case)
    db.commit()
    db.refresh(test_case)
    return test_case
