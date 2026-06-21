from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.api.deps import TEST_CASE_READ_ROLES, TEST_CASE_WRITE_ROLES, DbSession, require_roles
from app.models.test_case import TestCase
from app.models.user import User
from app.schemas.test_case import TestCaseCreate, TestCaseRead, TestCaseUpdate
from app.services.test_case_service import (
    TestCaseCodeAlreadyExistsError,
    TestCaseInUseError,
    TestCaseModuleNotFoundError,
    TestCaseOwnerNotFoundError,
    create_test_case as create_test_case_record,
    delete_test_case as delete_test_case_record,
    get_test_case,
    list_test_cases as list_test_case_records,
    update_test_case as update_test_case_record,
)


router = APIRouter(prefix="/test-cases", tags=["test-cases"])


@router.get("", response_model=list[TestCaseRead])
def list_test_cases(
    db: DbSession,
    _current_user: Annotated[User, Depends(require_roles(*TEST_CASE_READ_ROLES))],
    module_id: int | None = Query(default=None, gt=0),
    tag: str | None = Query(default=None, min_length=1),
    is_active: bool | None = Query(default=None),
) -> list[TestCase]:
    return list_test_case_records(db, module_id=module_id, tag=tag, is_active=is_active)


@router.post("", response_model=TestCaseRead, status_code=status.HTTP_201_CREATED)
def create_test_case(
    payload: TestCaseCreate,
    db: DbSession,
    current_user: Annotated[User, Depends(require_roles(*TEST_CASE_WRITE_ROLES))],
) -> TestCase:
    try:
        return create_test_case_record(db, payload, current_user.id)
    except TestCaseModuleNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except TestCaseOwnerNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except TestCaseCodeAlreadyExistsError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.get("/{test_case_id}", response_model=TestCaseRead)
def read_test_case(
    test_case_id: int,
    db: DbSession,
    _current_user: Annotated[User, Depends(require_roles(*TEST_CASE_READ_ROLES))],
) -> TestCase:
    return _get_test_case_or_404(db, test_case_id)


@router.put("/{test_case_id}", response_model=TestCaseRead)
def update_test_case(
    test_case_id: int,
    payload: TestCaseUpdate,
    db: DbSession,
    _current_user: Annotated[User, Depends(require_roles(*TEST_CASE_WRITE_ROLES))],
) -> TestCase:
    test_case = _get_test_case_or_404(db, test_case_id)
    try:
        return update_test_case_record(db, test_case, payload)
    except TestCaseModuleNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except TestCaseOwnerNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except TestCaseCodeAlreadyExistsError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.delete("/{test_case_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_test_case(
    test_case_id: int,
    db: DbSession,
    _current_user: Annotated[User, Depends(require_roles(*TEST_CASE_WRITE_ROLES))],
) -> None:
    test_case = _get_test_case_or_404(db, test_case_id)
    try:
        delete_test_case_record(db, test_case)
    except TestCaseInUseError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


def _get_test_case_or_404(db: DbSession, test_case_id: int) -> TestCase:
    test_case = get_test_case(db, test_case_id)
    if test_case is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Test case not found")
    return test_case
