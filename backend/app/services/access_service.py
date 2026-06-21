from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.test_case import TestCase
from app.models.test_run import TestRun
from app.models.user import User, UserRole


class TestCaseRunForbiddenError(Exception):
    pass


class TestRunAccessForbiddenError(Exception):
    pass


def list_visible_test_cases(db: Session, user: User) -> list[TestCase]:
    test_cases = list(db.scalars(select(TestCase).order_by(TestCase.code)))

    if user.role is UserRole.QA:
        return [test_case for test_case in test_cases if test_case.is_active]
    if user.role is UserRole.BUSINESS:
        return [
            test_case
            for test_case in test_cases
            if test_case.is_active and "business" in test_case.tags
        ]
    return test_cases


def ensure_test_case_can_be_run(test_case: TestCase, user: User) -> None:
    if user.role is UserRole.QA and not test_case.is_active:
        raise TestCaseRunForbiddenError("QA can only run active test cases")
    if user.role is UserRole.BUSINESS and (
        not test_case.is_active or "business" not in test_case.tags
    ):
        raise TestCaseRunForbiddenError(
            "Business users can only run active test cases tagged business"
        )


def list_visible_test_runs(db: Session, user: User) -> list[TestRun]:
    statement = select(TestRun).order_by(TestRun.created_at.desc())
    if user.role is UserRole.BUSINESS:
        statement = statement.where(TestRun.started_by_user_id == user.id)
    return list(db.scalars(statement))


def get_visible_test_run(db: Session, test_run_id: int, user: User) -> TestRun | None:
    test_run = db.get(TestRun, test_run_id)
    if test_run is not None and (
        user.role is UserRole.BUSINESS and test_run.started_by_user_id != user.id
    ):
        raise TestRunAccessForbiddenError("Test run access denied")
    return test_run
