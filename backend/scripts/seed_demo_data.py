from dataclasses import dataclass
from typing import Any

from sqlalchemy import select

from app.core.security import get_password_hash, verify_password
from app.db.database import SessionLocal
from app.models.module import Module
from app.models.test_case import TestCase
from app.models.user import User, UserRole


ADMIN_EMAIL = "admin@local.com"
ADMIN_PASSWORD = "admin"


@dataclass(frozen=True)
class ModuleSeed:
    code: str
    name: str
    description: str


@dataclass(frozen=True)
class TestCaseSeed:
    code: str
    name: str
    description: str
    module_code: str
    tags: list[str]
    input_schema: dict[str, Any]


MODULES = [
    ModuleSeed(
        code="cards",
        name="Cards",
        description="Card issuing and card servicing test cases",
    ),
    ModuleSeed(
        code="k2",
        name="K2",
        description="K2 payment processing test cases",
    ),
]

TEST_CASES = [
    TestCaseSeed(
        code="cards.issue_virtual_card",
        name="Issue virtual card",
        description="Demo runner test case for virtual card issuing",
        module_code="cards",
        tags=["smoke", "business", "cards"],
        input_schema={
            "iin": {"type": "string", "required": True},
            "product_code": {"type": "string", "required": True},
            "currency": {"type": "string", "required": True},
            "force_fail": {"type": "boolean", "required": False},
        },
    ),
    TestCaseSeed(
        code="k2.create_payment",
        name="Create payment",
        description="Demo runner test case for K2 payment creation",
        module_code="k2",
        tags=["smoke", "k2"],
        input_schema={
            "iin": {"type": "string", "required": True},
            "amount": {"type": "number", "required": True},
            "currency": {"type": "string", "required": True},
            "force_fail": {"type": "boolean", "required": False},
        },
    ),
]


def seed_demo_data() -> None:
    with SessionLocal() as session:
        admin = session.scalar(select(User).where(User.email == ADMIN_EMAIL))
        if admin is None:
            admin = User(
                email=ADMIN_EMAIL,
                hashed_password=get_password_hash(ADMIN_PASSWORD),
                full_name="Local Admin",
                role=UserRole.ADMIN,
                is_active=True,
            )
            session.add(admin)
            session.flush()
            print(f"Created admin user: {ADMIN_EMAIL}")
        else:
            updated_admin = False
            if admin.full_name != "Local Admin":
                admin.full_name = "Local Admin"
                updated_admin = True
            if admin.role != UserRole.ADMIN:
                admin.role = UserRole.ADMIN
                updated_admin = True
            if not admin.is_active:
                admin.is_active = True
                updated_admin = True
            try:
                password_matches = verify_password(ADMIN_PASSWORD, admin.hashed_password)
            except Exception:
                password_matches = False
            if not password_matches:
                admin.hashed_password = get_password_hash(ADMIN_PASSWORD)
                updated_admin = True
            message = "Updated admin user" if updated_admin else "Admin user already exists"
            print(f"{message}: {ADMIN_EMAIL}")

        modules_by_code: dict[str, Module] = {}
        for module_seed in MODULES:
            module = session.scalar(select(Module).where(Module.code == module_seed.code))
            if module is None:
                module = Module(
                    code=module_seed.code,
                    name=module_seed.name,
                    description=module_seed.description,
                )
                session.add(module)
                session.flush()
                print(f"Created module: {module_seed.code}")
            else:
                module.name = module_seed.name
                module.description = module_seed.description
                print(f"Updated module: {module_seed.code}")
            modules_by_code[module_seed.code] = module

        for test_case_seed in TEST_CASES:
            module = modules_by_code[test_case_seed.module_code]
            test_case = session.scalar(
                select(TestCase).where(TestCase.code == test_case_seed.code)
            )
            if test_case is None:
                test_case = TestCase(
                    code=test_case_seed.code,
                    name=test_case_seed.name,
                    description=test_case_seed.description,
                    module_id=module.id,
                    owner_id=admin.id,
                    input_schema=test_case_seed.input_schema,
                    tags=test_case_seed.tags,
                    is_active=True,
                )
                session.add(test_case)
                print(f"Created test case: {test_case_seed.code}")
            else:
                test_case.name = test_case_seed.name
                test_case.description = test_case_seed.description
                test_case.module_id = module.id
                test_case.owner_id = admin.id
                test_case.input_schema = test_case_seed.input_schema
                test_case.tags = test_case_seed.tags
                test_case.is_active = True
                print(f"Updated test case: {test_case_seed.code}")

        session.commit()
        print("Demo data seed completed successfully.")


if __name__ == "__main__":
    seed_demo_data()
