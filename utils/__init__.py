from passlib.context import CryptContext
from datetime import datetime, timedelta
from jose import JWTError, jwt

attack_map = {
   'SQL Injection' : 'SQL',
   'XSS' : 'XSS',
   'RCE' : 'RCE',
   'File Inclusion' : 'FI'
}

# 옵션 그룹 : [옵션 : [옵션 설명, 입력값 필요 여부]]
nuclei_options = {
   'TEMPLATES' : {
      '-t': ['실행할 템플릿 또는 템플릿 디렉토리 목록 (쉼표로 구분, 파일)', True],
      '-td': ['템플릿 내용 표시', False]
   },
   'OUTPUT' : {
      '-silent': ['결과만 표시', False],
   },
   'CONFIGURATIONS' : {
      '-H' : ['모든 http 요청에 포함할 사용자 정의 헤더/쿠키 (header:value 형식) (cli, file)', True]
   },
   'DEBUG' : {
      '-debug': ['모든 요청과 응답 표시', False],
   },
   'ETC..' : {
      '-dast': ['DAST(동적 테스트)', False],
   }
}

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

SECRET_KEY = "[YOUR_SECRET_KEY]"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

def hash_password(password: str) -> str:
   """비밀번호 해싱"""
   return pwd_context.hash(password)

def verify_password(plain_password: str, hashed_password: str) -> bool:
   """비밀번호 검증"""
   return pwd_context.verify(plain_password, hashed_password)

def create_access_token(data: dict, expires_delta: timedelta = None) -> str:
   """JWT 토큰 생성"""
   to_encode = data.copy()
   expire = datetime.now() + (expires_delta or timedelta(minutes=15))
   to_encode.update({"exp": expire})
   return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

def decode_access_token(token: str):
   """JWT 토큰 디코딩"""
   try:
      payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
      username: str = payload.get("sub")
      if username is None:
         raise ValueError("Invalid token payload")
      return username
   except ValueError:
      raise ValueError("Invalid Token")