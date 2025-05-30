"""
AI 서비스 API 엔드포인트
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Dict, Any, Optional

from app.db.database import get_db
from app.auth.dependencies import get_current_user
from app.models.user import User
from app.services.ai_service import enhanced_ai_service

router = APIRouter()

@router.get("/analyze/learning-pattern")
async def analyze_learning_pattern(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """학습 패턴 AI 분석"""
    try:
        return await enhanced_ai_service.analyze_learning_pattern(
            db=db,
            user_id=current_user.id
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"학습 패턴 분석 실패: {str(e)}")

@router.get("/generate/study-path")
async def generate_personalized_study_path(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """개인 맞춤 학습 경로 생성"""
    try:
        return await enhanced_ai_service.generate_personalized_study_path(
            db=db,
            user_id=current_user.id
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"학습 경로 생성 실패: {str(e)}")

@router.get("/predict/performance")
async def predict_performance(
    subject: str = Query(..., description="예측할 과목"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """성과 예측"""
    try:
        return await enhanced_ai_service.predict_performance(
            db=db,
            user_id=current_user.id,
            subject=subject
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"성과 예측 실패: {str(e)}")

@router.post("/generate/adaptive-questions")
async def generate_adaptive_questions(
    difficulty_target: float = Query(..., ge=0.0, le=1.0, description="목표 난이도"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> List[Dict[str, Any]]:
    """적응형 문제 생성"""
    try:
        return await enhanced_ai_service.generate_adaptive_questions(
            db=db,
            user_id=current_user.id,
            difficulty_target=difficulty_target
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"적응형 문제 생성 실패: {str(e)}")

@router.get("/analyze/mistakes")
async def analyze_mistake_patterns(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """실수 패턴 분석"""
    try:
        return await enhanced_ai_service.analyze_mistake_patterns(
            db=db,
            user_id=current_user.id
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"실수 패턴 분석 실패: {str(e)}")

@router.post("/generate/feedback")
async def generate_motivational_feedback(
    recent_performance: Dict[str, Any],
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> Dict[str, str]:
    """동기부여 피드백 생성"""
    try:
        feedback = await enhanced_ai_service.generate_motivational_feedback(
            db=db,
            user_id=current_user.id,
            recent_performance=recent_performance
        )
        return {"feedback": feedback}
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"피드백 생성 실패: {str(e)}")

@router.get("/insights/comprehensive")
async def get_comprehensive_ai_insights(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """종합 AI 인사이트"""
    try:
        # 모든 AI 분석을 병렬로 실행
        import asyncio
        
        pattern_task = enhanced_ai_service.analyze_learning_pattern(db, current_user.id)
        study_path_task = enhanced_ai_service.generate_personalized_study_path(db, current_user.id)
        mistake_task = enhanced_ai_service.analyze_mistake_patterns(db, current_user.id)
        
        pattern_analysis, study_path, mistake_analysis = await asyncio.gather(
            pattern_task, study_path_task, mistake_task
        )
        
        return {
            "learning_pattern": pattern_analysis,
            "recommended_study_path": study_path,
            "mistake_analysis": mistake_analysis,
            "generated_at": datetime.now().isoformat(),
            "ai_confidence_score": 0.85
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"종합 인사이트 생성 실패: {str(e)}") 