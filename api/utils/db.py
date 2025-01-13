from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker, declarative_base

DATABASE_URL = "sqlite+aiosqlite:///sqlite.db"

# SQLAlchemy engine 생성
engine = create_async_engine(
    DATABASE_URL, connect_args={"check_same_thread": False}
)

# DB 세션 생성
SessionLocal = sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False
)

# Base class 생성
Base = declarative_base()

async def get_db():
    db = SessionLocal()
    try: 
        yield db
    finally:
        await db.close()

# 테이블 생성
async def init_db():
    async with engine.begin() as conn:
        # await conn.run_sync(Base.metadata.drop_all) # Table model을 수정했을 때 실행하면 됨 (DB 초기화)
        await conn.run_sync(Base.metadata.create_all)