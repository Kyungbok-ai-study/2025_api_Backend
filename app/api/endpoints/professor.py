"""
교수용 API 엔드포인트
"""
from fastapi import APIRouter, Depends, HTTPException, status, File, UploadFile
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
from app.api.endpoints.auth import get_current_user
from app.schemas.question_upload import (
    QuestionUploadResponse, 
    AnswerUploadResponse,
    ParseAndMatchRequest,
    ParseAndMatchResponse
)
from app.services.question_service import process_files_with_gemini_parser
from app.services.question_parser import QuestionParser
import os
import shutil
from pathlib import Path
import json

router = APIRouter(prefix="/professor", tags=["professor"])

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
        
        # Gemini로 파싱
        parser = QuestionParser(api_key=settings.GEMINI_API_KEY)
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
        
        # Gemini로 파싱
        parser = QuestionParser(api_key=settings.GEMINI_API_KEY)
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
        # 문제-정답 매칭 및 저장 (새로운 함수 사용)
        result = process_files_with_gemini_parser(
            db=db,
            question_file_path=str(question_path),
            answer_file_path=str(answer_path),
            source_name=request.source_name,
            create_embeddings=request.create_embeddings,
            user_id=current_user.id,
            gemini_api_key=request.gemini_api_key or os.getenv("GEMINI_API_KEY")
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