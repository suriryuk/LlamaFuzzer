import asyncio
from api.utils.db import engine, Base

async def init_db():
    async with engine.begin() as conn:
        # 기존 테이블 삭제
        await conn.run_sync(Base.metadata.drop_all())
        # 새 테이블 생성
        await conn.run_sync(Base.metadata.create_all())
    print("Database tables created!")

if __name__ == "__main__":
    asyncio.run(init_db())