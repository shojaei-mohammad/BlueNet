from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession

from tgbot.config import DbConfig


def create_engine(db: DbConfig, echo=False):
    engine = create_async_engine(
        db.construct_sqlalchemy_url(),
        query_cache_size=1200,
        pool_size=20,
        max_overflow=200,
        future=True,
        echo=echo,
    )
    return engine


def create_session_pool(engine):
    """
    Create and return an async session pool with the event listener registered.
    """
    session_pool = async_sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False
    )
    return session_pool
