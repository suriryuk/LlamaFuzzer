from fastapi import APIRouter, HTTPException, status, WebSocket, WebSocketDisconnect,Request, UploadFile, Form, Cookie, Depends, File
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse, RedirectResponse
from starlette.websockets import WebSocketState

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from jose.exceptions import ExpiredSignatureError

from typing import Annotated, List
import pandas as pd
import json
import asyncio
import os

from api.utils.db import get_db
from api.models.models import User

from ai.train import UnslothTrainer
from ai.generator import process_chat, process_fuzz_payload
from ai.template import template_format

from utils import attack_map, nuclei_options, hash_password, verify_password, create_access_token, decode_access_token

router = APIRouter()

templates = Jinja2Templates(directory="templates")

# SQL : SELECT * FROM users WHERE username=username LIMIT 1
async def get_user_by_username(db: AsyncSession, username: str):
    """사용자 이름으로 사용자 검색"""
    result = await db.execute(select(User).where(User.username == username))
    return result.scalars().first()

# login 여부 체크
async def auth_login(SessionToken):
    """JWT 인증 여부 확인"""
    if SessionToken is None:
        # 인증되지 않은 경우
        return (False, '')
    
    # JWT 디코딩 및 검증
    try:
        username = decode_access_token(SessionToken)
    except ExpiredSignatureError: # JWT 세션 만료 시
        return (False, '')
    except Exception as e:
        return (False, '')
    
    # 인증 성공 시 사용자 정보 return
    return (True, username)

# stream process의 출력을 캡처하여 websocket으로 전송
async def read_output(stream, websocket: WebSocket):
    while True:
        try:
            line = await stream.readline()
        except asyncio.exceptions.LimitOverrunError:
            pass
    
        if not line:
            break

        print(f'{line.decode().strip()}')
        await websocket.send_text(f'{line.decode().strip()}')

# nuclei 실행 함수
async def run_nuclei(arguments, websocket: WebSocket):
    """Nuclei를 비동기적으로 실행하고 출력을 websocket을 통해 프론트엔드로 전송"""
    print('run_nuclei 실행')
    process = await asyncio.create_subprocess_exec(
        os.path.join(os.path.expanduser("~"), 'go', 'bin', 'nuclei'),
        *arguments,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    
    print('process 변수 정의')

    # Nuclei의 출력을 실시간 전송
    await asyncio.gather(
        read_output(process.stdout, websocket),
        read_output(process.stderr, websocket)
    )
    
    await websocket.send_text('Nuclei Running Complete')

# Main Page
@router.get('/', response_class=HTMLResponse)
async def index(
    request: Request,
    SessionToken: Annotated[str | None, Cookie()] = None
):
    # 세션 검증
    is_logged_in, username = await auth_login(SessionToken)
    if not is_logged_in:
        return RedirectResponse(url='/login', status_code=status.HTTP_302_FOUND)

    return templates.TemplateResponse("index.html", {"request": request, "is_logged_in": is_logged_in, "username": username})

# Generate Payload Page
@router.get('/payload', response_class=HTMLResponse)
async def payload(
    request: Request,
    SessionToken: Annotated[str | None, Cookie()] = None
):
    # 세션 검증
    is_logged_in, username = await auth_login(SessionToken)
    if not is_logged_in:
        return RedirectResponse(url='/login', status_code=status.HTTP_302_FOUND)
    
    return templates.TemplateResponse("payload.html", {"request": request, "is_logged_in": is_logged_in, "username": username})

# Generate Payload
@router.websocket('/ws/payload')
async def generate_payload(websocket: WebSocket):
    await websocket.accept()

    try:
        message = await websocket.receive_text()
        data = json.loads(message)
        payload_yaml = await process_fuzz_payload(data['attack'])

        await websocket.send_text(payload_yaml)
    except Exception as e:
        print(f"Error : {str(e)}")
    finally:
        await websocket.close()

# LLM Fine-Tuning Page
@router.get('/train', response_class=HTMLResponse)
async def train(
    request: Request,
    SessionToken: Annotated[str | None, Cookie()] = None
):
    # 세션 검증
    is_logged_in, username = await auth_login(SessionToken)
    if not is_logged_in:
        return RedirectResponse(url='/login', status_code=status.HTTP_302_FOUND)

    return templates.TemplateResponse("train.html", {"request": request, "is_logged_in": is_logged_in, "username": username})

# csv 데이터셋 업로드 기능
@router.post('/upload-csv')
async def upload_csv(file: UploadFile = File(...)):
    file_location = f'./csv/{file.filename}'
    with open(file_location, 'wb+') as file_object:
        file_object.write(await file.read())

    # csv 미리 보기
    df = pd.read_csv(file_location, encoding='latin1')

    # NaN 값을 ''로 대체
    df.fillna('', inplace=True)
    print(df)

    preview = df.head(10).to_dict(orient="records") # 상위 10줄 미리 보기
    return {'preview': preview}

# Fine-Tuning 요청을 처리하는 웹 소켓
@router.websocket('/ws/train')
async def train_websocket_endpoint(websocket: WebSocket):
    await websocket.accept()

    try:
        data = await websocket.receive_text()
        request_data = json.loads(data)
        filename = request_data['fileName']
        attack = request_data['attackType']

        # unsloth 학습기 로드
        trainer = UnslothTrainer(attack, attack_map)

        await websocket.send_text("UnslothTrainer Ready")

        await websocket.send_text("Load Model Started...")
        # 모델, 토크나이저 로드
        model, tokenizer = trainer.load_model()
        await websocket.send_text("Load Model End...")

        await websocket.send_text("Load Dataset Started...")
        # 데이터셋 로드
        dataset = trainer.load_dataset(filename)
        await websocket.send_text("Load Dataset End...")

        # 학습
        await trainer.train(websocket, dataset)
    except Exception as e:
        await websocket.send_text(f"Error : {str(e)}")
    finally:
        await websocket.close()

# 퍼징을 수행하는 페이지
@router.get('/fuzz', response_class=HTMLResponse)
async def fuzz_page(
    request: Request,
    SessionToken: Annotated[str | None, Cookie()] = None
):
    # 세션 검증
    is_logged_in, username = await auth_login(SessionToken)
    if not is_logged_in:
        return RedirectResponse(url='/login', status_code=status.HTTP_302_FOUND)
    
    return templates.TemplateResponse("fuzz.html", {
        "request": request, 
        "is_logged_in": is_logged_in, 
        "username": username,
        "nuclei_options": nuclei_options
    })

@router.websocket('/ws/fuzz')
async def fuzzing(websocket: WebSocket):
    await websocket.accept()
    try:
        # data json parsing
        data = await websocket.receive_text()
        request_data = json.loads(data)
        print(f'request data : {request_data}')

        # Nuclei 실행
        arguments = ['-u', request_data['target_url']]

        # AI payload 사용 여부 체크
        if request_data['ai_option']:
            try:
                await websocket.send_text('AI payload generation start')
                # AI Payload 생성
                payload_yaml = await process_fuzz_payload(request_data['attack'])
                await websocket.send_text('AI payload generation success')
                arguments.append('-t')
                arguments.append(f'./ai/payloads.yaml')
            except Exception as e:
                await websocket.send_text('AI payload generation failed')
                await websocket.send_text(f'Error : {e}')

        # 옵션 추가
        for option in request_data['selected_options']:
            if option['value'] == '':
                arguments.append(f'{option['option']}')
            else:
                arguments.append(f'{option['option']}')
                arguments.append(f'{option['value']}')
        await websocket.send_text(f'nuclei command : nuclei {' '.join(arguments)}')

        # Nuclei 실행 후 실시간 로그 출력
        await run_nuclei(arguments, websocket)
    except WebSocketDisconnect:
        print('Client Disconnected.')
    except Exception as e:
        await websocket.send_text(f"Error : {e}")
    finally:
        if websocket.client_state == WebSocketState.CONNECTED:
            await websocket.close()

# LLM과 채팅하는 페이지
@router.get('/chat', response_class=HTMLResponse)
async def chat_page(
    request: Request,
    SessionToken: Annotated[str | None, Cookie()] = None
):
    # 세션 검증
    is_logged_in, username = await auth_login(SessionToken)
    if not is_logged_in:
        return RedirectResponse(url='/login', status_code=status.HTTP_302_FOUND)
    
    return templates.TemplateResponse("chat.html", {
        "request": request, 
        "is_logged_in": is_logged_in, 
        "username": username,
    })

@router.websocket('/ws/chat')
async def chat(websocket: WebSocket):
    await websocket.accept()

    previous_msgs : List[str] = [] # 이전 메시지 저장 (채팅 내역 기억)

    try:
        while True:
            question = await websocket.receive_text()
            print(question)


            if question == '끝' or question == 'end':
                await websocket.send_text('LlamaFuzzer Chat Finish')
                break

            # 이전 메시지를 기반으로 context 생성
            # context = '\n'.join(previous_msgs)
            context = ''

            # 질문에 대한 답변
            answer = await process_chat(question, context)

            # 질문과 답변 저장
            previous_msgs.append(f'질문: {question}')
            previous_msgs.append(f'답변: {answer}')

            # 클라이언트에게 답변 전송
            await websocket.send_text(answer)
    except WebSocketDisconnect:
        print('Client Disconnected.')
    except Exception as e:
        print(f"Error: {e}")
    finally:
        if websocket.client_state == WebSocketState.CONNECTED:
            await websocket.close()

# Login Page
@router.get('/login', response_class=HTMLResponse)
async def login_page(request: Request): 
    return templates.TemplateResponse("login.html", {"request": request})

@router.post('/login', response_class=HTMLResponse)
async def login_user(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
    db: AsyncSession = Depends(get_db)
):
    """로그인 요청 처리"""
    user = await get_user_by_username(db, username)

    if not user or not verify_password(password, user.hashed_password):
        error_message = "Invalid username or password"
        return templates.TemplateResponse(
            "login.html",
            {"request": request, "error_message": error_message},
            status_code=status.HTTP_401_UNAUTHORIZED,
        )
    
    # 로그인 성공 시 JWT 발급
    access_token = create_access_token(data={"sub": user.username})

    # 로그인 성공 후 리다이렉션 또는 토큰 반환
    response = RedirectResponse(url="/", status_code=status.HTTP_302_FOUND)
    response.set_cookie(key='SessionToken', value=access_token, httponly=True)
    return response

# Register Page
@router.get('/register', response_class=HTMLResponse)
async def register_page(request: Request):
    return templates.TemplateResponse("register.html", {"request": request})


@router.post('/register')
async def register_user(
    username: str = Form(...),
    password: str = Form(...),
    name: str = Form(...),
    email: str = Form(...),
    db: AsyncSession = Depends(get_db)
):
    """회원가입 처리"""
    # 사용자 중복 체크
    existing_user = await db.execute(
        select(User).where((User.username == username) | (User.email == email))
    )

    if existing_user.scalars().first():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail='Username or email already exists.',
        )
    
    # 새로운 사용자 생성
    new_user = User(
        username=username,
        hashed_password=hash_password(password),
        full_name=name,
        email=email,
    )
    db.add(new_user)
    await db.commit()

    # 성공 시 로그인 페이지로 리다이렉션
    return RedirectResponse(url='/login', status_code=status.HTTP_302_FOUND)

# logout
@router.get('/logout')
async def logout(
    db: AsyncSession = Depends(get_db),
    SessionToken: Annotated[str | None, Cookie()] = None
):
    """로그아웃 처리"""
    response = RedirectResponse(url="/", status_code=status.HTTP_302_FOUND)
    response.delete_cookie('SessionToken')
    return response