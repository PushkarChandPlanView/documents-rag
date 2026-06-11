"""
Comments router — thin HTTP layer; all logic delegated to comment_service.

Routes:
  POST   /api/v1/comments                     → create
  PUT    /api/v1/comments/{id}                 → update (owner only)
  DELETE /api/v1/comments/{id}                 → soft-delete (owner only)
  GET    /api/v1/documents/{document_id}/comments → paginated list with replies
  POST   /api/v1/comments/{id}/like            → like (409 if duplicate)
  DELETE /api/v1/comments/{id}/like            → unlike
"""
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from dependencies import get_current_user, get_db
from models.user import User
from schemas.comment import (
    CommentCreate,
    CommentResponse,
    CommentUpdate,
    EXAMPLE_COMMENT_RESPONSE,
    EXAMPLE_PAGINATED_RESPONSE,
    PaginatedComments,
)
from services import comment_service

router = APIRouter(prefix="/api/v1", tags=["comments"])


@router.post(
    "/comments",
    response_model=CommentResponse,
    status_code=status.HTTP_201_CREATED,
    responses={201: {"content": {"application/json": {"example": EXAMPLE_COMMENT_RESPONSE}}}},
    summary="Create a comment or reply",
)
async def create_comment(
    payload: CommentCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> CommentResponse:
    return await comment_service.create_comment(db, current_user.id, payload)


@router.put(
    "/comments/{comment_id}",
    response_model=CommentResponse,
    summary="Update comment content (author only)",
)
async def update_comment(
    comment_id: str,
    payload: CommentUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> CommentResponse:
    return await comment_service.update_comment(db, current_user.id, comment_id, payload)


@router.delete(
    "/comments/{comment_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Soft-delete a comment (author only)",
)
async def delete_comment(
    comment_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> None:
    await comment_service.delete_comment(db, current_user.id, comment_id)


@router.get(
    "/documents/{document_id}/comments",
    response_model=PaginatedComments,
    responses={200: {"content": {"application/json": {"example": EXAMPLE_PAGINATED_RESPONSE}}}},
    summary="List top-level comments with nested replies and like counts",
)
async def list_comments(
    document_id: str,
    page: int = Query(1, ge=1, description="Page number (1-based)"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> PaginatedComments:
    return await comment_service.list_comments(
        db, document_id, current_user.id, page, page_size
    )


@router.post(
    "/comments/{comment_id}/like",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Like a comment (409 if already liked)",
)
async def like_comment(
    comment_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> None:
    await comment_service.like_comment(db, current_user.id, comment_id)


@router.delete(
    "/comments/{comment_id}/like",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Remove a like from a comment",
)
async def unlike_comment(
    comment_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> None:
    await comment_service.unlike_comment(db, current_user.id, comment_id)
