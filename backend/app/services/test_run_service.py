from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.test_case import TestCase
from app.models.test_run import TestRun, TestRunStatus
from app.models.user import User
from app.schemas.test_run import TestRunCreate
from app.services.access_service import ensure_test_case_can_be_run


class TestCaseNotFoundError(Exception):
    pass


class TestRunParametersValidationError(Exception):
    def __init__(self, errors: list[str]) -> None:
        self.errors = errors
        super().__init__("Invalid test run parameters")


def create_test_run(db: Session, payload: TestRunCreate, started_by_user: User) -> TestRun:
    test_case = db.scalar(select(TestCase).where(TestCase.code == payload.test_case_code))
    if test_case is None:
        raise TestCaseNotFoundError("Test case not found")
    ensure_test_case_can_be_run(test_case, started_by_user)
    _validate_parameters(test_case.input_schema, payload.parameters)

    test_run = TestRun(
        test_case_id=test_case.id,
        started_by_user_id=started_by_user.id,
        environment=payload.environment,
        parameters=payload.parameters,
        status=TestRunStatus.QUEUED,
    )
    db.add(test_run)
    db.commit()
    db.refresh(test_run)
    return test_run


def _validate_parameters(input_schema: dict[str, Any], parameters: dict[str, Any]) -> None:
    errors: list[str] = []
    for name, rule, is_required in _get_parameter_rules(input_schema):
        if is_required and name not in parameters:
            errors.append(f"Missing required parameter: {name}")
            continue
        if name not in parameters:
            continue

        expected_type = rule.get("type")
        if expected_type is None:
            continue
        if not _matches_type(parameters[name], expected_type):
            errors.append(f"Parameter {name} must be a {expected_type}")

    if errors:
        raise TestRunParametersValidationError(errors)


def _get_parameter_rules(input_schema: dict[str, Any]):
    properties = input_schema.get("properties")
    if isinstance(properties, dict):
        required = input_schema.get("required", [])
        required_fields = set(required) if isinstance(required, list) else set()
        for name, rule in properties.items():
            if isinstance(name, str) and isinstance(rule, dict):
                yield name, rule, bool(rule.get("required", name in required_fields))
        return

    for name, rule in input_schema.items():
        if isinstance(name, str) and isinstance(rule, dict):
            yield name, rule, bool(rule.get("required", False))


def _matches_type(value: Any, expected_type: str) -> bool:
    if expected_type == "string":
        return isinstance(value, str)
    if expected_type == "number":
        return isinstance(value, (int, float)) and not isinstance(value, bool)
    if expected_type == "boolean":
        return isinstance(value, bool)
    return True
