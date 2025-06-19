"""
진단테스트 단계별 분석 API
1차: 초기 진단 분석
2차~: 비교분석 및 학습추세 분석
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import Dict, Any, Optional

from app.db.database import get_db
from app.auth.dependencies import get_current_user
from app.models.user import User
from app.services.diagnosis_progress_service import DiagnosisProgressService

router = APIRouter(prefix="/diagnosis/analysis", tags=["diagnosis-analysis"])

@router.get("/comprehensive/{department}")
async def get_comprehensive_diagnosis_analysis(
    department: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    🎯 사용자의 종합 진단 분석
    
    - 1차 완료: 초기 진단 분석 (강점/약점, 학습 상태, 개인화 추천)
    - 2차 이상: 비교분석 및 학습추세 (성과 비교, 발전 추이, 약점 개선)
    """
    try:
        service = DiagnosisProgressService(db)
        analysis = await service.get_comprehensive_analysis(current_user.id, department)
        
        return {
            "success": True,
            "data": analysis,
            "message": f"{department} 진단 분석이 완료되었습니다."
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"진단 분석 조회 실패: {str(e)}"
        )

@router.get("/initial/{department}")
async def get_initial_diagnosis_analysis(
    department: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    🔍 1차 진단테스트 초기 분석 (강제 초기 분석 모드)
    
    테스트용으로 1차 분석 형태를 확인할 때 사용
    """
    try:
        service = DiagnosisProgressService(db)
        
        # 가장 최근 완료된 세션 조회
        from app.models.unified_diagnosis import DiagnosisSession, DiagnosisTest
        from sqlalchemy import and_
        
        latest_session = db.query(DiagnosisSession).join(
            DiagnosisTest, DiagnosisSession.test_id == DiagnosisTest.id
        ).filter(
            and_(
                DiagnosisSession.user_id == current_user.id,
                DiagnosisTest.department == department,
                DiagnosisSession.status == "completed"
            )
        ).order_by(DiagnosisSession.completed_at.desc()).first()
        
        if not latest_session:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="완료된 진단테스트가 없습니다."
            )
        
        analysis = await service._generate_initial_diagnosis_analysis(
            current_user.id, latest_session, department
        )
        
        return {
            "success": True,
            "data": analysis,
            "message": f"{department} 초기 진단 분석이 완료되었습니다."
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"초기 진단 분석 실패: {str(e)}"
        )

@router.get("/comparative/{department}")
async def get_comparative_trend_analysis(
    department: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    📈 비교분석 및 학습추세 분석 (2차 이상)
    
    여러 차수 완료 시 비교분석과 학습추세를 제공
    """
    try:
        service = DiagnosisProgressService(db)
        
        # 완료된 세션들 조회
        from app.models.unified_diagnosis import DiagnosisSession, DiagnosisTest
        from sqlalchemy import and_
        
        completed_sessions = db.query(DiagnosisSession).join(
            DiagnosisTest, DiagnosisSession.test_id == DiagnosisTest.id
        ).filter(
            and_(
                DiagnosisSession.user_id == current_user.id,
                DiagnosisTest.department == department,
                DiagnosisSession.status == "completed"
            )
        ).order_by(DiagnosisSession.completed_at).all()
        
        if len(completed_sessions) < 2:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="비교분석을 위해서는 최소 2차 이상의 진단테스트가 필요합니다."
            )
        
        analysis = await service._generate_comparative_trend_analysis(
            current_user.id, completed_sessions, department
        )
        
        return {
            "success": True,
            "data": analysis,
            "message": f"{department} 비교분석 및 학습추세 분석이 완료되었습니다."
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"비교분석 실패: {str(e)}"
        )

@router.get("/progress-summary/{department}")
async def get_progress_summary(
    department: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    📊 진단테스트 진행 요약 정보
    
    완료된 차수, 전체 진행률, 평균 점수 등 요약 정보 제공
    """
    try:
        from app.models.unified_diagnosis import DiagnosisSession, DiagnosisTest
        from sqlalchemy import and_, func
        
        # 완료된 세션들 조회
        completed_sessions = db.query(DiagnosisSession).join(
            DiagnosisTest, DiagnosisSession.test_id == DiagnosisTest.id
        ).filter(
            and_(
                DiagnosisSession.user_id == current_user.id,
                DiagnosisTest.department == department,
                DiagnosisSession.status == "completed"
            )
        ).order_by(DiagnosisSession.completed_at).all()
        
        if not completed_sessions:
            return {
                "success": True,
                "data": {
                    "completed_rounds": 0,
                    "total_rounds": 10,
                    "completion_rate": 0.0,
                    "average_score": 0.0,
                    "best_score": 0.0,
                    "latest_score": 0.0,
                    "trend": "시작 전"
                },
                "message": "아직 완료된 진단테스트가 없습니다."
            }
        
        # 기본 통계 계산
        scores = [session.percentage_score for session in completed_sessions if session.percentage_score]
        
        # 추세 계산 (최근 3개 세션 기준)
        recent_scores = scores[-3:] if len(scores) >= 3 else scores
        trend = "상승" if len(recent_scores) >= 2 and recent_scores[-1] > recent_scores[0] else "안정"
        
        summary = {
            "completed_rounds": len(completed_sessions),
            "total_rounds": 10,
            "completion_rate": round(len(completed_sessions) / 10 * 100, 1),
            "average_score": round(sum(scores) / len(scores), 1) if scores else 0.0,
            "best_score": round(max(scores), 1) if scores else 0.0,
            "latest_score": round(scores[-1], 1) if scores else 0.0,
            "trend": trend,
            "completed_dates": [session.completed_at.isoformat() for session in completed_sessions],
            "score_history": [round(score, 1) for score in scores]
        }
        
        return {
            "success": True,
            "data": summary,
            "message": f"{department} 진행 요약 정보입니다."
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"진행 요약 조회 실패: {str(e)}"
        ) 