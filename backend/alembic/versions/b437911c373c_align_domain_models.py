"""align domain models

Revision ID: b437911c373c
Revises: dc006fdc794c
Create Date: 2026-06-21 14:53:56.483615
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = "b437911c373c"
down_revision: Union[str, Sequence[str], None] = "dc006fdc794c"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


user_role = postgresql.ENUM(
    "ADMIN",
    "AUTOTESTER",
    "QA",
    "BUSINESS",
    "VIEWER",
    name="user_role",
)
test_run_status = postgresql.ENUM(
    "QUEUED",
    "RUNNING",
    "PASSED",
    "FAILED",
    "BROKEN",
    "CANCELLED",
    "TIMEOUT",
    name="test_run_status",
)
test_run_step_status = postgresql.ENUM(
    "RUNNING",
    "PASSED",
    "FAILED",
    "BROKEN",
    "SKIPPED",
    name="test_run_step_status",
)
legacy_test_run_status = postgresql.ENUM(
    "PENDING",
    "RUNNING",
    "SUCCEEDED",
    "FAILED",
    name="test_run_status",
)


def upgrade() -> None:
    bind = op.get_bind()

    op.add_column("modules", sa.Column("code", sa.String(length=100), nullable=True))
    op.execute("UPDATE modules SET code = 'MODULE-' || id WHERE code IS NULL")
    op.alter_column("modules", "code", nullable=False)
    op.add_column(
        "modules",
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )
    op.drop_index(op.f("ix_modules_name"), table_name="modules")
    op.drop_index(op.f("ix_modules_owner_id"), table_name="modules")
    op.create_index(op.f("ix_modules_code"), "modules", ["code"], unique=True)
    op.drop_constraint("modules_owner_id_fkey", "modules", type_="foreignkey")
    op.drop_column("modules", "owner_id")

    op.add_column("test_cases", sa.Column("code", sa.String(length=100), nullable=True))
    op.execute("UPDATE test_cases SET code = 'TEST-' || id WHERE code IS NULL")
    op.alter_column("test_cases", "code", nullable=False)
    op.add_column("test_cases", sa.Column("input_schema", sa.JSON(), nullable=True))
    op.execute("UPDATE test_cases SET input_schema = '{}'::json WHERE input_schema IS NULL")
    op.alter_column("test_cases", "input_schema", nullable=False)
    op.add_column("test_cases", sa.Column("tags", sa.JSON(), nullable=True))
    op.execute("UPDATE test_cases SET tags = '[]'::json WHERE tags IS NULL")
    op.alter_column("test_cases", "tags", nullable=False)
    op.add_column("test_cases", sa.Column("owner_id", sa.Integer(), nullable=True))
    op.execute("UPDATE test_cases SET owner_id = created_by_id WHERE owner_id IS NULL")
    op.alter_column("test_cases", "owner_id", nullable=False)
    op.drop_index(op.f("ix_test_cases_created_by_id"), table_name="test_cases")
    op.drop_index(op.f("ix_test_cases_name"), table_name="test_cases")
    op.create_index(op.f("ix_test_cases_code"), "test_cases", ["code"], unique=True)
    op.create_index(op.f("ix_test_cases_owner_id"), "test_cases", ["owner_id"], unique=False)
    op.drop_constraint("test_cases_created_by_id_fkey", "test_cases", type_="foreignkey")
    op.drop_constraint("test_cases_module_id_fkey", "test_cases", type_="foreignkey")
    op.create_foreign_key(
        "fk_test_cases_owner_id_users",
        "test_cases",
        "users",
        ["owner_id"],
        ["id"],
        ondelete="RESTRICT",
    )
    op.create_foreign_key(
        "fk_test_cases_module_id_modules",
        "test_cases",
        "modules",
        ["module_id"],
        ["id"],
        ondelete="RESTRICT",
    )
    op.drop_column("test_cases", "execution_config")
    op.drop_column("test_cases", "created_by_id")

    op.add_column("test_run_steps", sa.Column("started_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("test_run_steps", sa.Column("duration_ms", sa.Integer(), nullable=True))
    op.add_column("test_run_steps", sa.Column("request_json", sa.JSON(), nullable=True))
    op.add_column("test_run_steps", sa.Column("response_json", sa.JSON(), nullable=True))
    op.add_column(
        "test_run_steps",
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )
    test_run_step_status.create(bind, checkfirst=True)
    op.execute("ALTER TABLE test_run_steps ALTER COLUMN status DROP DEFAULT")
    op.execute(
        """
        ALTER TABLE test_run_steps
        ALTER COLUMN status TYPE test_run_step_status
        USING (
            CASE status::text
                WHEN 'PENDING' THEN 'RUNNING'
                WHEN 'RUNNING' THEN 'RUNNING'
                WHEN 'SUCCEEDED' THEN 'PASSED'
                WHEN 'FAILED' THEN 'FAILED'
                ELSE 'BROKEN'
            END
        )::test_run_step_status
        """
    )
    op.execute(
        "ALTER TABLE test_run_steps "
        "ALTER COLUMN status SET DEFAULT 'RUNNING'::test_run_step_status"
    )
    op.drop_column("test_run_steps", "input_data")
    op.drop_column("test_run_steps", "step_order")
    op.drop_column("test_run_steps", "output_data")

    op.add_column("test_runs", sa.Column("started_by_user_id", sa.Integer(), nullable=True))
    op.execute("UPDATE test_runs SET started_by_user_id = initiated_by_id WHERE started_by_user_id IS NULL")
    op.alter_column("test_runs", "started_by_user_id", nullable=False)
    op.add_column(
        "test_runs",
        sa.Column("environment", sa.String(length=128), server_default="local", nullable=False),
    )
    op.add_column("test_runs", sa.Column("error_message", sa.String(length=2000), nullable=True))
    op.add_column("test_runs", sa.Column("duration_ms", sa.Integer(), nullable=True))
    op.add_column(
        "test_runs",
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )
    op.drop_index(op.f("ix_test_runs_celery_task_id"), table_name="test_runs")
    op.drop_index(op.f("ix_test_runs_initiated_by_id"), table_name="test_runs")
    op.create_index(
        op.f("ix_test_runs_started_by_user_id"),
        "test_runs",
        ["started_by_user_id"],
        unique=False,
    )
    op.drop_constraint("test_runs_initiated_by_id_fkey", "test_runs", type_="foreignkey")
    op.create_foreign_key(
        "fk_test_runs_started_by_user_id_users",
        "test_runs",
        "users",
        ["started_by_user_id"],
        ["id"],
        ondelete="RESTRICT",
    )
    op.drop_column("test_runs", "celery_task_id")
    op.drop_column("test_runs", "initiated_by_id")

    op.execute("ALTER TABLE test_runs ALTER COLUMN status DROP DEFAULT")
    op.execute("ALTER TYPE test_run_status RENAME TO test_run_status_legacy")
    test_run_status.create(bind, checkfirst=True)
    op.execute(
        """
        ALTER TABLE test_runs
        ALTER COLUMN status TYPE test_run_status
        USING (
            CASE status::text
                WHEN 'PENDING' THEN 'QUEUED'
                WHEN 'RUNNING' THEN 'RUNNING'
                WHEN 'SUCCEEDED' THEN 'PASSED'
                WHEN 'FAILED' THEN 'FAILED'
                ELSE 'BROKEN'
            END
        )::test_run_status
        """
    )
    op.execute(
        "ALTER TABLE test_runs ALTER COLUMN status SET DEFAULT 'QUEUED'::test_run_status"
    )
    op.execute("DROP TYPE test_run_status_legacy")

    user_role.create(bind, checkfirst=True)
    op.add_column(
        "users",
        sa.Column("role", user_role, server_default="VIEWER", nullable=False),
    )
    op.add_column(
        "users",
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )


def downgrade() -> None:
    bind = op.get_bind()

    op.drop_column("users", "updated_at")
    op.drop_column("users", "role")
    user_role.drop(bind, checkfirst=True)

    op.execute("ALTER TABLE test_runs ALTER COLUMN status DROP DEFAULT")
    op.execute("ALTER TYPE test_run_status RENAME TO test_run_status_new")
    legacy_test_run_status.create(bind, checkfirst=True)
    op.execute(
        """
        ALTER TABLE test_runs
        ALTER COLUMN status TYPE test_run_status
        USING (
            CASE status::text
                WHEN 'QUEUED' THEN 'PENDING'
                WHEN 'RUNNING' THEN 'RUNNING'
                WHEN 'PASSED' THEN 'SUCCEEDED'
                ELSE 'FAILED'
            END
        )::test_run_status
        """
    )
    op.execute("ALTER TABLE test_runs ALTER COLUMN status SET DEFAULT 'PENDING'::test_run_status")
    op.execute("DROP TYPE test_run_status_new")

    op.execute("ALTER TABLE test_run_steps ALTER COLUMN status DROP DEFAULT")
    op.execute(
        """
        ALTER TABLE test_run_steps
        ALTER COLUMN status TYPE test_run_status
        USING (
            CASE status::text
                WHEN 'RUNNING' THEN 'PENDING'
                WHEN 'PASSED' THEN 'SUCCEEDED'
                WHEN 'FAILED' THEN 'FAILED'
                ELSE 'FAILED'
            END
        )::test_run_status
        """
    )
    op.execute("ALTER TABLE test_run_steps ALTER COLUMN status SET DEFAULT 'PENDING'::test_run_status")
    test_run_step_status.drop(bind, checkfirst=True)

    op.add_column("test_runs", sa.Column("initiated_by_id", sa.Integer(), nullable=True))
    op.execute("UPDATE test_runs SET initiated_by_id = started_by_user_id WHERE initiated_by_id IS NULL")
    op.alter_column("test_runs", "initiated_by_id", nullable=False)
    op.add_column("test_runs", sa.Column("celery_task_id", sa.String(length=255), nullable=True))
    op.drop_constraint("fk_test_runs_started_by_user_id_users", "test_runs", type_="foreignkey")
    op.create_foreign_key(
        "test_runs_initiated_by_id_fkey",
        "test_runs",
        "users",
        ["initiated_by_id"],
        ["id"],
        ondelete="RESTRICT",
    )
    op.drop_index(op.f("ix_test_runs_started_by_user_id"), table_name="test_runs")
    op.create_index(op.f("ix_test_runs_initiated_by_id"), "test_runs", ["initiated_by_id"])
    op.create_index(op.f("ix_test_runs_celery_task_id"), "test_runs", ["celery_task_id"])
    op.drop_column("test_runs", "updated_at")
    op.drop_column("test_runs", "duration_ms")
    op.drop_column("test_runs", "error_message")
    op.drop_column("test_runs", "environment")
    op.drop_column("test_runs", "started_by_user_id")

    op.add_column("test_run_steps", sa.Column("output_data", sa.JSON(), nullable=True))
    op.add_column("test_run_steps", sa.Column("step_order", sa.Integer(), nullable=True))
    op.execute("UPDATE test_run_steps SET step_order = 0 WHERE step_order IS NULL")
    op.alter_column("test_run_steps", "step_order", nullable=False)
    op.add_column("test_run_steps", sa.Column("input_data", sa.JSON(), nullable=True))
    op.drop_column("test_run_steps", "updated_at")
    op.drop_column("test_run_steps", "response_json")
    op.drop_column("test_run_steps", "request_json")
    op.drop_column("test_run_steps", "duration_ms")
    op.drop_column("test_run_steps", "started_at")

    op.add_column("test_cases", sa.Column("created_by_id", sa.Integer(), nullable=True))
    op.execute("UPDATE test_cases SET created_by_id = owner_id WHERE created_by_id IS NULL")
    op.alter_column("test_cases", "created_by_id", nullable=False)
    op.add_column("test_cases", sa.Column("execution_config", sa.JSON(), nullable=True))
    op.execute("UPDATE test_cases SET execution_config = '{}'::json WHERE execution_config IS NULL")
    op.alter_column("test_cases", "execution_config", nullable=False)
    op.drop_constraint("fk_test_cases_owner_id_users", "test_cases", type_="foreignkey")
    op.drop_constraint("fk_test_cases_module_id_modules", "test_cases", type_="foreignkey")
    op.create_foreign_key(
        "test_cases_module_id_fkey",
        "test_cases",
        "modules",
        ["module_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.create_foreign_key(
        "test_cases_created_by_id_fkey",
        "test_cases",
        "users",
        ["created_by_id"],
        ["id"],
        ondelete="RESTRICT",
    )
    op.drop_index(op.f("ix_test_cases_owner_id"), table_name="test_cases")
    op.drop_index(op.f("ix_test_cases_code"), table_name="test_cases")
    op.create_index(op.f("ix_test_cases_name"), "test_cases", ["name"])
    op.create_index(op.f("ix_test_cases_created_by_id"), "test_cases", ["created_by_id"])
    op.drop_column("test_cases", "owner_id")
    op.drop_column("test_cases", "tags")
    op.drop_column("test_cases", "input_schema")
    op.drop_column("test_cases", "code")

    op.add_column("modules", sa.Column("owner_id", sa.Integer(), nullable=True))
    op.execute(
        "UPDATE modules SET owner_id = (SELECT id FROM users ORDER BY id LIMIT 1) "
        "WHERE owner_id IS NULL"
    )
    op.alter_column("modules", "owner_id", nullable=False)
    op.create_foreign_key(
        "modules_owner_id_fkey",
        "modules",
        "users",
        ["owner_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.drop_index(op.f("ix_modules_code"), table_name="modules")
    op.create_index(op.f("ix_modules_owner_id"), "modules", ["owner_id"])
    op.create_index(op.f("ix_modules_name"), "modules", ["name"])
    op.drop_column("modules", "updated_at")
    op.drop_column("modules", "code")
