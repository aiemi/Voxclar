from typing import AsyncGenerator

from fastapi import Depends, Header
from jose import JWTError
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker

from src.config import Settings, get_settings
from src.core.security import decode_access_token
from src.core.exceptions import Unauthorized

_engine = None
_session_factory = None


def _get_engine(settings: Settings):
    global _engine
    if _engine is None:
        _engine = create_async_engine(settings.DATABASE_URL, echo=settings.DEBUG, pool_size=20)
    return _engine


def _get_session_factory(settings: Settings):
    global _session_factory
    if _session_factory is None:
        engine = _get_engine(settings)
        _session_factory = async_sessionmaker(engine, expire_on_commit=False)
    return _session_factory


def get_session_factory():
    """Get session factory for non-Depends contexts (e.g. ASR API)."""
    return _get_session_factory(get_settings())

# Alias for import convenience
async_session_factory = None

def _ensure_async_session_factory():
    global async_session_factory
    if async_session_factory is None:
        async_session_factory = _get_session_factory(get_settings())
    return async_session_factory


async def get_db(
    settings: Settings = Depends(get_settings),
) -> AsyncGenerator[AsyncSession, None]:
    factory = _get_session_factory(settings)
    async with factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


async def get_current_user_id(
    authorization: str = Header(..., alias="Authorization"),
) -> str:
    if not authorization.startswith("Bearer "):
        raise Unauthorized("Invalid authorization header")
    token = authorization[7:]
    try:
        payload = decode_access_token(token)
        user_id = payload.get("sub")
        if not user_id:
            raise Unauthorized("Invalid token payload")
        return user_id
    except JWTError:
        raise Unauthorized("Invalid or expired token")
