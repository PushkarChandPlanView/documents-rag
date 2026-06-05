from typing import Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models.folder import Folder


async def create_folder(
    db: AsyncSession,
    user_id: UUID,
    name: str,
    parent_id: Optional[UUID] = None,
) -> Folder:
    if parent_id:
        parent = await get_folder(db, parent_id, user_id)
        if not parent:
            raise ValueError("Parent folder not found")

    folder = Folder(user_id=user_id, name=name, parent_id=parent_id)
    db.add(folder)
    await db.commit()
    await db.refresh(folder)
    return folder


async def get_folder(db: AsyncSession, folder_id: UUID, user_id: UUID) -> Optional[Folder]:
    result = await db.execute(
        select(Folder).where(Folder.id == folder_id, Folder.user_id == user_id)
    )
    return result.scalar_one_or_none()


async def list_folders(
    db: AsyncSession,
    user_id: UUID,
    parent_id: Optional[UUID] = None,
) -> list[Folder]:
    stmt = select(Folder).where(Folder.user_id == user_id)
    if parent_id is None:
        stmt = stmt.where(Folder.parent_id.is_(None))
    else:
        stmt = stmt.where(Folder.parent_id == parent_id)
    stmt = stmt.order_by(Folder.name)
    result = await db.execute(stmt)
    return list(result.scalars().all())


async def delete_folder(db: AsyncSession, folder_id: UUID, user_id: UUID) -> bool:
    folder = await get_folder(db, folder_id, user_id)
    if not folder:
        return False
    await db.delete(folder)
    await db.commit()
    return True
