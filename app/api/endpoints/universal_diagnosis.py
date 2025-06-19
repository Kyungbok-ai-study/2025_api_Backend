"""
전체 학과 지원 통합 진단테스트 API 엔드포인트
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Dict, Any, Optional
import logging
from datetime import datetime

from app.db.database import get_db
from app.auth.dependencies import get_current_user
from app.models.user import User
from app.services.universal_diagnosis_service import get_universal_diagnosis_service
from app.services.diagnosis_progress_service import DiagnosisProgressService

router = APIRouter(prefix="/universal-diagnosis", tags=["universal-diagnosis"])
logger = logging.getLogger(__name__)

@router.get("/supported-departments")
async def get_supported_departments(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """지원되는 전체 학과 목록 조회"""
    try:
        service = get_universal_diagnosis_service(db)
        departments = service.get_supported_departments()
        
        return {
            "success": True,
            "message": "지원 학과 목록 조회 성공",
            "data": {
                "departments": departments,
                "total_categories": len(departments),
                "total_departments": sum(len(depts) for depts in departments.values())
            }
        }
    except Exception as e:
        logger.error(f"지원 학과 목록 조회 실패: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"지원 학과 목록 조회 실패: {str(e)}"
        )

@router.get("/department/{department_name}/test-info")
async def get_department_test_info(
    department_name: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """특정 학과의 진단테스트 정보 조회 (본인 학과만 접근 가능)"""
    try:
        # 사용자 학과 검증
        if current_user.department != department_name:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"본인의 학과({current_user.department})만 진단테스트를 받을 수 있습니다."
            )
        
        service = get_universal_diagnosis_service(db)
        
        # 테스트 데이터 로드
        test_data = service.create_universal_test_data(department_name)
        
        if not test_data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"해당 학과의 진단테스트 데이터를 찾을 수 없습니다: {department_name}"
            )
        
        return {
            "success": True,
            "message": f"{department_name} 진단테스트 정보 조회 성공",
            "data": {
                "department": department_name,
                "test_info": test_data["test_info"],
                "scoring_criteria": test_data["scoring_criteria"],
                "sample_questions": len(test_data["questions"]),
                "is_available": True
            }
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"진단테스트 정보 조회 실패: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"진단테스트 정보 조회 실패: {str(e)}"
        )

@router.post("/department/{department_name}/start-test")
async def start_department_diagnosis_test(
    department_name: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """학과별 진단테스트 시작 (본인 학과만 접근 가능)"""
    try:
        # 사용자 학과 검증
        if current_user.department != department_name:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"본인의 학과({current_user.department})만 진단테스트를 받을 수 있습니다."
            )
        
        service = get_universal_diagnosis_service(db)
        
        # 테스트 데이터 로드
        test_data = service.create_universal_test_data(department_name)
        
        if not test_data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"해당 학과의 진단테스트 데이터를 찾을 수 없습니다: {department_name}"
            )
        
        # 세션 ID 생성 (간단하게 타임스탬프 사용)
        import time
        session_id = f"{current_user.id}_{department_name}_{int(time.time())}"
        
        return {
            "success": True,
            "message": f"{department_name} 진단테스트 시작",
            "data": {
                "test_session_id": session_id,
                "department": department_name,
                "test_info": test_data["test_info"],
                "questions": test_data["questions"],
                "scoring_criteria": test_data["scoring_criteria"],
                "start_time": datetime.now().isoformat()
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"진단테스트 시작 실패: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"진단테스트 시작 실패: {str(e)}"
        )

@router.get("/department/{department_name}/questions/{session_id}")
async def get_department_test_questions(
    department_name: str,
    session_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """학과별 진단테스트 문제 조회"""
    try:
        progress_service = DiagnosisProgressService(db)
        
        # 세션 검증
        session_data = await progress_service.get_session_questions(
            session_id=session_id,
            user_id=current_user.id
        )
        
        if not session_data["success"]:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=session_data["message"]
            )
        
        return {
            "success": True,
            "message": "진단테스트 문제 조회 성공",
            "data": session_data["data"]
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"진단테스트 문제 조회 실패: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"진단테스트 문제 조회 실패: {str(e)}"
        )

@router.post("/department/{department_name}/submit-test")
async def submit_department_test(
    department_name: str,
    answer_data: Dict[str, Any],
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """학과별 진단테스트 전체 답안 제출 (본인 학과만 접근 가능)"""
    try:
        # 사용자 학과 검증
        if current_user.department != department_name:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"본인의 학과({current_user.department})만 진단테스트를 받을 수 있습니다."
            )
        
        service = get_universal_diagnosis_service(db)
        
        # 테스트 데이터 로드 (채점을 위해)
        test_data = service.create_universal_test_data(department_name)
        
        if not test_data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"해당 학과의 진단테스트 데이터를 찾을 수 없습니다: {department_name}"
            )
        
        # 제출된 답안 처리
        submitted_answers = answer_data.get("answers", {})
        test_session_id = answer_data.get("test_session_id")
        
        # 채점 수행
        result = service.grade_test(test_data, submitted_answers, current_user.id, department_name)
        
        return {
            "success": True,
            "message": f"{department_name} 진단테스트 제출 완료",
            "data": {
                "result_id": result["result_id"],
                "total_score": result["total_score"],
                "max_score": result["max_score"],
                "grade": result["grade"],
                "correct_answers": result["correct_answers"],
                "wrong_answers": result["wrong_answers"],
                "completion_time": datetime.now().isoformat()
            }
                 }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"진단테스트 제출 실패: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"진단테스트 제출 실패: {str(e)}"
        )

@router.get("/result/{result_id}")
async def get_test_result(
    result_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """테스트 결과 조회"""
    try:
        # 결과 ID에서 사용자 ID와 학과명 추출
        parts = result_id.split('_')
        if len(parts) < 3:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="잘못된 결과 ID 형식입니다."
            )
        
        user_id = int(parts[0])
        department_name = parts[1]
        
        # 본인의 결과만 조회 가능
        if current_user.id != user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="본인의 테스트 결과만 조회할 수 있습니다."
            )
        
        # 본인 학과의 결과만 조회 가능
        if current_user.department != department_name:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="본인 학과의 테스트 결과만 조회할 수 있습니다."
            )
        
        # 실제로는 캐시나 데이터베이스에서 결과를 조회해야 하지만,
        # 여기서는 간단하게 mock 데이터를 반환
        mock_result = {
            "result_id": result_id,
            "department_name": department_name,
            "total_score": 85.5,
            "max_score": 100,
            "percentage": 85.5,
            "grade": "상급",
            "correct_answers": 25,
            "wrong_answers": 5,
            "total_questions": 30,
            "percentile": 75,
            "completed_at": datetime.now().isoformat(),
            "strengths": [
                "기본 개념 이해도가 우수합니다.",
                "응용 문제 해결 능력이 뛰어납니다."
            ],
            "weaknesses": [
                "심화 이론 부분에서 추가 학습이 필요합니다.",
                "실습 관련 문제에서 보완이 필요합니다."
            ],
            "question_results": [
                {
                    "question_number": 1,
                    "is_correct": True,
                    "user_answer": "1",
                    "correct_answer": "1",
                    "difficulty": "쉬움"
                }
                # ... 더 많은 문제 결과
            ]
        }
        
        return {
            "success": True,
            "message": "테스트 결과 조회 성공",
            "data": mock_result
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"테스트 결과 조회 실패: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"테스트 결과 조회 실패: {str(e)}"
        )
        
        if not result["success"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=result["message"]
            )
        
        return {
            "success": True,
            "message": "답안 제출 성공",
            "data": result["data"]
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"답안 제출 실패: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"답안 제출 실패: {str(e)}"
        )

@router.post("/department/{department_name}/complete-test")
async def complete_department_test(
    department_name: str,
    completion_data: Dict[str, Any],
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """학과별 진단테스트 완료"""
    try:
        progress_service = DiagnosisProgressService(db)
        
        # 테스트 완료 처리
        result = await progress_service.complete_diagnosis_session(
            session_id=completion_data.get("session_id"),
            user_id=current_user.id
        )
        
        if not result["success"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=result["message"]
            )
        
        return {
            "success": True,
            "message": f"{department_name} 진단테스트 완료",
            "data": result["data"]
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"진단테스트 완료 실패: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"진단테스트 완료 실패: {str(e)}"
        )

@router.get("/department/{department_name}/my-results")
async def get_my_department_results(
    department_name: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """내 학과별 진단테스트 결과 조회"""
    try:
        progress_service = DiagnosisProgressService(db)
        
        # 사용자의 해당 학과 진단 결과 조회
        results = await progress_service.get_user_diagnosis_history(
            user_id=current_user.id,
            department=department_name
        )
        
        return {
            "success": True,
            "message": f"{department_name} 진단 결과 조회 성공",
            "data": {
                "department": department_name,
                "user_name": current_user.name,
                "results": results
            }
        }
        
    except Exception as e:
        logger.error(f"진단 결과 조회 실패: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"진단 결과 조회 실패: {str(e)}"
        )

@router.get("/department/{department_name}/comprehensive-analysis")
async def get_comprehensive_analysis(
    department_name: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """학과별 종합 분석 조회"""
    try:
        progress_service = DiagnosisProgressService(db)
        
        # 종합 분석 조회
        analysis = await progress_service.get_comprehensive_analysis(
            user_id=current_user.id,
            department=department_name
        )
        
        if not analysis["success"]:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=analysis["message"]
            )
        
        return {
            "success": True,
            "message": f"{department_name} 종합 분석 조회 성공",
            "data": analysis["data"]
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"종합 분석 조회 실패: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"종합 분석 조회 실패: {str(e)}"
        ) 