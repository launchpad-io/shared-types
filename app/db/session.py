# """
# Database session management
# """

# from typing import AsyncGenerator
# from contextlib import asynccontextmanager

# from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
# from sqlalchemy.orm import sessionmaker

# from app.core.config import settings

# # Create async engine
# engine = create_async_engine(
#     settings.DATABASE_URL,
#     echo=settings.DEBUG,
#     future=True
# )

# # Create async session factory
# AsyncSessionLocal = async_sessionmaker(
#     engine,
#     class_=AsyncSession,
#     expire_on_commit=False
# )


# async def get_db() -> AsyncGenerator[AsyncSession, None]:
#     """
#     Dependency to get database session.
    
#     Yields:
#         AsyncSession: Database session
#     """
#     async with AsyncSessionLocal() as session:
#         try:
#             yield session
#         finally:
#             await session.close()


# @asynccontextmanager
# async def get_db_context():
#     """
#     Context manager for database session.
#     Useful for non-FastAPI contexts like scripts or tests.
    
#     Usage:
#         async with get_db_context() as db:
#             # use db session here
#     """
#     async with AsyncSessionLocal() as session:
#         try:
#             yield session
#             await session.commit()
#         except Exception:
#             await session.rollback()
#             raise
#         finally:
#             await session.close()


# Update your app/db/session.py file:

"""
Database session management
"""

from typing import AsyncGenerator
from contextlib import asynccontextmanager

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import sessionmaker

from app.core.config import settings

# Create async engine with cache disabled
engine = create_async_engine(
    settings.DATABASE_URL,
    echo=settings.DEBUG,
    future=True,
    pool_pre_ping=True,  # Test connections before using them
    pool_size=20,
    max_overflow=40,
    # Disable prepared statement caching to avoid enum issues
    connect_args={
        "server_settings": {
            "jit": "off"
        },
        "prepared_statement_cache_size": 0,  # Disable statement cache
        "prepared_statement_name_func": lambda: None,  # Don't use prepared statements
    }
)

# Create async session factory
AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False
)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    Dependency to get database session.
    
    Yields:
        AsyncSession: Database session
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()


@asynccontextmanager
async def get_db_context():
    """
    Context manager for database session.
    Useful for non-FastAPI contexts like scripts or tests.
    
    Usage:
        async with get_db_context() as db:
            # use db session here
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()