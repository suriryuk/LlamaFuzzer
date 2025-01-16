from api.routes import router
from api.utils.db import init_db

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from contextlib import asynccontextmanager

import logging

# FastAPI 서버가 실행되고 종료될 때 실행되는 함수 정의 ( 최근에는 lifespan을 사용할 것을 권장하는 중 )
@asynccontextmanager
async def lifespan(app: FastAPI):
    logging.info('FastAPI Server Start')

    # db 초기화
    await init_db()

    yield

    logging.info('FastAPI Server Stop')

# FastAPI APP
app = FastAPI(lifespan=lifespan)

app.include_router(router, prefix='', tags=["api"])

app.mount('/assets', StaticFiles(directory="static"))

# logger 설정
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')

httpx_logger = logging.getLogger('httpx')
httpx_logger.setLevel(logging.WARNING)

# file handler를 추가하여 로그를 AIFuzz.log에 저장
file_handler = logging.FileHandler('AIFuzz.log', encoding='utf-8')
file_handler.setLevel(logging.INFO) # 파일에 기록할 로그 레벨 설정
formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s') # 로그 포맷 설정
file_handler.setFormatter(formatter)

# 루트 logger에 file handler 추가
logging.getLogger().addHandler(file_handler)

if __name__ == '__main__':
    import uvicorn
    uvicorn.run("main:app", host='0.0.0.0', port=8000, reload=True)