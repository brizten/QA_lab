from datetime import UTC, datetime

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import test_run as test_run_models
from app.models import test_run_step as step_models
from app.models.user import User, UserRole


def test_health(client: TestClient) -> None:
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_auth_flow_register_login_and_get_current_user(
    client: TestClient,
) -> None:
    email = "qa@example.com"
    password = "strong_password"

    register_response = client.post(
        "/api/auth/register",
        json={"email": email, "password": password, "full_name": "QA User"},
    )
    assert register_response.status_code == 201
    assert register_response.json()["email"] == email
    assert register_response.json()["role"] == UserRole.QA.value

    login_response = client.post(
        "/api/auth/login",
        json={"email": email, "password": password},
    )
    assert login_response.status_code == 200
    token = login_response.json()["access_token"]
    assert login_response.json()["token_type"] == "bearer"

    me_response = client.get(
        "/api/users/me",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert me_response.status_code == 200
    assert me_response.json()["email"] == email


def test_create_module_test_case_test_run_and_get_report(
    client: TestClient,
    db_session: Session,
) -> None:
    token = _register_admin_and_login(client, db_session)
    auth_headers = {"Authorization": f"Bearer {token}"}

    module_response = client.post(
        "/api/modules",
        headers=auth_headers,
        json={
            "code": "cards",
            "name": "Cards",
            "description": "Cards module",
        },
    )
    assert module_response.status_code == 201
    module = module_response.json()
    assert module["code"] == "cards"

    test_case_response = client.post(
        "/api/test-cases",
        headers=auth_headers,
        json={
            "code": "cards.issue_virtual_card",
            "name": "Issue virtual card",
            "description": "Smoke API test",
            "module_id": module["id"],
            "input_schema": {
                "iin": {"type": "string", "required": True},
                "force_fail": {"type": "boolean", "required": False},
            },
            "tags": ["smoke", "business", "cards"],
            "is_active": True,
        },
    )
    assert test_case_response.status_code == 201
    test_case = test_case_response.json()
    assert test_case["code"] == "cards.issue_virtual_card"

    run_response = client.post(
        "/api/test-runs",
        headers=auth_headers,
        json={
            "test_case_code": "cards.issue_virtual_card",
            "environment": "test",
            "parameters": {"iin": "990101300000"},
        },
    )
    assert run_response.status_code == 201
    run_payload = run_response.json()
    assert run_payload["status"] == test_run_models.TestRunStatus.QUEUED.value

    _complete_run_for_report(db_session, run_payload["run_id"])

    report_response = client.get(
        f"/api/test-runs/{run_payload['run_id']}/report",
        headers=auth_headers,
    )
    assert report_response.status_code == 200
    report = report_response.json()
    assert report["run"]["id"] == run_payload["run_id"]
    assert report["run"]["status"] == test_run_models.TestRunStatus.PASSED.value
    assert report["test_case"]["code"] == "cards.issue_virtual_card"
    assert report["module"]["code"] == "cards"
    assert report["started_by"]["email"] == "admin@example.com"
    assert [step["name"] for step in report["steps"]] == ["Validate input parameters"]
    assert report["steps"][0]["status"] == step_models.TestRunStepStatus.PASSED.value


def _register_admin_and_login(client: TestClient, db_session: Session) -> str:
    email = "admin@example.com"
    password = "strong_password"

    response = client.post(
        "/api/auth/register",
        json={"email": email, "password": password, "full_name": "Admin User"},
    )
    assert response.status_code == 201

    user = db_session.scalar(select(User).where(User.email == email))
    assert user is not None
    user.role = UserRole.ADMIN
    db_session.commit()

    login_response = client.post(
        "/api/auth/login",
        json={"email": email, "password": password},
    )
    assert login_response.status_code == 200
    return login_response.json()["access_token"]


def _complete_run_for_report(db_session: Session, test_run_id: int) -> None:
    now = datetime.now(UTC)
    test_run = db_session.get(test_run_models.TestRun, test_run_id)
    assert test_run is not None

    test_run.status = test_run_models.TestRunStatus.PASSED
    test_run.result = {"message": "Mock test completed successfully"}
    test_run.started_at = now
    test_run.finished_at = now
    test_run.duration_ms = 1

    db_session.add(
        step_models.TestRunStep(
            test_run_id=test_run_id,
            name="Validate input parameters",
            status=step_models.TestRunStepStatus.PASSED,
            started_at=now,
            finished_at=now,
            duration_ms=1,
            request_json={"iin": "990101300000"},
            response_json={"valid": True},
        )
    )
    db_session.commit()
