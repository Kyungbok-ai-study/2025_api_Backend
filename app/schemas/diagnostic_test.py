"""
진단테스트 Pydantic 스키마
물리치료학과 진단테스트 API용 데이터 모델
"""
from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional
from datetime import datetime

class DiagnosticTestInfo(BaseModel):
    """진단테스트 기본 정보"""
    id: int
    title: str
    description: Optional[str] = None
    total_questions: int
    time_limit: int  # 분

class DiagnosticQuestionResponse(BaseModel):
    """진단테스트 문제 응답 형식"""
    id: int
    question_id: str
    question_number: int
    content: str
    options: Dict[str, str]
    difficulty_level: str
    domain: str
    points: float
    answered: bool = False
    user_answer: Optional[str] = None

class DiagnosticTestStart(BaseModel):
    """진단테스트 시작 응답"""
    submission_id: int
    test_info: DiagnosticTestInfo
    questions: List[DiagnosticQuestionResponse]
    remaining_time: int  # 초
    start_time: datetime
    progress: Dict[str, int]  # answered, unanswered

class DiagnosticAnswerSubmit(BaseModel):
    """문제 답안 제출"""
    submission_id: int
    question_id: int
    user_answer: str
    response_time: Optional[float] = None  # 응답 시간 (초)

class DiagnosticSubmissionCreate(BaseModel):
    """진단테스트 제출 생성"""
    test_id: int

class DiagnosticSubmissionResponse(BaseModel):
    """진단테스트 완료 응답"""
    submission_id: int
    total_score: float
    score_percentage: float
    correct_count: int
    wrong_count: int
    unanswered_count: int
    level_classification: str
    diagnostic_result: Dict[str, Any]
    completion_time: datetime
    can_access_service: bool

class DiagnosticAnalysisResult(BaseModel):
    """진단 분석 결과"""
    domain_analysis: Dict[str, Any]
    difficulty_analysis: Dict[str, Any]
    recommendations: List[str]
    bkt_analysis: Optional[Dict[str, Any]] = None
    dkt_analysis: Optional[Dict[str, Any]] = None
    rnn_analysis: Optional[Dict[str, Any]] = None 