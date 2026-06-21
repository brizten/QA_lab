from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class ModuleCreate(BaseModel):
    code: str = Field(min_length=1, max_length=100)
    name: str = Field(min_length=1, max_length=255)
    description: str | None = None


class ModuleUpdate(BaseModel):
    code: str | None = Field(default=None, min_length=1, max_length=100)
    name: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = None


class ModuleRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    code: str
    name: str
    description: str | None
    created_at: datetime
    updated_at: datetime
