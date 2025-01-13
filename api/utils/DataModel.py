from pydantic import BaseModel
from typing import List, Optional

# 데이터 모델 정의
class Option(BaseModel):
    option: str
    value: Optional[str] = None

class RequestData(BaseModel):
    target_url: str
    selected_options: List[Option]
    ai_option: bool