from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.module import Module
from app.models.test_case import TestCase
from app.schemas.module import ModuleCreate, ModuleUpdate


class ModuleCodeAlreadyExistsError(Exception):
    pass


class ModuleInUseError(Exception):
    pass


def get_module(db: Session, module_id: int) -> Module | None:
    return db.get(Module, module_id)


def create_module(db: Session, payload: ModuleCreate) -> Module:
    if db.scalar(select(Module.id).where(Module.code == payload.code)) is not None:
        raise ModuleCodeAlreadyExistsError("Module code already exists")

    module = Module(**payload.model_dump())
    db.add(module)
    _commit_module_change(db)
    db.refresh(module)
    return module


def update_module(db: Session, module: Module, payload: ModuleUpdate) -> Module:
    changes = payload.model_dump(exclude_unset=True)
    code = changes.get("code")
    if code is not None and code != module.code:
        existing_module_id = db.scalar(select(Module.id).where(Module.code == code))
        if existing_module_id is not None:
            raise ModuleCodeAlreadyExistsError("Module code already exists")

    for field, value in changes.items():
        setattr(module, field, value)

    _commit_module_change(db)
    db.refresh(module)
    return module


def delete_module(db: Session, module: Module) -> None:
    test_case_id = db.scalar(select(TestCase.id).where(TestCase.module_id == module.id).limit(1))
    if test_case_id is not None:
        raise ModuleInUseError("Module is used by test cases and cannot be deleted")

    db.delete(module)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise ModuleInUseError("Module is used by test cases and cannot be deleted") from exc


def _commit_module_change(db: Session) -> None:
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise ModuleCodeAlreadyExistsError("Module code already exists") from exc
