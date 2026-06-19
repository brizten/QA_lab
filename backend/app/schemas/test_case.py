from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class TestCaseCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    description: str | None = None
    module_id: int
    execution_config: dict[str, Any] = Field(default_factory=dict)


class TestCaseRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    description: str | None
    execution_config: dict[str, Any]
    is_active: bool
    module_id: int
    created_by_id: int
    created_at: datetime
    updated_at: datetime
