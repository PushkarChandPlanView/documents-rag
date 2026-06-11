"""
Unit and integration tests for the comment service.

Strategy:
- Unit tests mock the DB session to test business logic in isolation.
- Integration tests (marked `@pytest.mark.integration`) hit a real async session
  and are skipped in CI unless DATABASE_URL is set.
- Fixtures use factory helpers to avoid repetition.
- Each test is narrowly focused: one assertion per logical outcome.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import HTTPException

from schemas.comment import CommentCreate, CommentUpdate
from services import comment_service


# ── Fixtures ───────────────────────────────────────────────────────────────────

def _make_user(user_id: str = "user-1") -> MagicMock:
    u = MagicMock()
    u.id = user_id
    u.full_name = "Test User"
    u.avatar_url = None
    return u


def _make_comment(
    comment_id: str = "cmt-1",
    user_id: str = "user-1",
    document_id: str = "doc-1",
    parent_id: str | None = None,
    content: str = "Hello world",
    deleted_at: datetime | None = None,
) -> MagicMock:
    c = MagicMock()
    c.id = comment_id
    c.user_id = user_id
    c.document_id = document_id
    c.parent_id = parent_id
    c.content = content
    c.created_at = datetime(2025, 1, 1, tzinfo=timezone.utc)
    c.updated_at = datetime(2025, 1, 1, tzinfo=timezone.utc)
    c.deleted_at = deleted_at
    c.replies = []
    c.user = _make_user(user_id)
    return c


def _make_db() -> AsyncMock:
    db = AsyncMock()
    db.add = MagicMock()
    db.commit = AsyncMock()
    db.refresh = AsyncMock()
    db.delete = AsyncMock()
    return db


# ── _get_or_404 ────────────────────────────────────────────────────────────────

class TestGetOr404:
    @pytest.mark.asyncio
    async def test_returns_comment_when_found(self) -> None:
        db = _make_db()
        comment = _make_comment()
        db.execute.return_value.scalar_one_or_none.return_value = comment

        result = await comment_service._get_or_404(db, "cmt-1")

        assert result.id == "cmt-1"

    @pytest.mark.asyncio
    async def test_raises_404_when_not_found(self) -> None:
        db = _make_db()
        db.execute.return_value.scalar_one_or_none.return_value = None

        with pytest.raises(HTTPException) as exc_info:
            await comment_service._get_or_404(db, "missing")

        assert exc_info.value.status_code == 404

    @pytest.mark.asyncio
    async def test_raises_404_for_soft_deleted_comment(self) -> None:
        """_get_or_404 filters by deleted_at IS NULL at the DB level; returning
        None from the mock simulates a row that was soft-deleted."""
        db = _make_db()
        db.execute.return_value.scalar_one_or_none.return_value = None

        with pytest.raises(HTTPException) as exc_info:
            await comment_service._get_or_404(db, "cmt-deleted")

        assert exc_info.value.status_code == 404


# ── _assert_owner ──────────────────────────────────────────────────────────────

class TestAssertOwner:
    def test_passes_for_owner(self) -> None:
        comment = _make_comment(user_id="user-1")
        comment_service._assert_owner(comment, "user-1")  # no exception

    def test_raises_403_for_non_owner(self) -> None:
        comment = _make_comment(user_id="user-1")
        with pytest.raises(HTTPException) as exc_info:
            comment_service._assert_owner(comment, "user-2")
        assert exc_info.value.status_code == 403


# ── create_comment ─────────────────────────────────────────────────────────────

class TestCreateComment:
    @pytest.mark.asyncio
    async def test_creates_top_level_comment(self) -> None:
        db = _make_db()
        comment = _make_comment()
        db.refresh.side_effect = lambda c: None  # no-op

        with patch.object(comment_service, "_to_response", new=AsyncMock(return_value=MagicMock())):
            with patch("services.comment_service.Comment", return_value=comment):
                await comment_service.create_comment(
                    db,
                    "user-1",
                    CommentCreate(document_id="doc-1", content="Hello"),
                )

        db.add.assert_called_once()
        db.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_raises_400_when_parent_from_different_document(self) -> None:
        db = _make_db()
        parent = _make_comment(comment_id="parent-1", document_id="doc-OTHER")
        db.execute.return_value.scalar_one_or_none.return_value = parent

        with pytest.raises(HTTPException) as exc_info:
            await comment_service.create_comment(
                db,
                "user-1",
                CommentCreate(document_id="doc-1", content="Reply", parent_id="parent-1"),
            )

        assert exc_info.value.status_code == 400


# ── update_comment ─────────────────────────────────────────────────────────────

class TestUpdateComment:
    @pytest.mark.asyncio
    async def test_updates_content_for_owner(self) -> None:
        db = _make_db()
        comment = _make_comment(user_id="user-1", content="old")
        db.execute.return_value.scalar_one_or_none.return_value = comment

        with patch.object(comment_service, "_to_response", new=AsyncMock(return_value=MagicMock())):
            await comment_service.update_comment(
                db, "user-1", "cmt-1", CommentUpdate(content="new content")
            )

        assert comment.content == "new content"
        db.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_raises_403_for_non_owner(self) -> None:
        db = _make_db()
        comment = _make_comment(user_id="user-1")
        db.execute.return_value.scalar_one_or_none.return_value = comment

        with pytest.raises(HTTPException) as exc_info:
            await comment_service.update_comment(
                db, "user-2", "cmt-1", CommentUpdate(content="hacked")
            )

        assert exc_info.value.status_code == 403


# ── delete_comment ─────────────────────────────────────────────────────────────

class TestDeleteComment:
    @pytest.mark.asyncio
    async def test_soft_deletes_comment(self) -> None:
        db = _make_db()
        comment = _make_comment(user_id="user-1")
        db.execute.return_value.scalar_one_or_none.return_value = comment

        await comment_service.delete_comment(db, "user-1", "cmt-1")

        assert comment.deleted_at is not None
        db.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_raises_403_for_non_owner_delete(self) -> None:
        db = _make_db()
        comment = _make_comment(user_id="user-1")
        db.execute.return_value.scalar_one_or_none.return_value = comment

        with pytest.raises(HTTPException) as exc_info:
            await comment_service.delete_comment(db, "user-99", "cmt-1")

        assert exc_info.value.status_code == 403
        assert comment.deleted_at is None  # not mutated


# ── like / unlike ──────────────────────────────────────────────────────────────

class TestLikeComment:
    @pytest.mark.asyncio
    async def test_like_adds_row(self) -> None:
        db = _make_db()
        comment = _make_comment()
        # First execute → _get_or_404, second → exists check
        db.execute.side_effect = [
            MagicMock(scalar_one_or_none=MagicMock(return_value=comment)),
            MagicMock(scalar=MagicMock(return_value=False)),
        ]

        await comment_service.like_comment(db, "user-1", "cmt-1")

        db.add.assert_called_once()
        db.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_like_raises_409_on_duplicate(self) -> None:
        db = _make_db()
        comment = _make_comment()
        db.execute.side_effect = [
            MagicMock(scalar_one_or_none=MagicMock(return_value=comment)),
            MagicMock(scalar=MagicMock(return_value=True)),  # already liked
        ]

        with pytest.raises(HTTPException) as exc_info:
            await comment_service.like_comment(db, "user-1", "cmt-1")

        assert exc_info.value.status_code == 409

    @pytest.mark.asyncio
    async def test_unlike_removes_row(self) -> None:
        db = _make_db()
        comment = _make_comment()
        like_row = MagicMock()
        db.execute.side_effect = [
            MagicMock(scalar_one_or_none=MagicMock(return_value=comment)),
            MagicMock(scalar_one_or_none=MagicMock(return_value=like_row)),
        ]

        await comment_service.unlike_comment(db, "user-1", "cmt-1")

        db.delete.assert_called_once_with(like_row)
        db.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_unlike_raises_404_when_not_liked(self) -> None:
        db = _make_db()
        comment = _make_comment()
        db.execute.side_effect = [
            MagicMock(scalar_one_or_none=MagicMock(return_value=comment)),
            MagicMock(scalar_one_or_none=MagicMock(return_value=None)),
        ]

        with pytest.raises(HTTPException) as exc_info:
            await comment_service.unlike_comment(db, "user-1", "cmt-1")

        assert exc_info.value.status_code == 404


# ── Schema validation ──────────────────────────────────────────────────────────

class TestCommentSchemas:
    def test_content_stripped_on_create(self) -> None:
        c = CommentCreate(document_id="d1", content="  hello  ")
        assert c.content == "hello"

    def test_blank_content_raises_on_create(self) -> None:
        with pytest.raises(Exception):
            CommentCreate(document_id="d1", content="   ")

    def test_content_stripped_on_update(self) -> None:
        u = CommentUpdate(content="  updated  ")
        assert u.content == "updated"

    def test_content_too_long_raises(self) -> None:
        with pytest.raises(Exception):
            CommentCreate(document_id="d1", content="x" * 10_001)
