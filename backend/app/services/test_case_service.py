from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.module import Module
from app.models.test_case import TestCase
from app.models.test_run import TestRun
from app.models.user import User
from app.schemas.test_case import TestCaseCreate, TestCaseUpdate


class TestCaseCodeAlreadyExistsError(Exception):
    pass


class TestCaseModuleNotFoundError(Exception):
    pass


class TestCaseOwnerNotFoundError(Exception):
    pass


class TestCaseInUseError(Exception):
    pass


def list_test_cases(
    db: Session,
    module_id: int | None = None,
    tag: str | None = None,
    is_active: bool | None = None,
) -> list[TestCase]:
    statement = select(TestCase).order_by(TestCase.code)
    if module_id is not None:
        statement = statement.where(TestCase.module_id == module_id)
    if is_active is not None:
        statement = statement.where(TestCase.is_active == is_active)

    test_cases = list(db.scalars(statement))
    if tag is not None:
        test_cases = [test_case for test_case in test_cases if tag in test_case.tags]
    return test_cases


def get_test_case(db: Session, test_case_id: int) -> TestCase | None:
    return db.get(TestCase, test_case_id)


def create_test_case(
    db: Session,
    payload: TestCaseCreate,
    default_owner_id: int,
) -> TestCase:
    _ensure_module_exists(db, payload.module_id)
    owner_id = payload.owner_id or default_owner_id
    _ensure_owner_exists(db, owner_id)
    _ensure_code_is_available(db, payload.code)

    test_case = TestCase(
        **payload.model_dump(exclude={"owner_id"}),
        owner_id=owner_id,
    )
    db.add(test_case)
    _commit_test_case_change(db)
    db.refresh(test_case)
    return test_case


def update_test_case(db: Session, test_case: TestCase, payload: TestCaseUpdate) -> TestCase:
    changes = payload.model_dump(exclude_unset=True)
    code = changes.get("code")
    if code is not None and code != test_case.code:
        _ensure_code_is_available(db, code)
    if "module_id" in changes:
        _ensure_module_exists(db, changes["module_id"])
    if "owner_id" in changes:
        _ensure_owner_exists(db, changes["owner_id"])

    for field, value in changes.items():
        setattr(test_case, field, value)

    _commit_test_case_change(db)
    db.refresh(test_case)
    return test_case


def delete_test_case(db: Session, test_case: TestCase) -> None:
    test_run_id = db.scalar(
        select(TestRun.id).where(TestRun.test_case_id == test_case.id).limit(1)
    )
    if test_run_id is not None:
        raise TestCaseInUseError("Test case has test runs and cannot be deleted")

    db.delete(test_case)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise TestCaseInUseError("Test case has test runs and cannot be deleted") from exc


def _ensure_code_is_available(db: Session, code: str) -> None:
    if db.scalar(select(TestCase.id).where(TestCase.code == code)) is not None:
        raise TestCaseCodeAlreadyExistsError("Test case code already exists")


def _ensure_module_exists(db: Session, module_id: int) -> None:
    if db.get(Module, module_id) is None:
        raise TestCaseModuleNotFoundError("Module not found")


def _ensure_owner_exists(db: Session, owner_id: int) -> None:
    if db.get(User, owner_id) is None:
        raise TestCaseOwnerNotFoundError("Owner user not found")


def _commit_test_case_change(db: Session) -> None:
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise TestCaseCodeAlreadyExistsError("Test case code already exists") from exc
