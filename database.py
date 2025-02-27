from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from sqlalchemy.orm import declarative_base
from config import DATABASE_URL

# Database Engine
engine = create_async_engine(DATABASE_URL, echo=True)
SessionLocal = async_sessionmaker(bind=engine, expire_on_commit=False)

# Base Model
Base = declarative_base()

# Create Tables Function
async def create_tables():
    """Ensure tables exist in the database on startup."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

# Dependency for DB Session
async def get_db():
    async with SessionLocal() as db:
        try:
            yield db
            await db.commit()
        finally:
            await db.close()
