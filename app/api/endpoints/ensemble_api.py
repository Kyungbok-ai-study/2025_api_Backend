"""
앙상블 AI 시스템 API 엔드포인트
DeepSeek + Gemini + OpenAI GPT 3단계 파이프라인
"""

from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel
from typing import Dict, Any, List, Optional
import logging

from app.services.ensemble_service import ensemble_service

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/ensemble", tags=["Ensemble AI"])

# 요청 모델들
class EnsembleRequest(BaseModel):
    question: str
    difficulty_level: str = "medium"
    department: str = "일반학과"
    target_audience: str = "university_students"

class BatchEnsembleRequest(BaseModel):
    questions: List[Dict[str, Any]]
    max_concurrent: int = 3

@router.post("/process")
async def process_educational_content(request: EnsembleRequest) -> Dict[str, Any]:
    """
    교육 콘텐츠 3단계 앙상블 처리
    
    단계:
    1. DeepSeek: 문제 분석 및 핵심 개념 추출
    2. Gemini: 교육적 설명 생성
    3. OpenAI GPT: 한국어 문체 개선
    """
    try:
        logger.info(f"앙상블 처리 요청: {request.question[:50]}...")
        
        result = await ensemble_service.process_educational_content(
            question=request.question,
            difficulty_level=request.difficulty_level,
            department=request.department,
            target_audience=request.target_audience
        )
        
        return result
        
    except Exception as e:
        logger.error(f"앙상블 처리 오류: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/batch")
async def batch_process_content(request: BatchEnsembleRequest) -> Dict[str, Any]:
    """배치 처리"""
    try:
        results = await ensemble_service.batch_process(
            questions=request.questions,
            max_concurrent=request.max_concurrent
        )
        
        return {
            "success": True,
            "total_processed": len(results),
            "results": results
        }
        
    except Exception as e:
        logger.error(f"배치 처리 오류: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/status")
async def get_system_status() -> Dict[str, Any]:
    """시스템 상태 조회"""
    try:
        return await ensemble_service.get_system_status()
    except Exception as e:
        logger.error(f"상태 조회 오류: {e}")
        raise HTTPException(status_code=500, detail=str(e)) 