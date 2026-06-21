from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class TestCaseCreate(BaseModel):
    code: str = Field(min_length=1, max_length=100)
    name: str = Field(min_length=1, max_length=255)
    description: str | None = None
    module_id: int
    input_schema: dict[str, Any] = Field(default_factory=dict)
    tags: list[str] = Field(default_factory=list)


class TestCaseRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    code: str
    name: str
    description: str | None
    input_schema: dict[str, Any]
    tags: list[str]
    is_active: bool
    module_id: int
    owner_id: int
    created_at: datetime
    updated_at: datetime
