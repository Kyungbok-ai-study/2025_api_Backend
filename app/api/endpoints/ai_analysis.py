"""
AI 난이도 분석 API 엔드포인트
"""
from fastapi import APIRouter, Depends, HTTPException, status
from datetime import datetime
import logging

from ...models.user import User
from app.auth.dependencies import get_current_user

logger = logging.getLogger(__name__)

router = APIRouter()

def check_professor_permission(current_user: User):
    """교수 권한 확인"""
    if current_user.role != "professor":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="교수만 접근할 수 있습니다."
        )


@router.get("/status")
async def get_ai_analysis_status(
    current_user: User = Depends(get_current_user)
):
    """AI 난이도 분석 시스템 상태 조회"""
    check_professor_permission(current_user)
    
    try:
        from app.services.ai_difficulty_analyzer import difficulty_analyzer
        
        # AI 분석 시스템 상태 체크
        learning_summary = difficulty_analyzer.get_learning_summary()
        
        # 사용자 부서에 맞는 학과 매핑
        department_mapping = {
            "물리치료학과": "물리치료",
            "작업치료학과": "작업치료"
        }
        
        user_dept = department_mapping.get(current_user.department, current_user.department)
        dept_patterns = learning_summary.get("departments", {}).get(user_dept, {})
        
        return {
            "success": True,
            "data": {
                "ai_available": True,
                "department": user_dept,
                "learning_status": {
                    "question_mappings": dept_patterns.get("question_mappings", 0),
                    "difficulty_distribution": dept_patterns.get("difficulty_distribution", {}),
                    "total_evaluators": dept_patterns.get("total_evaluators", 0),
                    "confidence": dept_patterns.get("pattern_confidence", "unknown")
                },
                "features": [
                    "문제번호별 난이도 패턴 학습",
                    "딥시크 AI 내용 분석", 
                    "6명 평가위원 패턴 평균화",
                    "실시간 자동 분석"
                ],
                "analysis_workflow": {
                    "step1": "파일 업로드",
                    "step2": "🤖 AI가 난이도 분석 중...",
                    "step3": "검토 페이지에서 확인",
                    "step4": "승인 후 저장"
                }
            },
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"AI 분석 상태 조회 실패: {e}")
        return {
            "success": True,
            "data": {
                "ai_available": False,
                "error": str(e),
                "fallback_mode": True,
                "message": "AI 분석 기능을 사용할 수 없습니다. 수동 모드로 진행해주세요."
            }
        }


@router.post("/analyze-question")
async def analyze_question_manually(
    request: dict,
    current_user: User = Depends(get_current_user)
):
    """수동 문제 AI 분석 요청"""
    check_professor_permission(current_user)
    
    try:
        from app.services.ai_difficulty_analyzer import difficulty_analyzer
        
        question_content = request.get("content", "")
        question_number = request.get("question_number", 1)
        
        if not question_content.strip():
            return {
                "success": False,
                "error": "문제 내용이 없습니다"
            }
        
        # 사용자 부서에 맞는 학과 매핑
        department_mapping = {
            "물리치료학과": "물리치료",
            "작업치료학과": "작업치료"
        }
        
        user_dept = department_mapping.get(current_user.department, "물리치료")
        
        # AI 분석 실행
        analysis_result = difficulty_analyzer.analyze_question_auto(
            question_content, question_number, user_dept
        )
        
        return {
            "success": True,
            "data": {
                "analysis_result": analysis_result,
                "analyzed_at": datetime.now().isoformat(),
                "department": user_dept,
                "ui_status": {
                    "analysis_complete": True,
                    "status_message": "🤖 AI 분석 완료",
                    "confidence_level": analysis_result.get("confidence", "medium"),
                    "recommended_action": "검토 후 승인해주세요"
                }
            }
        }
        
    except Exception as e:
        logger.error(f"수동 AI 분석 실패: {e}")
        return {
            "success": False,
            "error": str(e),
            "ui_status": {
                "analysis_complete": False,
                "status_message": "❌ AI 분석 실패",
                "fallback_message": "수동으로 난이도를 설정해주세요"
            }
        }


@router.get("/learning-patterns")
async def get_ai_learning_patterns(
    current_user: User = Depends(get_current_user)
):
    """AI 학습된 패턴 정보 조회"""
    check_professor_permission(current_user)
    
    try:
        from app.services.ai_difficulty_analyzer import difficulty_analyzer
        
        # 사용자 부서에 맞는 학과 매핑
        department_mapping = {
            "물리치료학과": "물리치료",
            "작업치료학과": "작업치료"
        }
        
        user_dept = department_mapping.get(current_user.department, "물리치료")
        
        # 학습 패턴 정보 가져오기
        patterns = difficulty_analyzer.learning_patterns.get(user_dept, {})
        question_map = patterns.get("question_difficulty_map", {})
        difficulty_dist = patterns.get("difficulty_distribution", {})
        
        # 1-22번 문제별 예상 난이도 생성
        question_predictions = {}
        for i in range(1, 23):
            predicted_difficulty = difficulty_analyzer.predict_difficulty_by_position(i, user_dept)
            question_predictions[str(i)] = predicted_difficulty
        
        return {
            "success": True,
            "data": {
                "department": user_dept,
                "evaluator_count": 6,
                "total_analyzed_questions": sum(difficulty_dist.values()) if difficulty_dist else 0,
                "difficulty_distribution": difficulty_dist,
                "question_predictions": question_predictions,
                "analysis_summary": {
                    "most_common_difficulty": max(difficulty_dist.items(), key=lambda x: x[1])[0] if difficulty_dist else "중",
                    "coverage": f"{len(question_map)}/22 문제 패턴 학습 완료",
                    "confidence": "high" if len(question_map) >= 20 else "medium"
                },
                "ui_display": {
                    "chart_data": [
                        {"difficulty": k, "count": v, "percentage": round(v/sum(difficulty_dist.values())*100, 1)}
                        for k, v in difficulty_dist.items()
                    ] if difficulty_dist else [],
                    "pattern_grid": [
                        {"question": f"{i}번", "predicted_difficulty": question_predictions.get(str(i), "중")}
                        for i in range(1, 23)
                    ]
                }
            }
        }
        
    except Exception as e:
        logger.error(f"학습 패턴 조회 실패: {e}")
        return {
            "success": False,
            "error": str(e)
        } 