from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select

from app.api.deps import (
    MODULE_READ_ROLES,
    MODULE_WRITE_ROLES,
    DbSession,
    require_roles,
)
from app.models.module import Module
from app.models.user import User
from app.schemas.module import ModuleCreate, ModuleRead, ModuleUpdate
from app.services.module_service import (
    ModuleCodeAlreadyExistsError,
    ModuleInUseError,
    create_module as create_module_record,
    delete_module as delete_module_record,
    get_module,
    update_module as update_module_record,
)


router = APIRouter(prefix="/modules", tags=["modules"])


@router.get("", response_model=list[ModuleRead])
def list_modules(
    db: DbSession,
    _current_user: Annotated[User, Depends(require_roles(*MODULE_READ_ROLES))],
) -> list[Module]:
    return list(db.scalars(select(Module).order_by(Module.code)))


@router.post("", response_model=ModuleRead, status_code=status.HTTP_201_CREATED)
def create_module(
    payload: ModuleCreate,
    db: DbSession,
    _current_user: Annotated[User, Depends(require_roles(*MODULE_WRITE_ROLES))],
) -> Module:
    try:
        return create_module_record(db, payload)
    except ModuleCodeAlreadyExistsError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.get("/{module_id}", response_model=ModuleRead)
def read_module(
    module_id: int,
    db: DbSession,
    _current_user: Annotated[User, Depends(require_roles(*MODULE_READ_ROLES))],
) -> Module:
    return _get_module_or_404(db, module_id)


@router.put("/{module_id}", response_model=ModuleRead)
def update_module(
    module_id: int,
    payload: ModuleUpdate,
    db: DbSession,
    _current_user: Annotated[User, Depends(require_roles(*MODULE_WRITE_ROLES))],
) -> Module:
    module = _get_module_or_404(db, module_id)
    try:
        return update_module_record(db, module, payload)
    except ModuleCodeAlreadyExistsError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.delete("/{module_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_module(
    module_id: int,
    db: DbSession,
    _current_user: Annotated[User, Depends(require_roles(*MODULE_WRITE_ROLES))],
) -> None:
    module = _get_module_or_404(db, module_id)
    try:
        delete_module_record(db, module)
    except ModuleInUseError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


def _get_module_or_404(db: DbSession, module_id: int) -> Module:
    module = get_module(db, module_id)
    if module is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Module not found")
    return module
