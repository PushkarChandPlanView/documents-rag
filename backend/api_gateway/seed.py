"""Seed script: creates the default admin user."""
import asyncio
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from config import get_settings
from services.auth_service import create_user

settings = get_settings()


async def run() -> None:
    engine = create_async_engine(settings.postgres_url)
    try:
        async with AsyncSession(engine) as db:
            user = await create_user(db, "admin@example.com", "changeme")
            print(f"Created user: {user.email}")
    except Exception as e:
        print(f"Error (user may already exist): {e}")
    finally:
        await engine.dispose()


asyncio.run(run())
