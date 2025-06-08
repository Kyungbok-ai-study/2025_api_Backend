"""
문제 검토 및 승인 관련 스키마
"""
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field
from datetime import datetime
from enum import Enum

class ApprovalStatus(str, Enum):
    """승인 상태"""
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"

class QuestionPreviewItem(BaseModel):
    """문제 미리보기 항목"""
    id: Optional[int] = None
    question_number: int = Field(..., description="문제 번호")
    content: str = Field(..., description="문제 내용")
    description: Optional[List[str]] = Field(None, description="문제 설명/지문")
    options: Dict[str, str] = Field(..., description="선택지")
    correct_answer: str = Field(..., description="정답")
    subject: Optional[str] = Field(None, description="과목명")
    area_name: Optional[str] = Field(None, description="영역이름")
    difficulty: str = Field(..., description="난이도")
    year: Optional[int] = Field(None, description="연도")
    
    # 파일 정보
    file_title: Optional[str] = Field(None, description="파일 제목")
    file_category: Optional[str] = Field(None, description="파일 카테고리")
    
    # 수정 이력
    last_modified_by: Optional[int] = None
    last_modified_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True

class ParsedFilePreview(BaseModel):
    """파싱된 파일 미리보기"""
    file_name: str = Field(..., description="파일명")
    parsed_at: datetime = Field(..., description="파싱 시간")
    total_questions: int = Field(..., description="총 문제 수")
    questions: List[QuestionPreviewItem] = Field(..., description="문제 목록")
    source_file_path: str = Field(..., description="원본 파일 경로")
    parsed_data_path: str = Field(..., description="파싱된 JSON 파일 경로")
    
    class Config:
        from_attributes = True

class QuestionUpdateRequest(BaseModel):
    """문제 수정 요청"""
    question_id: int = Field(..., description="문제 ID")
    content: Optional[str] = Field(None, description="문제 내용")
    description: Optional[List[str]] = Field(None, description="문제 설명/지문")
    options: Optional[Dict[str, str]] = Field(None, description="선택지")
    correct_answer: Optional[str] = Field(None, description="정답")
    subject: Optional[str] = Field(None, description="과목명")
    area_name: Optional[str] = Field(None, description="영역이름")
    difficulty: Optional[str] = Field(None, description="난이도")

class BulkApprovalRequest(BaseModel):
    """일괄 승인 요청"""
    question_ids: List[int] = Field(..., description="승인할 문제 ID 목록")
    action: ApprovalStatus = Field(..., description="승인/거부")
    feedback: Optional[str] = Field(None, description="피드백 메시지")

class QuestionApprovalResponse(BaseModel):
    """문제 승인 응답"""
    success: bool
    message: str
    approved_count: Optional[int] = None
    rejected_count: Optional[int] = None
    failed_count: Optional[int] = None

class QuestionHistoryItem(BaseModel):
    """문제 수정 이력 항목"""
    modified_at: datetime
    modified_by: int
    modified_by_name: str
    action: str  # created, updated, approved, rejected
    changes: Optional[Dict[str, Any]] = None

class QuestionDetailResponse(BaseModel):
    """문제 상세 정보 응답"""
    question: QuestionPreviewItem
    approval_status: ApprovalStatus
    approved_by: Optional[int] = None
    approved_by_name: Optional[str] = None
    approved_at: Optional[datetime] = None
    history: List[QuestionHistoryItem] = [] 