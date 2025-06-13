"""
인증 관련 스키마 정의 (dataclasses 사용)
"""
from typing import Optional
from dataclasses import dataclass, field
from dataclasses_json import dataclass_json

@dataclass_json
@dataclass
class Token:
    """
    토큰 스키마
    
    Attributes:
        access_token (str): 액세스 토큰
        token_type (str): 토큰 타입
    """
    access_token: str
    token_type: str

@dataclass_json
@dataclass
class TokenData:
    """
    토큰 데이터 스키마
    
    Attributes:
        student_id (Optional[str]): 학번
    """
    student_id: Optional[str] = None

@dataclass_json
@dataclass
class UserBase:
    """
    사용자 기본 스키마
    
    Attributes:
        student_id (str): 학번
        name (str): 이름
        role (str): 역할 ('student' 또는 'professor')
    """
    student_id: str
    name: str
    role: str

@dataclass_json
@dataclass
class UserCreate(UserBase):
    """
    사용자 생성 스키마
    
    Attributes:
        password (str): 비밀번호
    """
    password: str

@dataclass_json
@dataclass
class UserLogin:
    """
    사용자 로그인 스키마
    
    Attributes:
        student_id (str): 학번
        password (str): 비밀번호
    """
    student_id: str
    password: str

@dataclass_json
@dataclass
class User(UserBase):
    """
    사용자 응답 스키마
    
    Attributes:
        id (int): 사용자 ID
        school (str): 학교 이름
        is_first_login (bool): 첫 로그인 여부
    """
    id: int
    school: str
    is_first_login: bool
    
    class Config:
        orm_mode = True 