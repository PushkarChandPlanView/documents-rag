from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, field_validator


class FolderCreate(BaseModel):
    name: str
    parent_id: Optional[UUID] = None

    @field_validator("name")
    @classmethod
    def name_not_empty(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("Folder name cannot be empty")
        return v


class FolderResponse(BaseModel):
    id: UUID
    name: str
    parent_id: Optional[UUID] = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class FolderListResponse(BaseModel):
    items: list[FolderResponse]
    total: int
