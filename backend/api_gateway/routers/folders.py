import logging
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from dependencies import get_current_user, get_db
from models.user import User
from schemas.document import Item, ItemUpdateRequest
from schemas.folder import FolderCreate, FolderListResponse
from services import document_service as item_service
from services.auth_service import get_user_by_email

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/folders", tags=["folders"])


class BreadcrumbResponse(BaseModel):
    items: list[Item]


@router.post("", response_model=Item, status_code=status.HTTP_201_CREATED)
async def create_folder(
    body: FolderCreate,
    target_user_email: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    # Admin override: service accounts can create folders on behalf of another user.
    owner_id = current_user.id
    if target_user_email and getattr(current_user, "is_admin", False):
        target_user = await get_user_by_email(db, target_user_email)
        if target_user:
            owner_id = target_user.id
    try:
        folder = await item_service.create_folder_item(
            db=db,
            user_id=owner_id,
            name=body.name,
            parent_id=body.parent_id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    logger.info("Folder created: folder_id=%s user_id=%s (requester=%s)",
                folder.id, owner_id, current_user.id)
    return item_service._to_item(folder)


@router.get("", response_model=FolderListResponse)
async def list_folders(
    parent_id: Optional[UUID] = None,
    target_user_email: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    # Admin override: allow listing another user's folders (used by agent_service).
    owner_id = current_user.id
    if target_user_email and getattr(current_user, "is_admin", False):
        target_user = await get_user_by_email(db, target_user_email)
        if target_user:
            owner_id = target_user.id
    folders = await item_service.list_folders(db, owner_id, parent_id=parent_id)
    items = [item_service._to_item(f) for f in folders]
    return FolderListResponse(items=items, total=len(items))


@router.get("/{folder_id}/breadcrumb", response_model=BreadcrumbResponse)
async def get_folder_breadcrumb(
    folder_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    crumbs = await item_service.get_breadcrumb(db, folder_id, current_user.id)
    if not crumbs:
        raise HTTPException(status_code=404, detail="Folder not found")
    return BreadcrumbResponse(items=crumbs)


@router.get("/{folder_id}", response_model=Item)
async def get_folder(
    folder_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    folder = await item_service.get_item(db, folder_id, current_user.id)
    if not folder or folder.type != "folder":
        raise HTTPException(status_code=404, detail="Folder not found")
    return item_service._to_item(folder)


@router.patch("/{folder_id}", response_model=Item)
async def update_folder(
    folder_id: UUID,
    body: ItemUpdateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    item = await item_service.update_item(
        db,
        folder_id,
        current_user.id,
        name=body.name,
        description=body.description,
        clear_description=body.description is None and "description" in body.model_fields_set,
        parent_id=body.parent_id,
        clear_parent=body.parent_id is None and "parent_id" in body.model_fields_set,
    )
    if not item or item.type != "folder":
        raise HTTPException(status_code=404, detail="Folder not found")
    return item_service._to_item(item)


@router.delete("/{folder_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_folder(
    folder_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    item = await item_service.get_item(db, folder_id, current_user.id)
    if not item or item.type != "folder":
        raise HTTPException(status_code=404, detail="Folder not found")
    await item_service.delete_item(db, folder_id, current_user.id)
