"""
문제 및 정답 업로드 스키마

파일 업로드 및 파싱 결과를 위한 Pydantic 스키마 정의
"""
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field
from datetime import datetime


class QuestionUploadResponse(BaseModel):
    """문제 업로드 응답 스키마"""
    success: bool
    message: str
    file_name: Optional[str] = None
    parsed_count: Optional[int] = None
    
    class Config:
        schema_extra = {
            "example": {
                "success": True,
                "message": "문제 파일이 성공적으로 업로드되었습니다.",
                "file_name": "2021_questions.pdf",
                "parsed_count": 100
            }
        }


class AnswerUploadResponse(BaseModel):
    """정답 업로드 응답 스키마"""
    success: bool
    message: str
    file_name: Optional[str] = None
    years_found: Optional[List[int]] = None
    total_answers: Optional[int] = None
    
    class Config:
        schema_extra = {
            "example": {
                "success": True,
                "message": "정답 파일이 성공적으로 업로드되었습니다.",
                "file_name": "물리치료_라벨링_결과.xlsx",
                "years_found": [2021, 2022, 2023, 2024],
                "total_answers": 400
            }
        }


class ParseAndMatchRequest(BaseModel):
    """파싱 및 매칭 요청 스키마"""
    question_file_path: str = Field(..., description="문제 파일 경로")
    answer_file_path: str = Field(..., description="정답 엑셀 파일 경로")
    source_name: Optional[str] = Field(None, description="출처 이름")
    create_embeddings: bool = Field(True, description="임베딩 생성 여부")
    gemini_api_key: Optional[str] = Field(None, description="Gemini API 키")
    
    class Config:
        schema_extra = {
            "example": {
                "question_file_path": "uploads/questions/2021_questions.json",
                "answer_file_path": "uploads/answers/물리치료_라벨링_결과.xlsx",
                "source_name": "물리치료사 국가시험",
                "create_embeddings": True
            }
        }


class ParseAndMatchResponse(BaseModel):
    """파싱 및 매칭 응답 스키마"""
    success: bool
    message: str
    total_questions: Optional[int] = None
    saved_questions: Optional[int] = None
    save_rate: Optional[str] = None
    results_by_year: Optional[Dict[str, Any]] = None
    errors: Optional[List[str]] = None
    
    class Config:
        schema_extra = {
            "example": {
                "success": True,
                "message": "문제와 정답이 성공적으로 매칭되어 저장되었습니다.",
                "total_questions": 400,
                "saved_questions": 380,
                "save_rate": "95.0%",
                "results_by_year": {
                    "2021": {"saved": 95, "total": 100, "match_rate": "95.0%"},
                    "2022": {"saved": 96, "total": 100, "match_rate": "96.0%"},
                    "2023": {"saved": 94, "total": 100, "match_rate": "94.0%"},
                    "2024": {"saved": 95, "total": 100, "match_rate": "95.0%"}
                }
            }
        }


class QuestionParseStatus(BaseModel):
    """문제 파싱 상태 스키마"""
    status: str = Field(..., description="처리 상태")
    progress: int = Field(..., description="진행률 (0-100)")
    current_step: str = Field(..., description="현재 진행 단계")
    processed_items: Optional[int] = None
    total_items: Optional[int] = None
    
    class Config:
        schema_extra = {
            "example": {
                "status": "processing",
                "progress": 45,
                "current_step": "문제 텍스트 파싱 중",
                "processed_items": 45,
                "total_items": 100
            }
        }


class MatchedQuestionData(BaseModel):
    """매칭된 문제 데이터 스키마 (새로운 스키마)"""
    question_number: int
    content: str
    description: Optional[List[str]] = None  # 문제 설명/지문 (선택사항)
    options: Dict[str, str]
    correct_answer: str
    subject: Optional[str] = None
    area_name: Optional[str] = None
    difficulty: str
    year: int
    
    class Config:
        schema_extra = {
            "example": {
                "question_number": 1,
                "content": "다음에서 설명하는 인체 기본조직은?",
                "description": [
                    "- 몸에 널리 분포하며, 몸의 구조를 이룸",
                    "- 세포나 기관 사이 틈을 메우고, 기관을 지지·보호함"
                ],
                "options": {
                    "1": "상피조직",
                    "2": "결합조직",
                    "3": "근육조직",
                    "4": "신경조직",
                    "5": "혈액조직"
                },
                "correct_answer": "2",
                "subject": "물리치료학",
                "area_name": "해부학",
                "difficulty": "중",
                "year": 2021
            }
        } 