from __future__ import annotations

from pathlib import Path

from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase


def make_engine(url: str) -> AsyncEngine:
    if url.startswith("sqlite"):
        Path(url.split("///")[-1]).parent.mkdir(parents=True, exist_ok=True)
    return create_async_engine(url, future=True)


def make_session_factory(engine: AsyncEngine) -> async_sessionmaker[AsyncSession]:
    return async_sessionmaker(engine, expire_on_commit=False)


async def create_schema(engine: AsyncEngine, base: type[DeclarativeBase]) -> None:
    async with engine.begin() as conn:
        await conn.run_sync(base.metadata.create_all)

