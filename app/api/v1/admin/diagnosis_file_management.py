"""
진단테스트 파일 관리 API
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Dict, Any

from app.core.database import get_db
from app.core.security import get_current_admin_user
from app.models.user import User
from app.models.enums import DiagnosisSubject
from app.services.diagnosis_test_loader import diagnosis_test_loader
from app.services.department_diagnosis_service import DepartmentDiagnosisService

router = APIRouter(prefix="/admin/diagnosis-files", tags=["admin-diagnosis-files"])


@router.get("/validation-report")
async def get_validation_report(
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_admin_user)
) -> Dict[str, Any]:
    """진단테스트 파일 유효성 검사 보고서"""
    try:
        service = DepartmentDiagnosisService(db)
        return await service.get_test_validation_report()
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"유효성 검사 실패: {str(e)}"
        )


@router.get("/available-subjects")
async def get_available_subjects(
    current_admin: User = Depends(get_current_admin_user)
) -> List[Dict[str, str]]:
    """사용 가능한 진단 과목 목록"""
    try:
        available_subjects = diagnosis_test_loader.list_available_subjects()
        return [
            {
                "value": subject.value,
                "name": subject.value,
                "file_path": str(diagnosis_test_loader.get_test_file_path(subject))
            }
            for subject in available_subjects
        ]
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"과목 목록 조회 실패: {str(e)}"
        )


@router.get("/test-info/{subject}")
async def get_test_info(
    subject: DiagnosisSubject,
    current_admin: User = Depends(get_current_admin_user)
) -> Dict[str, Any]:
    """특정 과목의 테스트 정보"""
    try:
        test_info = diagnosis_test_loader.get_test_info(subject)
        scoring_criteria = diagnosis_test_loader.get_scoring_criteria(subject)
        statistics = diagnosis_test_loader.get_statistics(subject)
        
        return {
            "subject": subject.value,
            "test_info": test_info,
            "scoring_criteria": scoring_criteria,
            "statistics": statistics,
            "file_path": str(diagnosis_test_loader.get_test_file_path(subject))
        }
    except FileNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"과목 '{subject.value}'의 테스트 파일을 찾을 수 없습니다."
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"테스트 정보 조회 실패: {str(e)}"
        )


@router.get("/questions/{subject}")
async def get_questions(
    subject: DiagnosisSubject,
    limit: int = None,
    current_admin: User = Depends(get_current_admin_user)
) -> List[Dict[str, Any]]:
    """특정 과목의 문제 목록"""
    try:
        questions = diagnosis_test_loader.get_questions(subject, limit)
        return questions
    except FileNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"과목 '{subject.value}'의 테스트 파일을 찾을 수 없습니다."
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"문제 목록 조회 실패: {str(e)}"
        )


@router.post("/reload-cache")
async def reload_cache(
    current_admin: User = Depends(get_current_admin_user)
) -> Dict[str, str]:
    """진단테스트 파일 캐시 재로드"""
    try:
        diagnosis_test_loader.clear_cache()
        return {"message": "캐시가 성공적으로 초기화되었습니다."}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"캐시 초기화 실패: {str(e)}"
        )


@router.post("/reload-subject/{subject}")
async def reload_subject_data(
    subject: DiagnosisSubject,
    current_admin: User = Depends(get_current_admin_user)
) -> Dict[str, Any]:
    """특정 과목의 테스트 데이터 재로드"""
    try:
        data = diagnosis_test_loader.reload_test_data(subject)
        return {
            "message": f"과목 '{subject.value}' 데이터가 성공적으로 재로드되었습니다.",
            "question_count": len(data.get("questions", [])),
            "test_title": data.get("test_info", {}).get("title", "")
        }
    except FileNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"과목 '{subject.value}'의 테스트 파일을 찾을 수 없습니다."
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"데이터 재로드 실패: {str(e)}"
        )


@router.post("/sync-to-database/{subject}")
async def sync_subject_to_database(
    subject: DiagnosisSubject,
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_admin_user)
) -> Dict[str, Any]:
    """JSON 파일의 데이터를 데이터베이스로 동기화"""
    try:
        service = DepartmentDiagnosisService(db)
        
        # 현재 사용자의 학과를 기본값으로 사용 (관리자는 모든 학과 접근 가능)
        diagnosis_test = await service.create_diagnosis_test_from_file(
            subject, 
            current_admin.profile_info.get("department", "COMPUTER_SCIENCE")
        )
        
        return {
            "message": f"과목 '{subject.value}' 데이터가 데이터베이스에 성공적으로 동기화되었습니다.",
            "test_id": diagnosis_test.id,
            "test_title": diagnosis_test.title,
            "question_count": len(diagnosis_test.questions)
        }
    except FileNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"과목 '{subject.value}'의 테스트 파일을 찾을 수 없습니다."
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"데이터베이스 동기화 실패: {str(e)}"
        )


@router.get("/file-structure")
async def get_file_structure(
    current_admin: User = Depends(get_current_admin_user)
) -> Dict[str, Any]:
    """진단테스트 파일 구조 정보"""
    try:
        from app.models.enums import DEPARTMENT_CATEGORIES, DEPARTMENT_TEST_FILE_MAPPING
        
        return {
            "categories": DEPARTMENT_CATEGORIES,
            "file_mapping": {
                subject.value: path 
                for subject, path in DEPARTMENT_TEST_FILE_MAPPING.items()
            },
            "data_directory": str(diagnosis_test_loader.data_directory)
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"파일 구조 정보 조회 실패: {str(e)}"
        ) 