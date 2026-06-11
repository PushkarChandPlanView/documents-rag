"""
Comment service — all business logic lives here, routers stay thin.

Design decisions:
- `_get_or_404` is the single choke-point for comment lookup; all mutations go
  through it so 404 semantics are consistent.
- `_assert_owner` is separate from `_get_or_404` so admin-bypass can be added
  later without touching mutation methods.
- Like count and liked-by-me are fetched in ONE aggregate query per comment to
  avoid extra round-trips.
- `delete_comment` is a soft-delete: sets `deleted_at`, preserving replies.
- `list_comments` only loads top-level comments (parent_id IS NULL) and relies on
  `selectin` loading for replies, keeping the query set bounded.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import List

from fastapi import HTTPException, status
from sqlalchemy import exists, func, select
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from models.comment import Comment, CommentLike
from schemas.comment import (
    CommentAuthor,
    CommentCreate,
    CommentResponse,
    CommentUpdate,
    PaginatedComments,
)


# ── Private helpers ────────────────────────────────────────────────────────────

async def _get_or_404(db: AsyncSession, comment_id: str) -> Comment:
    """Return a live (non-deleted) comment or raise 404."""
    result = await db.execute(
        select(Comment)
        .options(selectinload(Comment.user), selectinload(Comment.replies))
        .where(
            Comment.id == comment_id,
            Comment.deleted_at.is_(None),
        )
    )
    comment = result.scalar_one_or_none()
    if comment is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Comment {comment_id} not found",
        )
    return comment


def _assert_owner(comment: Comment, user_id: str) -> None:
    """Raise 403 if user is not the comment author."""
    if str(comment.user_id) != str(user_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not authorised to modify this comment",
        )


async def _like_stats(
    db: AsyncSession, comment_id: str, user_id: str
) -> tuple[int, bool]:
    """Return (total_likes, liked_by_current_user) in a single query."""
    row = await db.execute(
        select(
            func.count(CommentLike.id).label("total"),
            func.count(CommentLike.id)
            .filter(CommentLike.user_id == user_id)
            .label("mine"),
        ).where(CommentLike.comment_id == comment_id)
    )
    r = row.one()
    return int(r.total), r.mine > 0


async def _to_response(
    db: AsyncSession, comment: Comment, user_id: str
) -> CommentResponse:
    """Convert ORM Comment → CommentResponse, including recursive replies."""
    like_count, liked_by_me = await _like_stats(db, comment.id, user_id)

    # Only recurse into non-deleted replies (selectin already loaded them)
    replies: List[CommentResponse] = [
        await _to_response(db, r, user_id)
        for r in comment.replies
        if r.deleted_at is None
    ]

    return CommentResponse(
        id=str(comment.id),
        document_id=str(comment.document_id),
        parent_id=str(comment.parent_id) if comment.parent_id else None,
        content=comment.content,
        author=CommentAuthor(
            id=str(comment.user.id),
            name=" ".join(filter(None, [comment.user.first_name, comment.user.last_name])) or comment.user.email,
            avatar=None,
        ),
        created_at=comment.created_at,
        updated_at=comment.updated_at,
        like_count=like_count,
        liked_by_me=liked_by_me,
        replies=replies,
    )


# ── Public service functions ───────────────────────────────────────────────────

async def create_comment(
    db: AsyncSession,
    user_id: str,
    payload: CommentCreate,
) -> CommentResponse:
    # Validate parent belongs to the same document
    if payload.parent_id:
        parent = await _get_or_404(db, payload.parent_id)
        if parent.document_id != payload.document_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Parent comment belongs to a different document",
            )

    comment = Comment(
        user_id=user_id,
        document_id=payload.document_id,
        parent_id=payload.parent_id,
        content=payload.content,
    )
    db.add(comment)
    await db.commit()

    # Re-fetch with relationships eagerly loaded
    result = await db.execute(
        select(Comment)
        .options(selectinload(Comment.user), selectinload(Comment.replies))
        .where(Comment.id == comment.id)
    )
    comment = result.scalar_one()
    return await _to_response(db, comment, user_id)


async def update_comment(
    db: AsyncSession,
    user_id: str,
    comment_id: str,
    payload: CommentUpdate,
) -> CommentResponse:
    comment = await _get_or_404(db, comment_id)
    _assert_owner(comment, user_id)
    comment.content = payload.content
    comment.updated_at = datetime.utcnow()
    await db.commit()

    result = await db.execute(
        select(Comment)
        .options(selectinload(Comment.user), selectinload(Comment.replies))
        .where(Comment.id == comment.id)
    )
    comment = result.scalar_one()
    return await _to_response(db, comment, user_id)


async def delete_comment(
    db: AsyncSession,
    user_id: str,
    comment_id: str,
) -> None:
    """Soft-delete preserves the row so existing replies stay attached."""
    comment = await _get_or_404(db, comment_id)
    _assert_owner(comment, user_id)
    comment.deleted_at = datetime.now(timezone.utc)
    await db.commit()


async def list_comments(
    db: AsyncSession,
    document_id: str,
    user_id: str,
    page: int = 1,
    page_size: int = 20,
) -> PaginatedComments:
    offset = (page - 1) * page_size

    # Count top-level, non-deleted comments for this document
    total_result = await db.execute(
        select(func.count(Comment.id)).where(
            Comment.document_id == document_id,
            Comment.parent_id.is_(None),
            Comment.deleted_at.is_(None),
        )
    )
    total = total_result.scalar_one()

    # Fetch page of top-level comments with all nested relationships eagerly loaded
    page_result = await db.execute(
        select(Comment)
        .options(
            selectinload(Comment.user),
            selectinload(Comment.replies).selectinload(Comment.user),
            selectinload(Comment.replies).selectinload(Comment.replies).selectinload(Comment.user),
        )
        .where(
            Comment.document_id == document_id,
            Comment.parent_id.is_(None),
            Comment.deleted_at.is_(None),
        )
        .order_by(Comment.created_at.desc())
        .limit(page_size)
        .offset(offset)
    )
    comments = page_result.scalars().all()

    items = [await _to_response(db, c, user_id) for c in comments]

    return PaginatedComments(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        has_next=(offset + page_size) < total,
    )


async def like_comment(db: AsyncSession, user_id: str, comment_id: str) -> None:
    await _get_or_404(db, comment_id)

    already = await db.execute(
        select(
            exists().where(
                CommentLike.user_id == user_id,
                CommentLike.comment_id == comment_id,
            )
        )
    )
    if already.scalar():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="You have already liked this comment",
        )

    db.add(CommentLike(user_id=user_id, comment_id=comment_id))
    await db.commit()


async def unlike_comment(db: AsyncSession, user_id: str, comment_id: str) -> None:
    await _get_or_404(db, comment_id)

    result = await db.execute(
        select(CommentLike).where(
            CommentLike.user_id == user_id,
            CommentLike.comment_id == comment_id,
        )
    )
    like = result.scalar_one_or_none()
    if like is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Like not found",
        )
    await db.delete(like)
    await db.commit()
