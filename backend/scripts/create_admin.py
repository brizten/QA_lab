from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.core.security import get_password_hash
from app.db.database import SessionLocal
from app.models.user import User, UserRole


ADMIN_EMAIL = "admin@local.com"
ADMIN_PASSWORD = "admin"


def create_admin() -> None:
    with SessionLocal() as session:
        existing_user = session.scalar(select(User).where(User.email == ADMIN_EMAIL))
        if existing_user is not None:
            print(f"Admin user {ADMIN_EMAIL} already exists. No changes were made.")
            return

        admin_user = User(
            email=ADMIN_EMAIL,
            hashed_password=get_password_hash(ADMIN_PASSWORD),
            full_name="Local Admin",
            role=UserRole.ADMIN,
            is_active=True,
        )
        session.add(admin_user)

        try:
            session.commit()
        except IntegrityError:
            session.rollback()
            print(f"Admin user {ADMIN_EMAIL} already exists. No changes were made.")
            return

        print(f"Admin user {ADMIN_EMAIL} was created successfully.")


if __name__ == "__main__":
    create_admin()
