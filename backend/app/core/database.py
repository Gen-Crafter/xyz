from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase
from app.core.config import get_settings

settings = get_settings()

engine = create_async_engine(settings.database_url, echo=False, pool_size=20, max_overflow=10)
async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


async def get_db() -> AsyncSession:
    async with async_session() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def init_db():
    import asyncio
    import logging

    # Import ALL models so Base.metadata knows about every table
    import app.models.db_models  # noqa: F401

    _logger = logging.getLogger("aigp.db")
    max_retries = 10
    retry_delay = 3  # seconds

    for attempt in range(1, max_retries + 1):
        try:
            async with engine.begin() as conn:
                await conn.run_sync(Base.metadata.create_all)
            _logger.info("All database tables created/verified successfully")
            return
        except Exception as e:
            if attempt < max_retries:
                _logger.warning(
                    "DB init attempt %d/%d failed: %s — retrying in %ds",
                    attempt, max_retries, e, retry_delay,
                )
                await asyncio.sleep(retry_delay)
            else:
                _logger.error("DB init failed after %d attempts: %s", max_retries, e)
                raise
