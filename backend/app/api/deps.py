from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jwt import InvalidTokenError
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.security import decode_access_token
from app.db.database import get_db
from app.models.user import User, UserRole


oauth2_scheme = OAuth2PasswordBearer(tokenUrl=f"{settings.api_prefix}/auth/login")
DbSession = Annotated[Session, Depends(get_db)]
MODULE_READ_ROLES = tuple(UserRole)
MODULE_WRITE_ROLES = (UserRole.ADMIN, UserRole.AUTOTESTER)
TEST_CASE_READ_ROLES = tuple(UserRole)
TEST_CASE_WRITE_ROLES = (UserRole.ADMIN, UserRole.AUTOTESTER)
TEST_RUN_CREATE_ROLES = (
    UserRole.ADMIN,
    UserRole.AUTOTESTER,
    UserRole.QA,
    UserRole.BUSINESS,
)
REPORT_READ_ROLES = tuple(UserRole)


def get_current_user(db: DbSession, token: Annotated[str, Depends(oauth2_scheme)]) -> User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = decode_access_token(token)
        subject = payload.get("sub")
        user_id = int(subject) if subject is not None else None
    except (InvalidTokenError, TypeError, ValueError):
        raise credentials_exception

    user = db.get(User, user_id) if user_id is not None else None
    if user is None:
        raise credentials_exception
    return user


def get_current_active_user(current_user: Annotated[User, Depends(get_current_user)]) -> User:
    if not current_user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Inactive user")
    return current_user


CurrentUser = Annotated[User, Depends(get_current_active_user)]


def require_roles(*roles: UserRole):
    allowed_roles = frozenset(roles)

    def role_checker(current_user: CurrentUser) -> User:
        if current_user.role is UserRole.ADMIN or current_user.role in allowed_roles:
            return current_user
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient permissions",
        )

    return role_checker
