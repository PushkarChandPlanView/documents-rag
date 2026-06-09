import logging
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from dependencies import get_current_user, get_db
from models.user import User
from schemas.edit import DocumentEditResponse, EditCreateRequest, EditListResponse
from services import document_edit_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/documents", tags=["edits"])


@router.post(
    "/{document_id}/edits",
    response_model=DocumentEditResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_edit(
    document_id: UUID,
    body: EditCreateRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> DocumentEditResponse:
    try:
        return await document_edit_service.create_edit_draft(
            doc_id=document_id,
            user_id=current_user.id,
            instruction=body.instruction,
            db=db,
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except Exception as exc:
        logger.error("Edit draft creation failed: %s", exc)
        raise HTTPException(status_code=502, detail="Failed to generate edit preview") from exc


@router.get("/{document_id}/edits", response_model=EditListResponse)
async def list_edits(
    document_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> EditListResponse:
    return await document_edit_service.list_edits(
        doc_id=document_id, user_id=current_user.id, db=db
    )


@router.post("/{document_id}/edits/{edit_id}/approve", response_model=DocumentEditResponse)
async def approve_edit(
    document_id: UUID,
    edit_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> DocumentEditResponse:
    try:
        return await document_edit_service.approve_edit(
            edit_id=edit_id, user_id=current_user.id, db=db
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/{document_id}/edits/{edit_id}/reject", response_model=DocumentEditResponse)
async def reject_edit(
    document_id: UUID,
    edit_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> DocumentEditResponse:
    try:
        return await document_edit_service.reject_edit(
            edit_id=edit_id, user_id=current_user.id, db=db
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
