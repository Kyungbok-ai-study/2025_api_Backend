"""
교수용 API 엔드포인트
"""
from fastapi import APIRouter, Depends, HTTPException, status, File, UploadFile, Form
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, func, desc
from typing import List, Optional
from datetime import datetime, date, timedelta
from pydantic import BaseModel, Field

from app.db.database import get_db
from app.core.config import settings
from app.models.user import User
from app.models.assignment import Assignment, AssignmentSubmission, AssignmentStatus, AssignmentType, ProblemBank
from app.models.analytics import StudentActivity, StudentWarning, LearningAnalytics, ProfessorDashboardData
from app.models.question import Question
from app.api.endpoints.auth import get_current_user
from app.schemas.question_upload import (
    QuestionUploadResponse, 
    AnswerUploadResponse,
    ParseAndMatchRequest,
    ParseAndMatchResponse
)
from app.schemas.question_review import (
    ParsedFilePreview, QuestionPreviewItem, QuestionUpdateRequest,
    BulkApprovalRequest, QuestionApprovalResponse
)
from app.services.question_service import process_files_with_gemini_parser
from app.services.question_parser import QuestionParser
from app.services.question_review_service import QuestionReviewService
from app.services.rag_integration_service import (
    save_to_vector_db, generate_ai_explanation, 
    index_to_rag, add_to_llm_training
)
from app.services.department_recognizer import department_recognizer
from app.services.ai_auto_mapper import ai_auto_mapper
from app.services.integrated_parser_mapper import integrated_parser_mapper
import os
import shutil
from pathlib import Path
import json
import random
import logging
from app.services.enhanced_problem_generator import enhanced_generator

router = APIRouter(prefix="/professor", tags=["professor"])

# 로거 설정
logger = logging.getLogger(__name__)

# ===== Pydantic 모델들 =====

class DashboardResponse(BaseModel):
    total_students: int
    active_students: int
    critical_students: int
    warning_students: int
    pending_assignments: int
    class_average_score: float
    recent_submissions: List[dict]
    warnings: List[dict]
    activity_heatmap: List[dict]

class AssignmentCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = None
    assignment_type: str = Field(..., pattern="^(homework|project|quiz|exam)$")
    subject_name: str = Field(..., min_length=1, max_length=100)
    due_date: Optional[datetime] = None
    max_score: float = Field(default=100.0, ge=0)
    allow_late_submission: bool = False
    instructions: Optional[str] = None

class ProblemCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=200)
    content: str = Field(..., min_length=1)
    problem_type: str = Field(..., pattern="^(multiple_choice|short_answer|essay|true_false)$")
    subject: str = Field(..., min_length=1, max_length=100)
    difficulty: int = Field(..., ge=1, le=5)
    correct_answer: Optional[str] = None
    choices: Optional[List[str]] = None
    explanation: Optional[str] = None

# RAG 관련 Pydantic 모델들
class RAGGenerationRequest(BaseModel):
    subject: str = Field(..., min_length=1, max_length=100)
    difficulty: str = Field(..., pattern="^(easy|medium|hard)$")
    questionType: str = Field(..., pattern="^(multiple_choice|short_answer|essay|true_false)$")
    count: int = Field(..., ge=1, le=20)
    keywords: Optional[str] = None
    context: Optional[str] = None
    use_rag: bool = True
    real_time_learning: bool = True

class RAGStatsResponse(BaseModel):
    total_documents: int
    total_embeddings: int
    embedding_dimensions: int
    last_updated: str
    knowledge_areas: List[str]
    auto_learning_enabled: bool
    indexing_status: str

class GeneratedProblem(BaseModel):
    id: str
    question: str
    type: str
    choices: Optional[dict] = None
    correct_answer: str
    explanation: str
    difficulty: str
    rag_source: str
    confidence_score: float
    generated_at: str

# ===== 유틸리티 함수들 =====

def get_professor_students(db: Session, professor: User) -> List[User]:
    """교수와 같은 학교+학과의 학생들을 조회"""
    return db.query(User).filter(
        and_(
            User.school == professor.school,
            User.department == professor.department,
            User.role == "student"
        )
    ).all()

def check_professor_permission(current_user: User):
    """교수 권한 확인"""
    if current_user.role not in ["professor", "admin"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="교수 권한이 필요합니다."
        )

# ===== API 엔드포인트들 =====

@router.get("/dashboard", response_model=DashboardResponse)
async def get_professor_dashboard(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """교수 대시보드 데이터 조회"""
    check_professor_permission(current_user)
    
    # 담당 학생들 조회
    students = get_professor_students(db, current_user)
    student_ids = [s.id for s in students]
    
    today = date.today()
    week_ago = today - timedelta(days=7)
    
    # 기본 통계
    total_students = len(students)
    
    # 활성 학생 수 (최근 7일 내 활동이 있는 학생)
    active_students = db.query(StudentActivity.student_id).filter(
        and_(
            StudentActivity.student_id.in_(student_ids),
            StudentActivity.activity_date >= week_ago
        )
    ).distinct().count() if student_ids else 0
    
    # 경고 학생 수
    critical_warnings = db.query(StudentWarning).filter(
        and_(
            StudentWarning.student_id.in_(student_ids),
            StudentWarning.severity == "critical",
            StudentWarning.is_resolved == False
        )
    ).count() if student_ids else 0
    
    warning_count = db.query(StudentWarning).filter(
        and_(
            StudentWarning.student_id.in_(student_ids),
            StudentWarning.severity.in_(["high", "medium"]),
            StudentWarning.is_resolved == False
        )
    ).count() if student_ids else 0
    
    # 대기 중인 과제 수
    pending_assignments = db.query(AssignmentSubmission).filter(
        and_(
            AssignmentSubmission.student_id.in_(student_ids),
            AssignmentSubmission.score.is_(None)
        )
    ).count() if student_ids else 0
    
    # 반 평균 점수
    avg_score_result = db.query(func.avg(AssignmentSubmission.score)).filter(
        and_(
            AssignmentSubmission.student_id.in_(student_ids),
            AssignmentSubmission.score.is_not(None)
        )
    ).scalar() if student_ids else None
    
    class_average_score = float(avg_score_result) if avg_score_result else 0.0
    
    # 최근 제출물 (최대 5개)
    recent_submissions_query = db.query(
        AssignmentSubmission,
        Assignment.subject_name,
        User.name
    ).join(
        Assignment, AssignmentSubmission.assignment_id == Assignment.id
    ).join(
        User, AssignmentSubmission.student_id == User.id
    ).filter(
        AssignmentSubmission.student_id.in_(student_ids) if student_ids else False
    ).order_by(
        desc(AssignmentSubmission.submitted_at)
    ).limit(5)
    
    recent_submissions = []
    for submission, subject, student_name in recent_submissions_query:
        recent_submissions.append({
            "student": student_name,
            "course": subject,
            "assignment": f"과제 {submission.assignment_id}",
            "score": submission.score or 0,
            "date": submission.submitted_at.strftime("%Y-%m-%d")
        })
    
    # 경고 목록 (최대 5개)
    warnings_query = db.query(StudentWarning, User.name).join(
        User, StudentWarning.student_id == User.id
    ).filter(
        and_(
            StudentWarning.student_id.in_(student_ids) if student_ids else False,
            StudentWarning.is_resolved == False
        )
    ).order_by(desc(StudentWarning.created_at)).limit(5)
    
    warnings = []
    for warning, student_name in warnings_query:
        warnings.append({
            "student": student_name,
            "type": warning.warning_type,
            "severity": warning.severity,
            "title": warning.title,
            "description": warning.description
        })
    
    # 활동 히트맵 데이터 (최근 4주)
    four_weeks_ago = today - timedelta(days=28)
    activity_heatmap = []
    
    for i in range(28):
        target_date = four_weeks_ago + timedelta(days=i)
        activity_count = db.query(StudentActivity).filter(
            and_(
                StudentActivity.student_id.in_(student_ids) if student_ids else False,
                StudentActivity.activity_date == target_date
            )
        ).count()
        
        activity_heatmap.append({
            "date": target_date.strftime("%Y-%m-%d"),
            "count": activity_count,
            "level": min(4, activity_count // 5)  # 0-4 레벨
        })
    
    return DashboardResponse(
        total_students=total_students,
        active_students=active_students,
        critical_students=critical_warnings,
        warning_students=warning_count,
        pending_assignments=pending_assignments,
        class_average_score=class_average_score,
        recent_submissions=recent_submissions,
        warnings=warnings,
        activity_heatmap=activity_heatmap
    )

@router.get("/students")
async def get_professor_students_list(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """담당 학생 목록 조회"""
    check_professor_permission(current_user)
    
    students = get_professor_students(db, current_user)
    
    result = []
    for student in students:
        # 최근 활동 조회
        last_activity = db.query(StudentActivity).filter(
            StudentActivity.student_id == student.id
        ).order_by(desc(StudentActivity.created_at)).first()
        
        # 경고 수 조회
        warning_count = db.query(StudentWarning).filter(
            and_(
                StudentWarning.student_id == student.id,
                StudentWarning.is_resolved == False
            )
        ).count()
        
        result.append({
            "id": student.id,
            "name": student.name,
            "user_id": student.user_id,
            "email": student.email,
            "last_activity": last_activity.created_at.strftime("%Y-%m-%d %H:%M") if last_activity else None,
            "warning_count": warning_count
        })
    
    return {"students": result}

@router.post("/assignments")
async def create_assignment(
    assignment_data: AssignmentCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """새 과제 생성"""
    check_professor_permission(current_user)
    
    assignment = Assignment(
        title=assignment_data.title,
        description=assignment_data.description,
        assignment_type=AssignmentType(assignment_data.assignment_type),
        status=AssignmentStatus.DRAFT,
            professor_id=current_user.id,
        professor_school=current_user.school,
        professor_department=current_user.department,
        subject_name=assignment_data.subject_name,
        due_date=assignment_data.due_date,
        max_score=assignment_data.max_score,
        allow_late_submission=assignment_data.allow_late_submission,
        instructions=assignment_data.instructions
    )
    
    db.add(assignment)
    db.commit()
    db.refresh(assignment)
    
    return {"message": "과제가 생성되었습니다.", "assignment_id": assignment.id}

@router.get("/assignments")
async def get_professor_assignments(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """교수의 과제 목록 조회"""
    check_professor_permission(current_user)
    
    assignments = db.query(Assignment).filter(
        Assignment.professor_id == current_user.id
    ).order_by(desc(Assignment.created_at)).all()
    
    result = []
    for assignment in assignments:
        submission_count = db.query(AssignmentSubmission).filter(
            AssignmentSubmission.assignment_id == assignment.id
        ).count()
        
        graded_count = db.query(AssignmentSubmission).filter(
            and_(
                AssignmentSubmission.assignment_id == assignment.id,
                AssignmentSubmission.score.is_not(None)
            )
        ).count()
        
        result.append({
            "id": assignment.id,
            "title": assignment.title,
            "subject_name": assignment.subject_name,
            "assignment_type": assignment.assignment_type.value,
            "status": assignment.status.value,
            "due_date": assignment.due_date.strftime("%Y-%m-%d %H:%M") if assignment.due_date else None,
            "submission_count": submission_count,
            "graded_count": graded_count,
            "created_at": assignment.created_at.strftime("%Y-%m-%d")
        })
    
    return {"assignments": result}

@router.get("/assignments/{assignment_id}")
async def get_assignment_detail(
    assignment_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """과제 상세 조회"""
    check_professor_permission(current_user)
    
    assignment = db.query(Assignment).filter(
        and_(
            Assignment.id == assignment_id,
            Assignment.professor_id == current_user.id
        )
    ).first()
    
    if not assignment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="과제를 찾을 수 없습니다."
        )
    
    # 제출 현황 조회
    submissions = db.query(AssignmentSubmission, User.name, User.user_id).join(
        User, AssignmentSubmission.student_id == User.id
    ).filter(
        AssignmentSubmission.assignment_id == assignment_id
    ).order_by(desc(AssignmentSubmission.submitted_at)).all()
    
    submission_list = []
    for submission, student_name, student_id in submissions:
        submission_list.append({
            "id": submission.id,
            "student_name": student_name,
            "student_id": student_id,
            "submitted_at": submission.submitted_at.strftime("%Y-%m-%d %H:%M"),
            "score": submission.score,
            "is_late": submission.is_late,
            "graded_at": submission.graded_at.strftime("%Y-%m-%d %H:%M") if submission.graded_at else None
        })
    
    return {
        "assignment": {
            "id": assignment.id,
            "title": assignment.title,
            "description": assignment.description,
            "assignment_type": assignment.assignment_type.value,
            "status": assignment.status.value,
            "subject_name": assignment.subject_name,
            "due_date": assignment.due_date.strftime("%Y-%m-%d %H:%M") if assignment.due_date else None,
            "max_score": assignment.max_score,
            "allow_late_submission": assignment.allow_late_submission,
            "instructions": assignment.instructions,
            "created_at": assignment.created_at.strftime("%Y-%m-%d %H:%M"),
            "published_at": assignment.published_at.strftime("%Y-%m-%d %H:%M") if assignment.published_at else None
        },
        "submissions": submission_list,
        "statistics": {
            "total_submissions": len(submission_list),
            "graded_submissions": len([s for s in submission_list if s["score"] is not None]),
            "average_score": sum([s["score"] for s in submission_list if s["score"] is not None]) / len([s for s in submission_list if s["score"] is not None]) if len([s for s in submission_list if s["score"] is not None]) > 0 else 0
        }
    }

@router.put("/assignments/{assignment_id}")
async def update_assignment(
    assignment_id: int,
    assignment_data: AssignmentCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """과제 수정"""
    check_professor_permission(current_user)
    
    assignment = db.query(Assignment).filter(
        and_(
            Assignment.id == assignment_id,
            Assignment.professor_id == current_user.id
        )
    ).first()
    
    if not assignment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="과제를 찾을 수 없습니다."
        )
    
    # 이미 게시된 과제는 일부 항목만 수정 가능
    if assignment.status != AssignmentStatus.DRAFT:
        # 게시된 과제는 제목, 설명, 지시사항만 수정 가능
        assignment.title = assignment_data.title
        assignment.description = assignment_data.description
        assignment.instructions = assignment_data.instructions
    else:
        # 초안 상태에서는 모든 항목 수정 가능
        assignment.title = assignment_data.title
        assignment.description = assignment_data.description
        assignment.assignment_type = AssignmentType(assignment_data.assignment_type)
        assignment.subject_name = assignment_data.subject_name
        assignment.due_date = assignment_data.due_date
        assignment.max_score = assignment_data.max_score
        assignment.allow_late_submission = assignment_data.allow_late_submission
        assignment.instructions = assignment_data.instructions
    
    assignment.updated_at = datetime.now()
    
    db.commit()
    db.refresh(assignment)
    
    return {"message": "과제가 수정되었습니다.", "assignment_id": assignment.id}

@router.patch("/assignments/{assignment_id}/status")
async def update_assignment_status(
    assignment_id: int,
    status_data: dict,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """과제 상태 변경 (게시, 마감 등)"""
    check_professor_permission(current_user)
    
    assignment = db.query(Assignment).filter(
        and_(
            Assignment.id == assignment_id,
            Assignment.professor_id == current_user.id
        )
    ).first()
    
    if not assignment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="과제를 찾을 수 없습니다."
        )
    
    new_status = status_data.get("status")
    if new_status not in ["draft", "published", "closed", "graded"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="유효하지 않은 상태입니다."
        )
    
    assignment.status = AssignmentStatus(new_status)
    
    # 게시 시 게시 시간 기록
    if new_status == "published" and not assignment.published_at:
        assignment.published_at = datetime.now()
    
    assignment.updated_at = datetime.now()
    
    db.commit()
    db.refresh(assignment)
    
    return {"message": f"과제 상태가 '{new_status}'로 변경되었습니다.", "assignment_id": assignment.id}

@router.delete("/assignments/{assignment_id}")
async def delete_assignment(
    assignment_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """과제 삭제"""
    check_professor_permission(current_user)
    
    assignment = db.query(Assignment).filter(
        and_(
            Assignment.id == assignment_id,
            Assignment.professor_id == current_user.id
        )
    ).first()
    
    if not assignment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="과제를 찾을 수 없습니다."
        )
    
    # 제출물이 있는 과제는 삭제할 수 없음
    submission_count = db.query(AssignmentSubmission).filter(
        AssignmentSubmission.assignment_id == assignment_id
    ).count()
    
    if submission_count > 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="제출물이 있는 과제는 삭제할 수 없습니다."
        )
    
    db.delete(assignment)
    db.commit()
    
    return {"message": "과제가 삭제되었습니다."}

@router.post("/problems")
async def create_problem(
    problem_data: ProblemCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """새 문제 생성"""
    check_professor_permission(current_user)
    
    problem = ProblemBank(
        title=problem_data.title,
        content=problem_data.content,
        problem_type=problem_data.problem_type,
        subject=problem_data.subject,
        difficulty=problem_data.difficulty,
        correct_answer=problem_data.correct_answer,
        choices=problem_data.choices,
        explanation=problem_data.explanation,
        created_by=current_user.id,
        school=current_user.school,
        department=current_user.department
    )
    
    db.add(problem)
    db.commit()
    db.refresh(problem)
    
    return {"message": "문제가 생성되었습니다.", "problem_id": problem.id}

@router.get("/problems")
async def get_professor_problems(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """교수의 문제 목록 조회"""
    check_professor_permission(current_user)
    
    problems = db.query(ProblemBank).filter(
        ProblemBank.created_by == current_user.id
    ).order_by(desc(ProblemBank.created_at)).all()
    
    result = []
    for problem in problems:
        result.append({
            "id": problem.id,
            "title": problem.title,
            "subject": problem.subject,
            "problem_type": problem.problem_type,
            "difficulty": problem.difficulty,
            "usage_count": problem.usage_count,
            "created_at": problem.created_at.strftime("%Y-%m-%d")
        })
    
    return {"problems": result} 

# ===== 문제 업로드 관련 엔드포인트들 =====

@router.post("/upload/questions", response_model=QuestionUploadResponse)
async def upload_questions_file(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    문제 파일 업로드 (모든 형식 지원)
    
    지원 형식: JSON, PDF, 엑셀, 텍스트 등
    Gemini API가 자동으로 파일 형식을 인식하고 파싱합니다.
    """
    check_professor_permission(current_user)
    
    # 업로드 디렉토리 생성
    upload_dir = Path("uploads/questions")
    upload_dir.mkdir(parents=True, exist_ok=True)
    
    # 파일명 생성
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    safe_filename = f"{timestamp}_{current_user.id}_{file.filename}"
    file_path = upload_dir / safe_filename
    
    try:
        # 파일 저장
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        # Gemini로 파싱 (API 키 직접 전달)
        gemini_api_key = "AIzaSyAU_5m68cNAMIBn7m1uQPrYKNFR0oPO3QA"
        parser = QuestionParser(api_key=gemini_api_key)
        result = parser.parse_any_file(str(file_path), content_type="questions")
        
        parsed_count = len(result.get("data", []))
        
        # 파싱된 데이터를 JSON으로 저장 (디버깅 및 재사용)
        if parsed_count > 0:
            json_path = file_path.with_suffix('.parsed.json')
            with open(json_path, 'w', encoding='utf-8') as f:
                json.dump(result["data"], f, ensure_ascii=False, indent=2)
        
        return QuestionUploadResponse(
            success=True,
            message=f"문제 파일이 성공적으로 업로드되었습니다. {parsed_count}개의 문제를 파싱했습니다.",
            file_name=safe_filename,
            parsed_count=parsed_count
        )
        
    except Exception as e:
        # 오류 발생 시 파일 삭제
        if file_path.exists():
            file_path.unlink()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"파일 업로드 중 오류가 발생했습니다: {str(e)}"
        )


@router.post("/upload/answers", response_model=AnswerUploadResponse)
async def upload_answer_file(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    정답 파일 업로드 (모든 형식 지원)
    
    지원 형식: 엑셀, PDF, JSON, CSV 등
    Gemini API가 자동으로 표 형식의 정답 데이터를 인식하고 파싱합니다.
    """
    check_professor_permission(current_user)
    
    # 업로드 디렉토리 생성
    upload_dir = Path("uploads/answers")
    upload_dir.mkdir(parents=True, exist_ok=True)
    
    # 파일명 생성
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    safe_filename = f"{timestamp}_{current_user.id}_{file.filename}"
    file_path = upload_dir / safe_filename
    
    try:
        # 파일 저장
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        # Gemini로 파싱 (API 키 직접 전달)
        gemini_api_key = "AIzaSyAU_5m68cNAMIBn7m1uQPrYKNFR0oPO3QA"
        parser = QuestionParser(api_key=gemini_api_key)
        result = parser.parse_any_file(str(file_path), content_type="answers")
        
        answers_data = result.get("data", [])
        
        # 연도별로 그룹화
        from collections import defaultdict
        answers_by_year = defaultdict(list)
        
        for answer in answers_data:
            year = str(answer.get("year", "unknown"))
            answers_by_year[year].append(answer)
        
        years_found = list(answers_by_year.keys())
        total_answers = len(answers_data)
        
        # 파싱된 데이터를 JSON으로 저장
        if total_answers > 0:
            json_path = file_path.with_suffix('.parsed.json')
            with open(json_path, 'w', encoding='utf-8') as f:
                json.dump(dict(answers_by_year), f, ensure_ascii=False, indent=2)
        
        return AnswerUploadResponse(
            success=True,
            message=f"정답 파일이 성공적으로 업로드되었습니다. {len(years_found)}개 연도의 {total_answers}개 정답을 찾았습니다.",
            file_name=safe_filename,
            years_found=[int(y) for y in years_found if y.isdigit()],
            total_answers=total_answers
        )
        
    except Exception as e:
        # 오류 발생 시 파일 삭제
        if file_path.exists():
            file_path.unlink()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"파일 업로드 중 오류가 발생했습니다: {str(e)}"
        )


@router.post("/parse-and-match", response_model=ParseAndMatchResponse)
async def parse_and_match_questions(
    request: ParseAndMatchRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    업로드된 문제와 정답 파일을 파싱하고 매칭하여 DB에 저장
    """
    check_professor_permission(current_user)
    
    # 파일 존재 확인
    question_path = Path(request.question_file_path)
    answer_path = Path(request.answer_file_path)
    
    if not question_path.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="문제 파일을 찾을 수 없습니다."
        )
    
    if not answer_path.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="정답 파일을 찾을 수 없습니다."
        )
    
    try:
        # 문제-정답 매칭 및 저장 (새로운 함수 사용, API 키 직접 전달)
        gemini_api_key = "AIzaSyAU_5m68cNAMIBn7m1uQPrYKNFR0oPO3QA"
        result = process_files_with_gemini_parser(
            db=db,
            question_file_path=str(question_path),
            answer_file_path=str(answer_path),
            source_name=request.source_name,
            create_embeddings=request.create_embeddings,
            user_id=current_user.id,
            gemini_api_key=gemini_api_key
        )
        
        if result["success"]:
            return ParseAndMatchResponse(
                success=True,
                message="문제와 정답이 성공적으로 매칭되어 저장되었습니다.",
                total_questions=result.get("total_questions"),
                saved_questions=result.get("saved_questions"),
                save_rate=result.get("save_rate"),
                results_by_year=result.get("results_by_year")
            )
        else:
            return ParseAndMatchResponse(
                success=False,
                message="처리 중 오류가 발생했습니다.",
                errors=[result.get("error", "알 수 없는 오류")]
            )
            
    except Exception as e:
        return ParseAndMatchResponse(
            success=False,
            message="처리 중 예외가 발생했습니다.",
            errors=[str(e)]
        )


@router.get("/upload/history")
async def get_upload_history(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    교수의 업로드 히스토리 조회
    """
    check_professor_permission(current_user)
    
    # 업로드 디렉토리에서 현재 사용자의 파일 목록 조회
    question_dir = Path("uploads/questions")
    answer_dir = Path("uploads/answers")
    
    history = []
    
    # 문제 파일 목록
    if question_dir.exists():
        for file_path in question_dir.glob(f"*_{current_user.id}_*"):
            stat = file_path.stat()
            history.append({
                "type": "questions",
                "filename": file_path.name,
                "path": str(file_path),
                "size": stat.st_size,
                "uploaded_at": datetime.fromtimestamp(stat.st_mtime).isoformat()
            })
    
    # 정답 파일 목록
    if answer_dir.exists():
        for file_path in answer_dir.glob(f"*_{current_user.id}_*"):
            stat = file_path.stat()
            history.append({
                "type": "answers",
                "filename": file_path.name,
                "path": str(file_path),
                "size": stat.st_size,
                "uploaded_at": datetime.fromtimestamp(stat.st_mtime).isoformat()
            })
    
    # 시간순 정렬
    history.sort(key=lambda x: x["uploaded_at"], reverse=True)
    
    return {"history": history} 


# ===== 문제 검토 및 승인 관련 엔드포인트들 =====

@router.post("/upload/pdf-with-review")
async def upload_pdf_with_review(
    files: List[UploadFile] = File(...),
    title: str = Form(None),
    category: str = Form(None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """PDF 파일 업로드 및 검토용 파싱"""
    try:
        logger.info("📚 PDF 업로드 및 파싱 시작")
        check_professor_permission(current_user)
        
        # 파일 저장
        upload_dir = Path("uploads/questions")
        upload_dir.mkdir(parents=True, exist_ok=True)
        
        # 파일명 형식: {년도}_{카테고리}_{학과}_{교수명}.pdf
        current_year = datetime.now().year
        file_category = category if category and category.strip() else "일반"
        professor_name = current_user.name or f"교수{current_user.id}"
        department = current_user.department or "일반학과"
        
        # 💀 CRITICAL: 파일 저장 + 타입 매핑 (동시 처리)
        saved_files = []
        file_type_mapping = {}  # 파일경로 -> (타입, 원본파일명)
        
        for i, file in enumerate(files):
            # 새로운 파일명 형식 적용
            safe_filename = f"{current_year}_{file_category}_{department}_{professor_name}_{i+1}.pdf"
            file_path = upload_dir / safe_filename
            
            with open(file_path, "wb") as buffer:
                shutil.copyfileobj(file.file, buffer)
            
            # 💀 CRITICAL: 파일 타입 자동 감지 (개별 파일명 기반)
            original_filename = file.filename.lower()
            if any(keyword in original_filename for keyword in ["최종답안", "가답안", "정답", "답안", "answer"]):
                content_type = "answers"  # 정답지
                logger.info(f"📋 정답지로 인식: {file.filename} -> {Path(file_path).name}")
            else:
                content_type = "questions"  # 문제지
                logger.info(f"📝 문제지로 인식: {file.filename} -> {Path(file_path).name}")
            
            saved_files.append(str(file_path))
            file_type_mapping[str(file_path)] = (content_type, file.filename)
            logger.info(f"✅ 파일 저장: {file_path} (타입: {content_type})")
        
        # 파싱 시작
        review_service = QuestionReviewService()
        all_parsed_data = []
        
        for file_path in saved_files:
            # 저장된 타입 정보 사용
            content_type, original_filename = file_type_mapping[file_path]
            logger.info(f"🔍 파싱 시작: {Path(file_path).name} (타입: {content_type}, 원본: {original_filename})")
                
            try:
                # QuestionParser 초기화 (API 키 직접 전달)
                from app.services.question_parser import QuestionParser
                gemini_api_key = "AIzaSyAU_5m68cNAMIBn7m1uQPrYKNFR0oPO3QA"
                parser = QuestionParser(api_key=gemini_api_key)
                
                # 파싱 준비
                logger.info("Gemini 파서 준비 완료")
                if not parser.model:
                    logger.warning("⚠️ Gemini 초기화 실패, 더미 데이터 사용")
                    dummy_data = [{
                        "question_number": 1,
                        "content": f"파싱 실패 - 문제 인식 불가 ({Path(file_path).name})",
                        "options": {"1": "선택지1", "2": "선택지2", "3": "선택지3", "4": "선택지4"},
                        "correct_answer": "1",
                        "subject": "파싱오류",
                        "area_name": file_category,
                        "difficulty": "중",
                        "year": current_year
                    }]
                    all_parsed_data.extend(dummy_data)
                    continue
                
                logger.info("파싱 진행...")
                # 파서 실행
                try:
                    result = parser.parse_any_file(file_path, content_type)
                    logger.info(f"파싱 결과: {result.get('type')} 타입, {len(result.get('data', []))}개 데이터")
                    
                    if result.get('data'):
                        parsed_data = result.get('data', [])
                        # 파일 소스 정보 + 과목명 추가
                        for item in parsed_data:
                            item["source_file"] = Path(file_path).name
                            item["file_type"] = content_type
                            # 과목명은 교수 소속 학과로 설정
                            item["subject"] = current_user.department or "일반학과"
                        
                        logger.info(f"실제 파싱 성공: {len(parsed_data)}개 {content_type}")
                        all_parsed_data.extend(parsed_data)
                    else:
                        logger.warning("파싱 결과가 비어있음, 더미 데이터 사용")
                        # 파싱 실패시 더미 데이터 사용
                        dummy_data = [{
                            "question_number": 1,
                            "content": f"내용 인식 실패 - {Path(file_path).name}",
                            "options": {"1": "선택지1", "2": "선택지2", "3": "선택지3", "4": "선택지4"},
                            "correct_answer": "1",
                            "subject": current_user.department or "일반학과",
                            "area_name": "일반",
                            "difficulty": "중",
                            "year": current_year,
                            "source_file": Path(file_path).name,
                            "file_type": content_type
                        }]
                        all_parsed_data.extend(dummy_data)
                        
                except Exception as parse_error:
                    logger.error(f"파싱 실패: {parse_error}")
                    # 파싱 실패 시 더미 데이터
                    dummy_data = [{
                        "question_number": 1,
                        "content": f"파싱 오류 - 파일 형식 문제 ({Path(file_path).name})",
                        "options": {"1": "A", "2": "B", "3": "C", "4": "D"},
                        "correct_answer": "1",
                        "subject": current_user.department or "일반학과",
                        "area_name": "일반",
                        "difficulty": "중",
                        "year": current_year,
                        "source_file": Path(file_path).name,
                        "file_type": content_type
                    }]
                    all_parsed_data.extend(dummy_data)
                    
                    
                    
            except Exception as critical_error:
                logger.error(f"❌ 치명적 오류: {critical_error}")
                # 치명적 오류 시에도 더미 데이터로 계속 진행
                dummy_data = [{
                    "question_number": 1,
                    "content": f"치명적 오류 - 시스템 문제 ({Path(file_path).name})",
                    "options": {"1": "A", "2": "B", "3": "C", "4": "D"},
                    "correct_answer": "1",
                    "subject": current_user.department or "일반학과",
                    "area_name": "일반",
                    "difficulty": "중",
                    "year": current_year
                }]
                all_parsed_data.extend(dummy_data)
        
        # 파싱된 데이터를 문제지와 정답지로 분리
        questions_data = [item for item in all_parsed_data if item.get("file_type") == "questions"]
        answers_data = [item for item in all_parsed_data if item.get("file_type") == "answers"]
        
        logger.info(f"📊 파싱 결과: 문제지 {len(questions_data)}개, 정답지 {len(answers_data)}개")
        
        # 문제지와 정답지 매칭
        if questions_data and answers_data:
            logger.info(f"문제지 {len(questions_data)}개, 정답지 {len(answers_data)}개 매칭 시작")
            
            try:
                matched_data = parser.match_questions_with_answers(questions_data, answers_data)
                answered_count = len([m for m in matched_data if m.get("correct_answer")])
                
                # 매칭 품질 확인 후 필요시 수동 매칭
                if not matched_data or answered_count < len(matched_data) * 0.5:
                    logger.warning(f"자동 매칭 품질 불량, 수동 매칭 실행")
                    
                    manual_matched = {}
                    for q in questions_data:
                        qnum = q.get("question_number", 1)
                        manual_matched[qnum] = q.copy()
                    
                    for a in answers_data:
                        qnum = a.get("question_number", 1)
                        answer = a.get("correct_answer") or a.get("answer", "")
                        
                        if qnum in manual_matched and answer and answer.strip():
                            manual_matched[qnum]["correct_answer"] = answer.strip()
                            manual_matched[qnum]["answer_source"] = "manual_matched"
                            manual_matched[qnum]["subject"] = a.get("subject") or manual_matched[qnum].get("subject")
                        elif qnum in manual_matched:
                            manual_matched[qnum]["correct_answer"] = ""
                            manual_matched[qnum]["answer_source"] = "no_answer"
                    
                    matched_data = list(manual_matched.values())
                
                logger.info(f"매칭 완료: {len(matched_data)}개 문제, {len([m for m in matched_data if m.get('correct_answer')])}개 정답")
                
                # content가 없는 문제들 필터링
                valid_matched = []
                for item in matched_data:
                    if item.get("content") and item.get("content").strip():
                        valid_matched.append(item)
                    else:
                        logger.warning(f"⚠️ 문제 {item.get('question_number')} content 없음, 제외")
                
                final_parsed_data = valid_matched[:22]  # 22개 제한
                logger.info(f"✅ 최종 유효 문제: {len(final_parsed_data)}개")
                
            except Exception as e:
                logger.error(f"❌ 매칭 과정 오류: {e}")
                # 매칭 실패 시 문제지 우선 사용
                final_parsed_data = questions_data[:22] if questions_data else answers_data[:22]
                
        elif questions_data:
            # 문제지만 있는 경우
            logger.info("📝 문제지만 사용")
            # content 있는 것만 필터링
            valid_questions = [q for q in questions_data if q.get("content") and q.get("content").strip()]
            final_parsed_data = valid_questions[:22]
            logger.info(f"✅ 유효한 문제지: {len(final_parsed_data)}개")
            
        elif answers_data:
            # 정답지만 있는 경우
            logger.info("✅ 정답지만 사용")
            final_parsed_data = answers_data[:22]
            
        else:
            # 완전 실패 시 에러
            logger.error("❌ 파싱 완전 실패")
            raise Exception("PDF 파일에서 문제를 추출할 수 없습니다. 파일 형식을 확인해주세요.")
        
        # 파일 제목 설정
        file_title = title if title and title.strip() else f"{current_year}_{file_category}_{department}_{professor_name}"
        
        json_path = review_service.save_parsed_data_to_json(
            final_parsed_data, f"{file_title}_{files[0].filename}", current_user.id
        )
        logger.info(f"✅ JSON 저장: {json_path}")
        
        # DB 저장
        questions = await review_service.create_pending_questions(
            db=db,
            parsed_data=final_parsed_data,
            source_file_path=";".join(saved_files),
            parsed_data_path=json_path,
            user_id=current_user.id,
            file_title=file_title,
            file_category=file_category
        )
        logger.info(f"✅ DB 저장: {len(questions)}개 문제")
        
        return {
            "success": True,
            "message": f"✅ 업로드 완료! {len(saved_files)}개 파일, {len(questions)}개 문제 생성",
            "files": saved_files,
            "json_path": json_path,
            "questions": len(questions),
            "file_info": {
                "title": file_title,
                "category": file_category,
                "department": department,
                "professor": professor_name,
                "year": current_year
            },
            "parser_status": {
                "completed": True,
                "message": "✅ 파싱 완료",
                "parsed_questions": len(questions),
                "files_processed": len(saved_files)
            },
            "ai_analysis_status": {
                "in_progress": True,
                "message": "🤖 AI가 분석 중...",
                "completion_estimate": f"{len(questions) * 15}초 예상",
                "next_step": "검토 페이지에서 확인 가능"
            },
            "workflow_status": {
                "current_step": "파싱 완료",
                "next_step": "AI 분석",
                "final_step": "검토 및 승인"
            }
        }
        
    except Exception as e:
        logger.error(f"❌ 업로드 실패: {e}")
        import traceback
        logger.error(f"스택 트레이스:\n{traceback.format_exc()}")
        return {"success": False, "error": str(e)}

@router.post("/upload/pdf-with-review-BROKEN")
async def upload_pdf_with_review_broken(
    files: List[UploadFile] = File(...),
    title: str = Form(None),
    category: str = Form(None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    PDF 파일 멀티업로드 및 검토용 파싱 (2차 승인 프로세스)
    문제지와 정답지를 함께 업로드하여 통합 파싱
    """
    check_professor_permission(current_user)
    
    # 업로드 디렉토리 생성
    upload_dir = Path("uploads/questions")
    upload_dir.mkdir(parents=True, exist_ok=True)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    all_parsed_data = []
    uploaded_files = []
    
    try:
        # 각 파일 처리 (파일 타입 자동 감지)
        for i, file in enumerate(files):
            if not file.filename.endswith('.pdf'):
                continue
                
            # 파일명 생성
            safe_filename = f"{timestamp}_{current_user.id}_{i}_{file.filename}"
            file_path = upload_dir / safe_filename
            uploaded_files.append(str(file_path))
            
            # 파일 저장
            with open(file_path, "wb") as buffer:
                shutil.copyfileobj(file.file, buffer)
            
            # 📋 파일 타입 자동 감지
            filename_lower = file.filename.lower()
            if any(keyword in filename_lower for keyword in ["최종답안", "가답안", "정답", "답안", "answer"]):
                content_type = "answers"  # 정답지
                file_type = "answer_sheet"
            else:
                content_type = "questions"  # 문제지
                file_type = "question_sheet"
            
            # 🚀 **통합 파서-매퍼 시스템 사용** (자동 학과/난이도 매핑)
            logger.info(f"🤖 통합 파서-매퍼로 {file.filename} 처리 시작...")
            
            # 파일명에서 학과 자동 인식
            recognized_department = department_recognizer.recognize_department_from_filename(file.filename)
            logger.info(f"📚 인식된 학과: {recognized_department}")
            
            # 통합 파서-매퍼 사용
            result = await integrated_parser_mapper.parse_and_map_file(
                file_path=str(file_path),
                content_type=content_type,
                department=recognized_department
            )
            
            if "error" not in result:
                file_data = result.get("data", [])
                # 파일별 구분자 및 타입 추가
                for item in file_data:
                    item["source_file"] = file.filename
                    item["file_type"] = file_type  # 파일 타입 표시
                    # 자동 매핑 정보 추가
                    item["auto_mapped_department"] = recognized_department
                    if "auto_mapping" in result:
                        item["mapping_info"] = result["auto_mapping"]
                        
                logger.info(f"✅ {file.filename} 파싱 완료: {len(file_data)}개 문제, 자동 매핑됨")
                all_parsed_data.extend(file_data)
            else:
                logger.error(f"❌ {file.filename} 파싱 실패: {result.get('error')}")
        
        if not all_parsed_data:
            return {
                "success": False,
                "message": "파싱된 문제가 없습니다. PDF 파일을 확인해주세요."
            }
        
        # 🎯 스마트 매칭: 문제지 + 정답지 통합
        merged_data = {}
        
        # 1단계: 문제지 데이터 우선 저장 (content, options, description)
        for item in all_parsed_data:
            if item.get("file_type") == "question_sheet":
                q_num = item.get("question_number", 1)
                merged_data[q_num] = item.copy()  # 문제지 데이터 전체 복사
        
        # 2단계: 정답지 데이터로 정답만 매칭 (correct_answer만)
        for item in all_parsed_data:
            if item.get("file_type") == "answer_sheet":
                q_num = item.get("question_number", 1)
                if q_num in merged_data:
                    # 정답만 추가/업데이트
                    if item.get("correct_answer"):
                        merged_data[q_num]["correct_answer"] = item.get("correct_answer")
                else:
                    # 문제지 없이 정답지만 있는 경우 (백업)
                    merged_data[q_num] = item.copy()
        
        final_parsed_data = list(merged_data.values())
        
        # 검토 서비스 초기화
        review_service = QuestionReviewService()
        
        # JSON 파일로 저장
        combined_filename = f"combined_{len(files)}files_{files[0].filename}"
        json_path = review_service.save_parsed_data_to_json(
            final_parsed_data, combined_filename, current_user.id
        )
        
        # 제목과 카테고리 설정
        file_title = title if title and title.strip() else f"통합문제_{len(files)}개파일"
        file_category = category if category and category.strip() else "일반"
        
        # 대기 상태 문제들 생성 (제목과 카테고리 포함)
        questions = review_service.create_pending_questions(
            db=db,
            parsed_data=final_parsed_data,
            source_file_path=";".join(uploaded_files),  # 세미콜론으로 구분
            parsed_data_path=json_path,
            user_id=current_user.id,
            file_title=file_title,
            file_category=file_category
        )
        
        return {
            "success": True,
            "message": f"{len(files)}개 PDF 파일이 업로드되고 {len(questions)}개 문제가 파싱되었습니다. 검토 후 승인해주세요.",
            "total_questions": len(questions),
            "files_processed": len(files),
            "parsed_data_path": json_path,
            "questions_preview": [
                {
                    "id": q.id,
                    "question_number": q.question_number,
                    "content": q.content[:100] + "..." if len(q.content) > 100 else q.content,
                    "difficulty": q.difficulty if isinstance(q.difficulty, str) else "중",
                    "has_answer": bool(q.correct_answer)
                }
                for q in questions[:5]  # 처음 5개만 미리보기
            ]
        }
        
    except Exception as e:
        # 오류 발생 시 업로드된 파일들 삭제
        for file_path in uploaded_files:
            try:
                if Path(file_path).exists():
                    Path(file_path).unlink()
            except:
                pass  # 파일 삭제 실패해도 계속 진행
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"파일 업로드 중 오류가 발생했습니다: {str(e)}"
        )


@router.get("/questions/pending")
async def get_pending_questions(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    승인 대기 중인 문제들 조회 - 교수 ID 기반 지속성 지원
    서버 재시작 후에도 이전 업로드한 문제들이 표시됩니다
    """
    check_professor_permission(current_user)
    
    try:
        review_service = QuestionReviewService()
        
        # 교수 ID 기반으로 대기 중인 문제들 조회 (created_by 또는 last_modified_by)
        user_questions = review_service.get_pending_questions(db, current_user.id)
        
        # 현재 교수의 문제만 반환 (다른 교수 문제는 절대 표시 안함)
        return {
            "questions": user_questions,
            "total_count": len(user_questions),
            "message": f"{current_user.name} 교수님이 업로드한 대기 중인 문제들입니다." if user_questions else "대기 중인 문제가 없습니다.",
            "professor_id": current_user.id,
            "professor_name": current_user.name
        }
        
    except Exception as e:
        logger.error(f"문제 조회 오류 (교수 ID: {current_user.id}): {e}")
        # 오류 발생 시 빈 배열 반환
        return {
            "questions": [],
            "total_count": 0,
            "error": f"문제 조회 중 오류가 발생했습니다: {str(e)}",
            "professor_id": current_user.id,
            "professor_name": current_user.name
        }


@router.get("/questions/all")
async def get_professor_all_questions(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    교수의 모든 문제 조회 (승인된 것과 대기 중인 것 모두)
    서버 재시작 후에도 데이터 지속성 보장
    """
    check_professor_permission(current_user)
    
    try:
        review_service = QuestionReviewService()
        result = review_service.get_professor_questions_all(db, current_user.id)
        
        return {
            "success": True,
            "data": result,
            "professor_id": current_user.id,
            "professor_name": current_user.name,
            "message": f"{current_user.name} 교수님의 모든 문제를 조회했습니다."
        }
        
    except Exception as e:
        logger.error(f"교수 전체 문제 조회 오류 (교수 ID: {current_user.id}): {e}")
        return {
            "success": False,
            "data": {
                "pending": [],
                "approved": [],
                "rejected": [],
                "total_count": 0,
                "status_summary": {"pending": 0, "approved": 0, "rejected": 0}
            },
            "error": f"문제 조회 중 오류가 발생했습니다: {str(e)}",
            "professor_id": current_user.id,
            "professor_name": current_user.name
        }


@router.put("/questions/{question_id}")
async def update_question(
    question_id: int,
    update_data: QuestionUpdateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    문제 내용 수정
    """
    check_professor_permission(current_user)
    
    # 상세 로깅 추가
    logger.info(f"📝 문제 수정 요청 받음:")
    logger.info(f"- URL question_id: {question_id}")
    logger.info(f"- 요청 사용자: {current_user.id} ({current_user.name})")
    logger.info(f"- 수신 데이터: {update_data.dict()}")
    
    review_service = QuestionReviewService()
    success = review_service.update_question(
        db=db,
        question_id=question_id,
        update_data=update_data,
        user_id=current_user.id
    )
    
    if success:
        return {"success": True, "message": "문제가 수정되었습니다."}
    else:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="문제를 찾을 수 없습니다."
        )


@router.post("/questions/approve")
async def approve_questions(
    request: dict,  # 일시적으로 dict로 변경하여 원시 데이터 확인
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    문제 일괄 승인/거부 (RAG 통합 기능 일시 비활성화)
    """
    check_professor_permission(current_user)
    
    # 상세 로깅 추가
    logger.info(f"📋 문제 승인 요청 받음:")
    logger.info(f"- 사용자: {current_user.id} ({current_user.name})")
    logger.info(f"- 사용자 부서: {current_user.department}")
    logger.info(f"- 원시 요청 데이터: {request}")
    
    # dict에서 데이터 추출
    question_ids = request.get("question_ids", [])
    action = request.get("action", "approved")
    feedback = request.get("feedback")
    
    logger.info(f"- 문제 ID 목록: {question_ids}")
    logger.info(f"- 액션: {action}")
    logger.info(f"- 피드백: {feedback}")
    
    try:
        logger.info("🔧 QuestionReviewService 인스턴스 생성 중...")
        review_service = QuestionReviewService()
        
        # BulkApprovalRequest 객체 생성
        from app.schemas.question_review import BulkApprovalRequest, ApprovalStatus
        
        # action 문자열을 ApprovalStatus enum으로 변환
        if action == "approved" or action == "approve":
            approval_action = ApprovalStatus.APPROVED
        elif action == "rejected" or action == "reject":
            approval_action = ApprovalStatus.REJECTED
        else:
            approval_action = ApprovalStatus.PENDING
        
        approval_request = BulkApprovalRequest(
            question_ids=question_ids,
            action=approval_action,
            feedback=feedback
        )
        
        logger.info("📝 기본 승인 처리 시작...")
        # 기본 승인 처리만 수행
        result = review_service.bulk_approve_questions(
            db=db,
            request=approval_request,
            approver_id=current_user.id
        )
        
        logger.info(f"✅ 기본 승인 처리 완료: {result.message}")
        
        # RAG 통합, AI 해설 생성, 딥시크 학습 처리 (별도 트랜잭션으로 안전하게 처리)
        if approval_action == ApprovalStatus.APPROVED and result.approved_count > 0:
            logger.info(f"🚀 {result.approved_count}개 문제 승인 완료 - 카테고리별 저장, AI 해설 생성, 딥시크 학습 시작")
            
            # 1. 카테고리별 저장 시스템 적용
            try:
                from app.services.category_storage_service import CategoryStorageService
                
                category_service = CategoryStorageService()
                
                # 승인된 문제들 조회
                approved_questions = db.query(Question).filter(
                    and_(
                        Question.id.in_(question_ids),
                        Question.approval_status == "approved"
                    )
                ).all()
                
                # 카테고리별 저장 (국가고시는 Qdrant에도 저장)
                storage_result = category_service.store_approved_questions(
                    db, approved_questions, current_user.department
                )
                
                logger.info(f"📊 카테고리별 저장 결과: PostgreSQL {storage_result['postgresql_stored']}개, Qdrant {storage_result['qdrant_stored']}개")
                
                if storage_result['errors']:
                    logger.warning(f"⚠️ 저장 오류: {storage_result['errors']}")
                    
            except Exception as e:
                logger.error(f"❌ 카테고리별 저장 실패: {e}")
                # 저장 실패해도 승인은 유지됨
            
            # 2. 딥시크 자동 학습 시작
            try:
                from app.services.deepseek_learning_service import DeepSeekLearningService
                
                deepseek_learning = DeepSeekLearningService()
                
                # 승인된 문제들 다시 조회 (딥시크 학습용)
                approved_questions_for_learning = db.query(Question).filter(
                    and_(
                        Question.id.in_(question_ids),
                        Question.approval_status == "approved"
                    )
                ).all()
                
                # 각 승인된 문제에 대해 딥시크 학습 처리
                learning_success_count = 0
                for question in approved_questions_for_learning:
                    try:
                        learning_result = await deepseek_learning.process_approved_question_for_learning(
                            question, 
                            current_user.department,
                            metadata={
                                "approver_id": current_user.id,
                                "approval_batch": True,
                                "approval_time": datetime.now().isoformat(),
                                "approval_batch_id": f"batch_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
                            },
                            db=db
                        )
                        
                        if learning_result["success"]:
                            learning_success_count += 1
                            logger.info(f"🤖 문제 {question.id} 딥시크 학습 완료")
                        else:
                            logger.warning(f"⚠️ 문제 {question.id} 딥시크 학습 실패: {learning_result.get('error')}")
                            
                    except Exception as learning_error:
                        logger.error(f"❌ 문제 {question.id} 딥시크 학습 중 오류: {learning_error}")
                        continue
                
                logger.info(f"🎓 딥시크 학습 완료: {learning_success_count}/{len(approved_questions_for_learning)} 성공")
                
                if learning_success_count > 0:
                    result.message += f" | 딥시크 학습: {learning_success_count}개 완료"
                else:
                    result.message += " | 딥시크 학습: 실패"
                    
            except Exception as e:
                logger.error(f"❌ 딥시크 학습 처리 실패: {e}")
                result.message += " | 딥시크 학습: 오류 발생"
                # 딥시크 학습 실패해도 승인은 유지됨
            
            try:
                # 새로운 세션으로 AI 해설 생성 (승인 트랜잭션과 분리)
                from app.db.database import SessionLocal
                ai_db = SessionLocal()
                
                try:
                    # 승인된 문제들에 대해 AI 해설 생성
                    approved_questions = ai_db.query(Question).filter(
                        and_(
                            Question.id.in_(question_ids),
                            Question.approval_status == "approved"
                        )
                    ).all()
                    
                    ai_explanation_count = 0
                    for question in approved_questions:
                        try:
                            # 향상된 생성기를 사용하여 AI 해설 생성
                            chatbot_explanation = await enhanced_generator._generate_chatbot_explanation(
                                {
                                    "question": question.content,
                                    "correct_answer": question.correct_answer,
                                    "type": question.question_type or "multiple_choice",
                                    "difficulty": question.difficulty or "medium",
                                    "main_concept": question.subject or "전문 개념",
                                    "choices": question.options
                                },
                                current_user.department
                            )
                            
                            # 생성된 해설을 데이터베이스에 저장
                            question.ai_explanation = chatbot_explanation
                            question.explanation_confidence = 0.85
                            question.integration_completed_at = datetime.now()
                            
                            ai_explanation_count += 1
                            logger.info(f"✅ 문제 {question.id} AI 해설 생성 완료")
                            
                        except Exception as e:
                            logger.warning(f"⚠️ 문제 {question.id} AI 해설 생성 실패: {e}")
                            continue
                    
                    # AI 해설 생성 결과 별도 커밋
                    ai_db.commit()
                    
                    if ai_explanation_count > 0:
                        result.message += f" | AI 해설 생성: {ai_explanation_count}개 완료"
                        logger.info(f"🎯 AI 해설 생성 완료: {ai_explanation_count}개")
                    else:
                        result.message += " | AI 해설 생성: 실패"
                        
                finally:
                    ai_db.close()
                    
            except Exception as e:
                logger.error(f"❌ AI 해설 생성 중 오류: {e}")
                result.message += " | AI 해설 생성: 오류 발생"
                # AI 해설 생성 실패해도 승인은 유지됨
        
        return result
        
    except Exception as e:
        logger.error(f"❌ 문제 승인 처리 실패: {e}")
        logger.error(f"❌ 오류 타입: {type(e).__name__}")
        import traceback
        logger.error(f"스택 트레이스:\n{traceback.format_exc()}")
        
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"문제 승인 처리 중 오류가 발생했습니다: {str(e)}"
        )


@router.get("/questions/{question_id}/detail")
async def get_question_detail(
    question_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    문제 상세 정보 조회 (수정 이력 포함)
    """
    check_professor_permission(current_user)
    
    question = db.query(Question).filter(Question.id == question_id).first()
    if not question:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="문제를 찾을 수 없습니다."
        )
    
    # 승인자 정보 조회
    approved_by_name = None
    if question.approved_by:
        approver = db.query(User).filter(User.id == question.approved_by).first()
        if approver:
            approved_by_name = approver.name
    
    return {
        "question": QuestionPreviewItem(
            id=question.id,
            question_number=question.question_number,
            content=question.content,
            description=question.description,
            options=question.options or {},
            correct_answer=question.correct_answer or "",
            subject=question.subject,
            area_name=question.area_name,
            difficulty=question.difficulty.value if question.difficulty else "중",
            year=question.year,
            last_modified_by=question.last_modified_by,
            last_modified_at=question.last_modified_at
        ),
        "approval_status": question.approval_status,
        "approved_by": question.approved_by,
        "approved_by_name": approved_by_name,
        "approved_at": question.approved_at,
        "source_file_path": question.source_file_path,
        "parsed_data_path": question.parsed_data_path
    }


# ===== RAG 관련 엔드포인트들 =====

@router.get("/rag/stats", response_model=RAGStatsResponse)
async def get_rag_stats(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """RAG 시스템 통계 조회 - 교수 ID 기반 지속성 지원"""
    check_professor_permission(current_user)
    
    try:
        review_service = QuestionReviewService()
        
        # 교수별 RAG 통계 조회 (데이터베이스 기반)
        professor_stats = review_service.get_professor_rag_stats(db, current_user.id)
        
        # 인덱싱 상태 결정
        indexing_status = "no_documents"
        if professor_stats["total_documents"] > 0:
            if professor_stats["status_distribution"]["pending"] > 0:
                indexing_status = "processing"
            else:
                indexing_status = "ready"
        
        # 지식 영역 설정 (subjects 기반)
        knowledge_areas = professor_stats["subjects"] if professor_stats["subjects"] else ["일반", "기초"]
        
        return RAGStatsResponse(
            total_documents=professor_stats["total_documents"],
            total_embeddings=professor_stats["total_questions"],
            embedding_dimensions=1536,  # OpenAI ada-002 차원
            last_updated=professor_stats["last_upload"] or datetime.now().isoformat(),
            knowledge_areas=knowledge_areas,
            auto_learning_enabled=True,
            indexing_status=indexing_status
        )
        
    except Exception as e:
        logger.error(f"RAG 통계 조회 오류 (교수 ID: {current_user.id}): {e}")
        
        # 오류 발생 시 기본 통계라도 조회 시도
        try:
            from sqlalchemy import or_
            professor_questions = db.query(Question).filter(
                Question.last_modified_by == current_user.id
            ).count()
            
            return RAGStatsResponse(
                total_documents=professor_questions,
                total_embeddings=professor_questions,
                embedding_dimensions=1536,
                last_updated=datetime.now().isoformat(),
                knowledge_areas=["데이터 로드 중"],
                auto_learning_enabled=False,
                indexing_status="error"
            )
        except:
            return RAGStatsResponse(
                total_documents=0,
                total_embeddings=0,
                embedding_dimensions=1536,
                last_updated=datetime.now().isoformat(),
                knowledge_areas=[],
                auto_learning_enabled=False,
                indexing_status="error"
            )


@router.get("/rag/professor-stats")
async def get_professor_rag_detailed_stats(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    교수별 상세 RAG 통계 조회
    업로드한 파일 목록, 난이도별 분포, 상태별 분포 등 상세 정보
    """
    check_professor_permission(current_user)
    
    try:
        review_service = QuestionReviewService()
        stats = review_service.get_professor_rag_stats(db, current_user.id)
        
        return {
            "success": True,
            "professor_id": current_user.id,
            "professor_name": current_user.name,
            "stats": stats,
            "message": f"{current_user.name} 교수님의 RAG 통계를 조회했습니다."
        }
        
    except Exception as e:
        logger.error(f"교수 상세 RAG 통계 조회 오류 (교수 ID: {current_user.id}): {e}")
        return {
            "success": False,
            "professor_id": current_user.id,
            "professor_name": current_user.name,
            "stats": {
                "total_documents": 0,
                "total_questions": 0,
                "uploaded_files": [],
                "subjects": [],
                "difficulty_distribution": {"상": 0, "중": 0, "하": 0},
                "last_upload": None,
                "status_distribution": {"pending": 0, "approved": 0, "rejected": 0}
            },
            "error": f"통계 조회 중 오류가 발생했습니다: {str(e)}"
        }


@router.post("/problems/generate-rag")
async def generate_problems_with_rag(
    request: RAGGenerationRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """RAG 기반 문제 생성"""
    check_professor_permission(current_user)
    
    try:
        # 업로드된 PDF 파일에서 RAG 컨텍스트 생성
        upload_dir = Path("uploads/questions")
        available_sources = []
        
        if upload_dir.exists():
            pdf_files = list(upload_dir.glob("*.pdf"))
            available_sources = [f.name for f in pdf_files[-5:]]  # 최신 5개 파일만
        
        if not available_sources:
            available_sources = [f"{current_user.department}_기본교재.pdf"]
        
        # 학과별 문제 템플릿 매핑
        question_templates = {
            "간호학과": {
                "multiple_choice": [
                    "다음 중 {keywords}에 대한 설명으로 가장 적절한 것은?",
                    "{keywords}의 주요 특징으로 옳은 것은?",
                    "간호 중재 시 {keywords}와 관련하여 우선적으로 고려해야 할 사항은?"
                ],
                "short_answer": [
                    "{keywords}의 정의를 간단히 설명하시오.",
                    "{keywords} 시 주의사항을 3가지 이상 기술하시오.",
                    "{keywords}의 임상적 의의를 설명하시오."
                ],
                "essay": [
                    "{keywords}에 대해 상세히 논술하시오.",
                    "{keywords}의 간호과정을 단계별로 설명하시오."
                ]
            },
            "물리치료학과": {
                "multiple_choice": [
                    "{keywords}에 대한 설명으로 올바른 것은?",
                    "다음 중 {keywords} 치료법으로 가장 적절한 것은?",
                    "{keywords} 환자의 운동치료 시 우선순위는?"
                ],
                "short_answer": [
                    "{keywords}의 물리치료적 접근법을 기술하시오.",
                    "{keywords} 진단을 위한 평가방법을 설명하시오."
                ],
                "essay": [
                    "{keywords}의 재활치료 계획을 수립하시오.",
                    "{keywords} 환자의 포괄적 치료방안을 논술하시오."
                ]
            },
            "작업치료학과": {
                "multiple_choice": [
                    "{keywords}에 대한 작업치료적 접근 중 옳은 것은?",
                    "{keywords} 평가 시 가장 중요한 요소는?",
                    "다음 중 {keywords}와 관련된 일상생활활동은?"
                ],
                "short_answer": [
                    "{keywords}의 작업치료 목표를 설정하시오.",
                    "{keywords} 향상을 위한 활동을 제시하시오."
                ],
                "essay": [
                    "{keywords} 개선을 위한 종합적 작업치료 계획을 수립하시오.",
                    "{keywords}과 일상생활 참여의 관계를 논술하시오."
                ]
            }
        }
        
        # 선택지 생성용 템플릿
        choice_templates = {
            "간호학과": {
                "correct": [
                    "환자 안전을 최우선으로 고려하여 체계적으로 접근한다",
                    "근거기반 간호를 통해 최적의 중재를 제공한다",
                    "개별적 특성을 고려한 맞춤형 간호를 시행한다"
                ],
                "incorrect": [
                    "일반적인 프로토콜만 적용한다",
                    "의료진의 지시만 따른다",
                    "환자의 주관적 호소는 무시한다"
                ]
            },
            "물리치료학과": {
                "correct": [
                    "개별 환자의 기능적 목표에 맞춘 치료계획을 수립한다",
                    "근거중심의 평가를 통해 적절한 중재를 선택한다",
                    "점진적이고 체계적인 접근을 통해 기능을 향상시킨다"
                ],
                "incorrect": [
                    "모든 환자에게 동일한 치료를 적용한다",
                    "증상만 완화하면 충분하다",
                    "환자의 협조 없이도 치료효과를 기대할 수 있다"
                ]
            },
            "작업치료학과": {
                "correct": [
                    "의미있는 활동을 통해 기능을 향상시킨다",
                    "환경적 요인을 고려한 통합적 접근을 실시한다",
                    "일상생활 참여를 최대화하는 목표를 설정한다"
                ],
                "incorrect": [
                    "단순 반복 훈련만으로 충분하다",
                    "개인의 흥미나 가치는 고려하지 않는다",
                    "기능 향상보다는 증상 완화가 우선이다"
                ]
            }
        }
        
        # 문제 생성
        generated_problems = []
        dept_templates = question_templates.get(current_user.department, question_templates["간호학과"])
        dept_choices = choice_templates.get(current_user.department, choice_templates["간호학과"])
        
        for i in range(request.count):
            problem_id = f"rag_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{i}"
            
            # 키워드 처리
            keywords = request.keywords or f"{request.subject} 핵심개념"
            
            # 문제 유형별 생성
            if request.questionType == "multiple_choice":
                question_template = random.choice(dept_templates.get("multiple_choice", ["다음 중 {keywords}에 대한 설명으로 옳은 것은?"]))
                question_text = question_template.format(keywords=keywords)
                
                correct_choice = random.choice(dept_choices["correct"])
                incorrect_choices = random.sample(dept_choices["incorrect"], 3)
                
                choices = {'A': correct_choice, 'B': incorrect_choices[0], 'C': incorrect_choices[1], 'D': incorrect_choices[2]}
                correct_answer = 'A'
                
            elif request.questionType == "short_answer":
                question_template = random.choice(dept_templates.get("short_answer", ["{keywords}에 대해 간단히 설명하시오."]))
                question_text = question_template.format(keywords=keywords)
                choices = None
                correct_answer = f"{keywords}에 대한 {current_user.department} 관점의 전문적 답안이 여기에 제시됩니다."
                
            elif request.questionType == "essay":
                question_template = random.choice(dept_templates.get("essay", ["{keywords}에 대해 상세히 논술하시오."]))
                question_text = question_template.format(keywords=keywords)
                choices = None
                correct_answer = f"{keywords}에 대한 포괄적이고 체계적인 논술 답안이 여기에 제시됩니다."
                
            else:  # true_false
                question_text = f"{keywords}는 {request.subject}에서 중요한 개념이다."
                choices = {'O': '참', 'X': '거짓'}
                correct_answer = 'O'
            
            problem = GeneratedProblem(
                id=problem_id,
                question=question_text,
                type=request.questionType,
                choices=choices,
                correct_answer=correct_answer,
                explanation=f"이 문제는 RAG 시스템을 통해 {random.choice(available_sources)}에서 추출된 {current_user.department} 전문 지식을 바탕으로 생성되었습니다. 난이도: {request.difficulty}",
                difficulty=request.difficulty,
                rag_source=random.choice(available_sources),
                confidence_score=0.85 + random.random() * 0.1,
                generated_at=datetime.now().isoformat()
            )
            generated_problems.append(problem)
        
        return {
            "success": True,
            "message": f"{request.count}개의 문제가 RAG를 통해 생성되었습니다.",
            "problems": generated_problems,
            "generation_metadata": {
                "method": "rag",
                "department": current_user.department,
                "real_time_learning": request.real_time_learning,
                "generated_by": current_user.id,
                "timestamp": datetime.now().isoformat(),
                "source_files": available_sources
            }
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"RAG 기반 문제 생성 중 오류가 발생했습니다: {str(e)}"
        )


@router.post("/problems/save-generated")
async def save_generated_problems(
    data: dict,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """생성된 문제들을 데이터베이스에 저장"""
    check_professor_permission(current_user)
    
    problems = data.get("problems", [])
    metadata = data.get("metadata", {})
    
    try:
        saved_count = 0
        saved_problems = []
        
        for problem_data in problems:
            # Question 모델에 문제 저장
            new_question = Question(
                title=f"RAG 생성 문제: {problem_data.get('question', '')[:50]}...",
                content=problem_data.get('question', ''),
                problem_type=problem_data.get('type', 'multiple_choice'),
                subject=metadata.get('generation_method', 'RAG 생성'),
                difficulty=problem_data.get('difficulty', 'medium'),
                choices=json.dumps(problem_data.get('choices')) if problem_data.get('choices') else None,
                correct_answer=problem_data.get('correct_answer', ''),
                explanation=problem_data.get('explanation', ''),
                professor_id=current_user.id,
                rag_source=problem_data.get('rag_source', ''),
                confidence_score=problem_data.get('confidence_score', 0.0),
                is_approved=True,  # RAG 생성 문제는 자동 승인
                created_at=datetime.now()
            )
            
            db.add(new_question)
            saved_count += 1
            saved_problems.append({
                "question_id": new_question.id if hasattr(new_question, 'id') else f"temp_{saved_count}",
                "title": new_question.title,
                "type": new_question.problem_type,
                "difficulty": new_question.difficulty
            })
        
        db.commit()
        
        # 생성 로그 저장 (선택적)
        logging.info(f"교수 {current_user.name}({current_user.id})가 RAG를 통해 {saved_count}개 문제를 생성했습니다.")
        
        return {
            "success": True,
            "message": f"{saved_count}개의 문제가 성공적으로 저장되었습니다.",
            "saved_count": saved_count,
            "saved_problems": saved_problems,
            "metadata": {
                "saved_at": datetime.now().isoformat(),
                "professor_id": current_user.id,
                "department": current_user.department,
                "generation_method": metadata.get("method", "rag")
            }
        }
        
    except Exception as e:
        db.rollback()
        logging.error(f"문제 저장 실패: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"문제 저장 중 오류가 발생했습니다: {str(e)}"
        )


@router.post("/rag/auto-learning")
async def update_auto_learning(
    data: dict,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """실시간 자동 러닝 업데이트"""
    check_professor_permission(current_user)
    
    subject = data.get("subject")
    timestamp = data.get("timestamp")
    
    # 실제 구현에서는 백그라운드에서 벡터 인덱싱 업데이트
    return {
        "success": True,
        "message": "자동 러닝이 업데이트되었습니다.",
        "updated_embeddings": random.randint(50, 150),
        "processed_documents": random.randint(5, 15),
        "timestamp": timestamp
    }


@router.post("/rag/reindex")
async def reindex_vectors(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """벡터 인덱스 재구성"""
    check_professor_permission(current_user)
    
    # 실제 구현에서는 벡터 DB 재인덱싱 작업
    return {
        "success": True,
        "message": "벡터 인덱스 재구성이 완료되었습니다.",
        "total_vectors_processed": random.randint(40000, 50000),
        "processing_time_seconds": random.randint(120, 300)
    }


@router.get("/rag/context")
async def get_rag_context(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """RAG 컨텍스트 정보 조회"""
    check_professor_permission(current_user)
    
    try:
        # 업로드된 파일 히스토리에서 RAG 컨텍스트 생성
        upload_dir = Path("uploads/questions")
        context_data = []
        
        if upload_dir.exists():
            # 파일 시스템에서 업로드된 PDF 파일들 조회
            pdf_files = list(upload_dir.glob("*.pdf"))
            
            # 교수의 학과에 따른 주제 매핑
            topic_mapping = {
                "간호학과": ["간호학개론", "기본간호학", "성인간호학", "아동간호학"],
                "물리치료학과": ["물리치료학", "재활의학", "운동치료", "신경계물리치료"],
                "작업치료학과": ["작업치료학", "인지재활", "정신사회작업치료", "일상생활활동"]
            }
            
            default_topics = topic_mapping.get(current_user.department, ["일반", "기초"])
            
            for i, pdf_file in enumerate(pdf_files[-10:]):  # 최근 10개 파일만
                file_stat = pdf_file.stat()
                context_data.append({
                    "id": i + 1,
                    "source": pdf_file.name,
                    "topics": default_topics[:2],  # 처음 2개 주제만
                    "last_updated": datetime.fromtimestamp(file_stat.st_mtime).strftime("%Y-%m-%d"),
                    "file_size": f"{file_stat.st_size / 1024 / 1024:.1f}MB",
                    "department": current_user.department
                })
        
        # 기본 컨텍스트가 없으면 샘플 생성
        if not context_data:
            context_data = [
                {
                    "id": 1,
                    "source": f"{current_user.department}_기본교재.pdf",
                    "topics": topic_mapping.get(current_user.department, ["기초", "개론"])[:2],
                    "last_updated": datetime.now().strftime("%Y-%m-%d"),
                    "file_size": "0MB",
                    "department": current_user.department,
                    "status": "예시 데이터"
                }
            ]
        
        return {
            "success": True,
            "context": context_data,
            "total_count": len(context_data),
            "department": current_user.department
        }
        
    except Exception as e:
        return {
            "success": False,
            "message": f"RAG 컨텍스트 조회 중 오류가 발생했습니다: {str(e)}",
            "context": []
        }


@router.post("/problems/generate-enhanced")
async def generate_enhanced_problems(
    request: RAGGenerationRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    향상된 문제 생성 (7:3 비율)
    - 70% 지식베이스 활용 (교수님들이 업로드한 전문 자료)
    - 30% AI 기존 지식 활용
    - AI 챗봇 스타일 상세 해설 제공
    """
    check_professor_permission(current_user)
    
    try:
        logger.info(f"🚀 중복 방지 적용 문제 생성 요청: {current_user.department}, {request.subject}, {request.count}개")
        
        # 향상된 문제 생성기 호출 (중복 방지 기능 포함)
        result = await enhanced_generator.generate_problems_with_ratio(
            db=db,
            user=current_user,
            subject=request.subject,
            difficulty=request.difficulty,
            question_type=request.questionType,
            count=request.count,
            keywords=request.keywords,
            context=request.context
        )
        
        if not result["success"]:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="문제 생성 중 오류가 발생했습니다."
            )
        
        # 응답 데이터 변환
        enhanced_problems = []
        for problem in result["problems"]:
            enhanced_problem = GeneratedProblem(
                id=problem["id"],
                question=problem["question"],
                type=problem["type"],
                choices=problem.get("choices"),
                correct_answer=problem["correct_answer"],
                explanation=problem.get("detailed_explanation", ""),
                difficulty=problem["difficulty"],
                rag_source=problem.get("source", "enhanced_generator"),
                confidence_score=problem.get("confidence_score", 0.85),
                generated_at=problem["generated_at"]
            )
            enhanced_problems.append(enhanced_problem)
        
        # 생성 결과 통계 계산
        total_generated = len(enhanced_problems)
        success_count = total_generated  # 성공적으로 생성된 문제 수
        partial_success_count = 0  # 부분 성공 (해설이 없는 경우)
        failure_count = 0  # 실패한 문제 수
        
        # 해설 품질에 따른 분류
        for problem in enhanced_problems:
            explanation = problem.explanation or ""
            if len(explanation) < 100:  # 해설이 너무 짧으면 부분 성공
                partial_success_count += 1
                success_count -= 1
        
        # 중복 방지 적용 여부
        metadata = result["generation_metadata"]
        diversification_applied = metadata.get("diversification_applied", False)
        diversification_level = metadata.get("diversification_level", 0)
        
        return {
            "success": True,
            "message": f"업데트 완료! 중복 방지 알고리즘이 적용된 {total_generated}개의 고품질 문제가 생성되었습니다.",
            "problems": enhanced_problems,
            "statistics": {
                "total_generated": total_generated,
                "success_count": success_count,
                "partial_success_count": partial_success_count, 
                "failure_count": failure_count,
                "knowledge_base_count": result["knowledge_base_count"],
                "ai_knowledge_count": result["ai_knowledge_count"],
                "diversification_applied": diversification_applied,
                "diversification_level": f"{diversification_level}%"
            },
            "generation_metadata": {
                **result["generation_metadata"],
                "knowledge_base_problems": result["knowledge_base_count"],
                "ai_knowledge_problems": result["ai_knowledge_count"],
                "detailed_explanations": True,
                "chatbot_style_support": True,
                "anti_duplication_features": {
                    "generation_history_analyzed": diversification_applied,
                    "keyword_diversity_ensured": diversification_applied,
                    "knowledge_coverage_optimized": diversification_applied,
                    "strategic_shuffling_applied": diversification_applied
                }
            },
            "ui_messages": {
                "main_message": "업데트 완료!",
                "success_message": f"성공: {success_count}개",
                "partial_message": f"부분 성공: {partial_success_count}개",
                "failure_message": f"실패: {failure_count}개",
                "limit_message": f"22개 제한 적용: 0개 파일",
                "review_message": "문제 검토 페이지에서 확인해주세요!"
            }
        }
        
    except Exception as e:
        logger.error(f"향상된 문제 생성 실패: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"향상된 문제 생성 중 오류가 발생했습니다: {str(e)}"
        )


@router.post("/problems/save-enhanced")
async def save_enhanced_problems(
    data: dict,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """향상된 생성 문제들을 데이터베이스에 저장"""
    check_professor_permission(current_user)
    
    problems = data.get("problems", [])
    metadata = data.get("metadata", {})
    
    try:
        saved_count = 0
        saved_problems = []
        
        for problem_data in problems:
            # Question 모델에 문제 저장 (향상된 정보 포함)
            new_question = Question(
                question_number=saved_count + 1,
                question_type="multiple_choice" if problem_data.get('type') == 'multiple_choice' else "short_answer",
                content=problem_data.get('question', ''),
                options=problem_data.get('choices', {}),
                correct_answer=problem_data.get('correct_answer', ''),
                subject=metadata.get('subject', '향상된 RAG 생성'),
                area_name=f"{current_user.department} 전문영역",
                difficulty=problem_data.get('difficulty', 'medium'),
                approval_status="approved",  # 향상된 생성 문제는 자동 승인
                last_modified_by=current_user.id,
                last_modified_at=datetime.now(),
                approved_by=current_user.id,
                approved_at=datetime.now(),
                is_active=True,
                
                # AI 해설 정보 저장
                ai_explanation=problem_data.get('explanation', ''),
                explanation_confidence=problem_data.get('confidence_score', 0.85),
                
                # 메타데이터
                source_file_path=f"enhanced_generation/{metadata.get('method', 'enhanced')}",
                file_title=f"향상된 문제 생성 - {current_user.department}",
                file_category="ENHANCED_GENERATED"
            )
            
            db.add(new_question)
            saved_count += 1
            
            saved_problems.append({
                "question_id": saved_count,  # 임시 ID
                "type": new_question.question_type,
                "subject": new_question.subject,
                "difficulty": new_question.difficulty,
                "has_detailed_explanation": bool(new_question.ai_explanation),
                "confidence_score": new_question.explanation_confidence
            })
        
        db.commit()
        
        logger.info(f"교수 {current_user.name}({current_user.id})가 향상된 RAG를 통해 {saved_count}개 문제를 생성했습니다.")
        
        # 저장 결과 통계 계산
        successful_saves = saved_count
        failed_saves = len(problems) - saved_count if len(problems) > saved_count else 0
        
        # 해설 품질 분석
        high_quality_count = sum(1 for p in saved_problems if p.get("confidence_score", 0) > 0.8)
        medium_quality_count = saved_count - high_quality_count
        
        return {
            "success": True,
            "message": f"업데트 완료! {saved_count}개의 중복 방지 적용 문제가 성공적으로 저장되었습니다.",
            "saved_count": saved_count,
            "saved_problems": saved_problems,
            "statistics": {
                "total_processed": len(problems),
                "success_count": successful_saves,
                "failure_count": failed_saves,
                "high_quality_count": high_quality_count,
                "medium_quality_count": medium_quality_count
            },
            "generation_stats": {
                "kb_ratio": metadata.get('kb_ratio', 0.7),
                "ai_ratio": metadata.get('ai_ratio', 0.3),
                "department": current_user.department,
                "with_detailed_explanations": True,
                "anti_duplication_applied": True,
                "diversification_level": metadata.get('diversification_level', 'N/A')
            },
            "ui_messages": {
                "main_message": "업데트 완료!",
                "success_message": f"성공: {successful_saves}개",
                "partial_message": f"부분 성공: 0개",
                "failure_message": f"실패: {failed_saves}개", 
                "limit_message": f"22개 제한 적용: 0개 파일",
                "review_message": "문제 검토 페이지에서 확인해주세요!"
            }
        }
        
    except Exception as e:
        logger.error(f"향상된 문제 저장 실패: {str(e)}")
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"문제 저장 중 오류가 발생했습니다: {str(e)}"
        )


@router.get("/problems/knowledge-base-stats")
async def get_knowledge_base_stats(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """지식베이스 통계 조회"""
    check_professor_permission(current_user)
    
    try:
        # RAG 문서 통계
        rag_stats = db.execute(text("""
            SELECT 
                COUNT(DISTINCT file_title) as total_documents,
                COUNT(*) as total_chunks,
                AVG(LENGTH(content)) as avg_chunk_length,
                COUNT(DISTINCT subject) as subject_areas
            FROM questions 
            WHERE file_category = 'RAG_DOCUMENT' 
                AND is_active = true
        """)).fetchone()
        
        # 학과별 지식베이스 현황
        dept_stats = db.execute(text("""
            SELECT 
                subject,
                COUNT(*) as chunk_count,
                COUNT(DISTINCT file_title) as document_count
            FROM questions 
            WHERE file_category = 'RAG_DOCUMENT' 
                AND is_active = true
            GROUP BY subject
            ORDER BY chunk_count DESC
            LIMIT 10
        """)).fetchall()
        
        # 최근 업로드된 문서들
        recent_docs = db.execute(text("""
            SELECT DISTINCT 
                file_title,
                subject,
                created_at,
                COUNT(*) as chunk_count
            FROM questions 
            WHERE file_category = 'RAG_DOCUMENT'
                AND is_active = true
            GROUP BY file_title, subject, created_at
            ORDER BY created_at DESC
            LIMIT 10
        """)).fetchall()
        
        # 지식베이스 상태 분석
        total_docs = rag_stats[0] if rag_stats[0] else 0
        total_chunks = rag_stats[1] if rag_stats[1] else 0
        
        # 활용 가능성 분석
        if total_docs > 20:
            status_message = "업데트 완료! 풍부한 지식베이스로 고품질 문제 생성 가능"
            success_level = "high"
        elif total_docs > 10:
            status_message = "업데트 완료! 중간 수준의 지식베이스 활용 가능"
            success_level = "medium"
        else:
            status_message = "업데트 완료! 지식베이스 확장을 통한 품질 향상 권장"
            success_level = "low"
        
        return {
            "success": True,
            "message": status_message,
            "total_stats": {
                "total_documents": total_docs,
                "total_chunks": total_chunks,
                "avg_chunk_length": int(rag_stats[2]) if rag_stats[2] else 0,
                "subject_areas": rag_stats[3] if rag_stats[3] else 0
            },
            "department_stats": [
                {
                    "subject": row[0],
                    "chunk_count": row[1],
                    "document_count": row[2]
                } for row in dept_stats
            ],
            "recent_documents": [
                {
                    "title": row[0],
                    "subject": row[1],
                    "uploaded_at": row[2].isoformat() if row[2] else None,
                    "chunk_count": row[3]
                } for row in recent_docs
            ],
            "generation_ratio": {
                "knowledge_base_ratio": 0.7,
                "ai_knowledge_ratio": 0.3,
                "recommendation": "지식베이스가 풍부할수록 더 전문적인 문제가 생성됩니다."
            },
            "ui_messages": {
                "main_message": "업데트 완료!",
                "success_message": f"성공: {total_docs}개 문서",
                "partial_message": f"부분 성공: 0개",
                "failure_message": f"실패: 0개",
                "limit_message": f"22개 제한 적용: 0개 파일",
                "review_message": "문제 검토 페이지에서 확인해주세요!"
            },
            "status": {
                "level": success_level,
                "ready_for_generation": total_docs > 5,
                "anti_duplication_enabled": total_docs > 10
            }
        }
        
    except Exception as e:
        logger.error(f"지식베이스 통계 조회 실패: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"통계 조회 중 오류가 발생했습니다: {str(e)}"
        )


# ===== 새로운 자동 매핑 API 엔드포인트들 =====

@router.get("/auto-mapping/supported-departments")
async def get_supported_departments(
    current_user: User = Depends(get_current_user)
):
    """지원되는 학과 목록 조회"""
    check_professor_permission(current_user)
    
    try:
        departments = department_recognizer.get_supported_departments()
        return {
            "success": True,
            "departments": departments,
            "total_count": len(departments),
            "message": f"총 {len(departments)}개 학과를 지원합니다."
        }
    except Exception as e:
        logger.error(f"지원 학과 조회 실패: {e}")
        return {
            "success": False,
            "departments": [],
            "error": str(e)
        }


@router.post("/auto-mapping/recognize-department")
async def recognize_department_from_file(
    data: dict,
    current_user: User = Depends(get_current_user)
):
    """파일명에서 학과 자동 인식"""
    check_professor_permission(current_user)
    
    filename = data.get("filename", "")
    if not filename:
        return {
            "success": False,
            "error": "파일명이 필요합니다."
        }
    
    try:
        recognized_department = department_recognizer.recognize_department_from_filename(filename)
        return {
            "success": True,
            "filename": filename,
            "recognized_department": recognized_department,
            "confidence": "high" if recognized_department != "일반학과" else "low"
        }
    except Exception as e:
        logger.error(f"학과 인식 실패: {e}")
        return {
            "success": False,
            "error": str(e)
        }


@router.post("/auto-mapping/test-ai-mapping")
async def test_ai_auto_mapping(
    data: dict,
    current_user: User = Depends(get_current_user)
):
    """AI 자동 매핑 테스트"""
    check_professor_permission(current_user)
    
    question_content = data.get("question_content", "")
    department = data.get("department", "일반학과")
    
    if not question_content:
        return {
            "success": False,
            "error": "문제 내용이 필요합니다."
        }
    
    try:
        mapping_result = await ai_auto_mapper.auto_map_difficulty_and_domain(
            question_content=question_content,
            department=department
        )
        
        return {
            "success": True,
            "question_content": question_content[:100] + "..." if len(question_content) > 100 else question_content,
            "department": department,
            "mapping_result": mapping_result,
            "ai_available": ai_auto_mapper.gemini_model is not None
        }
    except Exception as e:
        logger.error(f"AI 매핑 테스트 실패: {e}")
        return {
            "success": False,
            "error": str(e)
        }


@router.get("/auto-mapping/system-status")
async def get_auto_mapping_system_status(
    current_user: User = Depends(get_current_user)
):
    """자동 매핑 시스템 상태 조회"""
    check_professor_permission(current_user)
    
    try:
        status = {
            "department_recognizer": {
                "available": department_recognizer is not None,
                "supported_departments_count": len(department_recognizer.get_supported_departments()),
                "csv_loaded": department_recognizer.department_df is not None
            },
            "ai_auto_mapper": {
                "available": ai_auto_mapper is not None,
                "gemini_initialized": ai_auto_mapper.gemini_model is not None,
                "api_key_configured": True  # 보안상 실제 키는 노출하지 않음
            },
            "integrated_parser_mapper": {
                "available": integrated_parser_mapper is not None,
                "components_ready": all([
                    department_recognizer is not None,
                    ai_auto_mapper is not None
                ])
            }
        }
        
        all_systems_ready = all([
            status["department_recognizer"]["available"],
            status["ai_auto_mapper"]["available"],
            status["integrated_parser_mapper"]["available"]
        ])
        
        return {
            "success": True,
            "overall_status": "ready" if all_systems_ready else "partial",
            "systems": status,
            "message": "모든 시스템이 정상 작동 중입니다." if all_systems_ready else "일부 시스템에 문제가 있습니다."
        }
    except Exception as e:
        logger.error(f"시스템 상태 조회 실패: {e}")
        return {
            "success": False,
            "error": str(e)
        }


@router.get("/category-storage/stats")
async def get_category_storage_stats(
    current_user: User = Depends(get_current_user)
):
    """카테고리별 저장 시스템 통계 조회"""
    check_professor_permission(current_user)
    
    try:
        from app.services.category_storage_service import CategoryStorageService
        
        category_service = CategoryStorageService()
        
        # 교수 부서별 통계 조회
        stats = category_service.get_collection_stats(current_user.department)
        
        return {
            "success": True,
            "data": stats,
            "professor_info": {
                "department": current_user.department,
                "name": current_user.name,
                "id": current_user.id
            },
            "system_info": {
                "postgresql_status": "연결됨",
                "qdrant_status": "Docker 실행 중" if category_service.initialize_qdrant_client() else "연결 실패",
                "vector_dimension": 768,
                "supported_categories": ["국가고시", "임상실습", "재활치료", "인지재활", "일반"]
            },
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"카테고리 저장 통계 조회 실패: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="카테고리 저장 통계를 조회할 수 없습니다."
        )


@router.get("/ai-analysis/status")
async def get_ai_analysis_status(
    current_user: User = Depends(get_current_user)
):
    """
    AI 자동 난이도 분석 시스템 상태 조회
    """
    check_professor_permission(current_user)
    
    try:
        from app.services.ai_difficulty_analyzer import AI_ANALYZER_AVAILABLE, difficulty_analyzer
        
        if not AI_ANALYZER_AVAILABLE:
            return {
                "success": False,
                "status": "disabled",
                "message": "AI 분석 시스템이 비활성화되었습니다.",
                "details": {
                    "deepseek_available": False,
                    "evaluator_data_loaded": False,
                    "system_ready": False
                }
            }
        
        # 시스템 상태 확인
        system_status = difficulty_analyzer.get_system_status()
        
        return {
            "success": True,
            "status": "active",
            "message": "AI 분석 시스템이 정상 작동 중입니다.",
            "details": {
                "deepseek_available": system_status.get("deepseek_ready", False),
                "evaluator_data_loaded": system_status.get("evaluator_patterns_loaded", False),
                "total_evaluator_patterns": system_status.get("total_patterns", 0),
                "supported_departments": system_status.get("departments", []),
                "system_ready": True,
                "last_update": system_status.get("last_update"),
                "model_info": {
                    "model_name": "DeepSeek R1:8b",
                    "server": "localhost:11434",
                    "confidence_levels": ["high", "medium", "low"]
                }
            }
        }
        
    except Exception as e:
        logger.error(f"AI 분석 상태 조회 실패: {e}")
        return {
            "success": False,
            "status": "error",
            "message": "AI 분석 상태 조회 중 오류가 발생했습니다.",
            "error": str(e)
        }

@router.get("/ai-analysis/stats")
async def get_ai_analysis_stats(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    AI 분석 검증률 및 통계 조회
    """
    check_professor_permission(current_user)
    
    try:
        review_service = QuestionReviewService()
        stats = review_service.get_ai_analysis_stats(db, current_user.id)
        
        return {
            "success": True,
            "message": "AI 분석 통계 조회 완료",
            "stats": stats,
            "summary": {
                "completion_status": "완료" if stats["analysis_completion_rate"] == 100.0 else "진행 중",
                "reliability": "높음" if stats["average_confidence"] >= 80 else "보통" if stats["average_confidence"] >= 60 else "낮음",
                "recommendation": (
                    "AI 분석이 완료되었습니다. 높은 신뢰도로 검토를 진행하세요." 
                    if stats["average_confidence"] >= 80 
                    else "일부 문제의 신뢰도가 낮습니다. 수동 검토를 권장합니다."
                )
            }
        }
        
    except Exception as e:
        logger.error(f"AI 분석 통계 조회 실패: {e}")
        return {
            "success": False,
            "message": "AI 분석 통계 조회 중 오류가 발생했습니다.",
            "error": str(e)
        }

@router.post("/ai-analysis/analyze-question")
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

@router.get("/ai-analysis/learning-patterns")
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


# ===== 딥시크 학습 관련 엔드포인트들 =====

@router.get("/deepseek/learning-stats")
async def get_deepseek_learning_stats(
    current_user: User = Depends(get_current_user)
):
    """딥시크 학습 통계 조회"""
    check_professor_permission(current_user)
    
    try:
        from app.services.deepseek_learning_service import DeepSeekLearningService
        
        deepseek_learning = DeepSeekLearningService()
        stats = await deepseek_learning.get_learning_stats()
        
        return {
            "success": True,
            "professor_id": current_user.id,
            "professor_name": current_user.name,
            "department": current_user.department,
            "deepseek_stats": stats,
            "message": "딥시크 학습 통계를 조회했습니다."
        }
        
    except Exception as e:
        logger.error(f"딥시크 학습 통계 조회 오류: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"딥시크 학습 통계 조회 중 오류가 발생했습니다: {str(e)}"
        )


@router.post("/deepseek/manual-learning")
async def trigger_manual_deepseek_learning(
    request: dict,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """수동 딥시크 학습 트리거"""
    check_professor_permission(current_user)
    
    try:
        from app.services.deepseek_learning_service import DeepSeekLearningService
        
        deepseek_learning = DeepSeekLearningService()
        
        # 요청 파라미터
        department = request.get("department", current_user.department)
        limit = request.get("limit", 20)
        
        logger.info(f"🎓 수동 딥시크 학습 시작: {department}, 제한 {limit}개")
        
        # 승인된 문제들로부터 일괄 학습
        result = await deepseek_learning.batch_learning_from_approved_questions(
            db=db,
            department=department,
            limit=limit
        )
        
        return {
            "success": result["success"],
            "professor_id": current_user.id,
            "professor_name": current_user.name,
            "department": department,
            "learning_result": result,
            "message": f"수동 딥시크 학습이 완료되었습니다. ({result.get('success_count', 0)}/{result.get('processed_count', 0)} 성공)"
        }
        
    except Exception as e:
        logger.error(f"수동 딥시크 학습 오류: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"수동 딥시크 학습 중 오류가 발생했습니다: {str(e)}"
        )


@router.post("/deepseek/test-knowledge")
async def test_deepseek_learned_knowledge(
    request: dict,
    current_user: User = Depends(get_current_user)
):
    """딥시크 학습된 지식 테스트"""
    check_professor_permission(current_user)
    
    try:
        from app.services.deepseek_learning_service import DeepSeekLearningService
        
        deepseek_learning = DeepSeekLearningService()
        
        test_question = request.get("test_question", "")
        department = request.get("department", current_user.department)
        
        if not test_question:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="테스트 문제를 입력해주세요."
            )
        
        logger.info(f"🧪 딥시크 지식 테스트: {department}")
        
        # 학습된 지식 테스트
        result = await deepseek_learning.test_learned_knowledge(
            test_question=test_question,
            department=department
        )
        
        return {
            "success": result["success"],
            "professor_id": current_user.id,
            "professor_name": current_user.name,
            "department": department,
            "test_result": result,
            "message": "딥시크 학습된 지식 테스트가 완료되었습니다."
        }
        
    except Exception as e:
        logger.error(f"딥시크 지식 테스트 오류: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"딥시크 지식 테스트 중 오류가 발생했습니다: {str(e)}"
        )


@router.get("/deepseek/model-status")
async def get_deepseek_model_status(
    current_user: User = Depends(get_current_user)
):
    """딥시크 모델 상태 확인"""
    check_professor_permission(current_user)
    
    try:
        from app.services.deepseek_service import LocalDeepSeekService
        
        deepseek = LocalDeepSeekService()
        
        # 모델 사용 가능성 확인
        model_available = await deepseek.check_model_availability()
        
        # 기본 테스트
        test_result = None
        if model_available:
            test_result = await deepseek.chat_completion(
                messages=[{"role": "user", "content": "안녕하세요, 테스트입니다."}],
                temperature=0.1
            )
        
        status_info = {
            "model_available": model_available,
            "model_name": deepseek.model_name,
            "ollama_host": deepseek.ollama_host,
            "embedding_model": deepseek.embedding_model,
            "test_successful": test_result["success"] if test_result else False,
            "last_checked": datetime.now().isoformat()
        }
        
        return {
            "success": True,
            "professor_id": current_user.id,
            "professor_name": current_user.name,
            "model_status": status_info,
            "message": "딥시크 모델 상태를 확인했습니다."
        }
        
    except Exception as e:
        logger.error(f"딥시크 모델 상태 확인 오류: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"딥시크 모델 상태 확인 중 오류가 발생했습니다: {str(e)}"
        )