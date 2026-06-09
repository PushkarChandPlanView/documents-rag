from __future__ import annotations

import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel


class EditCreateRequest(BaseModel):
    instruction: str


class DocumentEditResponse(BaseModel):
    id: uuid.UUID
    document_id: uuid.UUID
    user_id: uuid.UUID
    instruction: str
    original_content: str
    proposed_content: str
    status: str
    version: int | None
    created_at: datetime

    model_config = {"from_attributes": True}


class EditListResponse(BaseModel):
    edits: list[DocumentEditResponse]


class EditStatusResponse(BaseModel):
    id: uuid.UUID
    status: Literal["pending", "approved", "rejected"]
