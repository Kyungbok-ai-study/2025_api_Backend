"""
질문/문제 관련 스키마 정의
"""
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from datetime import datetime

class QuestionResponse(BaseModel):
    """
    질문 응답 스키마
    """
    id: int
    content: str
    question_type: str
    difficulty: int
    subject: str
    choices: Optional[List[str]] = None
    correct_answer: Optional[str] = None
    is_active: bool = True
    metadata: Optional[Dict[str, Any]] = None
    created_at: datetime
    
    class Config:
        from_attributes = True

class QuestionCreate(BaseModel):
    """
    질문 생성 스키마
    """
    content: str
    question_type: str
    difficulty: int
    subject: str
    choices: Optional[List[str]] = None
    correct_answer: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None

class QuestionUpdate(BaseModel):
    """
    질문 수정 스키마
    """
    content: Optional[str] = None
    question_type: Optional[str] = None
    difficulty: Optional[int] = None
    subject: Optional[str] = None
    choices: Optional[List[str]] = None
    correct_answer: Optional[str] = None
    is_active: Optional[bool] = None
    metadata: Optional[Dict[str, Any]] = None 