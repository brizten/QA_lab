from typing import Annotated

from fastapi import APIRouter, Depends, status
from sqlalchemy import select

from app.api.deps import (
    MODULE_READ_ROLES,
    MODULE_WRITE_ROLES,
    DbSession,
    require_roles,
)
from app.models.module import Module
from app.models.user import User
from app.schemas.module import ModuleCreate, ModuleRead


router = APIRouter(prefix="/modules", tags=["modules"])


@router.get("/", response_model=list[ModuleRead])
def list_modules(
    db: DbSession,
    _current_user: Annotated[User, Depends(require_roles(*MODULE_READ_ROLES))],
) -> list[Module]:
    return list(db.scalars(select(Module).order_by(Module.code)))


@router.post("/", response_model=ModuleRead, status_code=status.HTTP_201_CREATED)
def create_module(
    payload: ModuleCreate,
    db: DbSession,
    _current_user: Annotated[User, Depends(require_roles(*MODULE_WRITE_ROLES))],
) -> Module:
    module = Module(**payload.model_dump())
    db.add(module)
    db.commit()
    db.refresh(module)
    return module
