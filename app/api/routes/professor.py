"""
교수용 API 엔드포인트
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, func, desc
from typing import List, Optional
from datetime import datetime, date, timedelta
from pydantic import BaseModel, Field
import random

from app.db.database import get_db
from app.models.user import User
from app.models.assignment import Assignment, AssignmentSubmission, AssignmentStatus, AssignmentType, ProblemBank
from app.models.analytics import StudentActivity, StudentWarning, LearningAnalytics, ProfessorDashboardData
from app.auth.dependencies import get_current_user

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
    description: str = Field(..., min_length=1)
    assignment_type: str = Field(..., pattern="^(homework|project|quiz|exam)$")
    subject_name: str = Field(..., min_length=1, max_length=100)
    due_date: Optional[datetime] = None
    max_score: int = Field(..., gt=0, le=1000)
    allow_late_submission: bool = False
    instructions: Optional[str] = None

class StudentResponse(BaseModel):
    students: List[dict]

class AssignmentListResponse(BaseModel):
    assignments: List[dict]
    total_count: int

class ProblemCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=200)
    question_text: str = Field(..., min_length=1)
    question_type: str = Field(..., pattern="^(multiple_choice|short_answer|essay|true_false)$") 
    options: Optional[List[str]] = None
    correct_answer: str = Field(..., min_length=1)
    difficulty: str = Field(..., pattern="^(easy|medium|hard)$")
    subject: str = Field(..., min_length=1, max_length=100)
    tags: Optional[List[str]] = None

class ProblemListResponse(BaseModel):
    problems: List[dict]
    total_count: int

# ===== 헬퍼 함수들 =====

def check_professor_permission(user: User):
    """교수 권한 확인"""
    if user.role != "professor":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="교수 권한이 필요합니다"
        )

def get_professor_students(db: Session, professor: User) -> List[User]:
    """교수가 담당하는 학생들 조회 (같은 학교, 같은 학과)"""
    return db.query(User).filter(
        and_(
            User.role == "student",
            User.school == professor.school,
            User.department == professor.department
        )
    ).all()

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

@router.get("/students", response_model=StudentResponse)
async def get_professor_students_list(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """교수가 담당하는 학생 목록 조회"""
    check_professor_permission(current_user)
    
    students = get_professor_students(db, current_user)
    student_list = []
    
    for student in students:
        # 경고 개수 조회
        warning_count = db.query(StudentWarning).filter(
            and_(
                StudentWarning.student_id == student.id,
                StudentWarning.is_resolved == False
            )
        ).count()
        
        # 최근 활동 조회
        last_activity = db.query(StudentActivity).filter(
            StudentActivity.student_id == student.id
        ).order_by(desc(StudentActivity.created_at)).first()
        
        student_list.append({
            "id": student.id,
            "name": student.name,
            "user_id": student.user_id,
            "email": student.email,
            "warning_count": warning_count,
            "last_activity": last_activity.created_at.isoformat() if last_activity else None
        })
    
    return StudentResponse(students=student_list)

@router.post("/assignments")
async def create_assignment(
    assignment_data: AssignmentCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """새 과제 생성"""
    check_professor_permission(current_user)
    
    # AssignmentType enum 값으로 변환
    try:
        assignment_type = AssignmentType(assignment_data.assignment_type)
    except ValueError:
        raise HTTPException(status_code=400, detail="유효하지 않은 과제 유형입니다")
    
    # 새 과제 생성
    new_assignment = Assignment(
        title=assignment_data.title,
        description=assignment_data.description,
        assignment_type=assignment_type,
        subject_name=assignment_data.subject_name,
        professor_id=current_user.id,
        due_date=assignment_data.due_date,
        max_score=assignment_data.max_score,
        allow_late_submission=assignment_data.allow_late_submission,
        instructions=assignment_data.instructions,
        status=AssignmentStatus.draft  # 기본값: 초안
    )
    
    db.add(new_assignment)
    db.commit()
    db.refresh(new_assignment)
    
    return {
        "message": "과제가 성공적으로 생성되었습니다",
        "assignment_id": new_assignment.id
    }

@router.get("/assignments", response_model=AssignmentListResponse)
async def get_professor_assignments(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    page: int = 1,
    size: int = 10
):
    """교수의 과제 목록 조회"""
    check_professor_permission(current_user)
    
    # 페이지네이션
    offset = (page - 1) * size
    
    # 과제 조회
    assignments_query = db.query(Assignment).filter(
        Assignment.professor_id == current_user.id
    ).order_by(desc(Assignment.created_at))
    
    total_count = assignments_query.count()
    assignments = assignments_query.offset(offset).limit(size).all()
    
    assignment_list = []
    for assignment in assignments:
        # 제출 통계
        total_submissions = db.query(AssignmentSubmission).filter(
            AssignmentSubmission.assignment_id == assignment.id
        ).count()
        
        graded_submissions = db.query(AssignmentSubmission).filter(
            and_(
                AssignmentSubmission.assignment_id == assignment.id,
                AssignmentSubmission.score.is_not(None)
            )
        ).count()
        
        assignment_list.append({
            "id": assignment.id,
            "title": assignment.title,
            "assignment_type": assignment.assignment_type.value,
            "status": assignment.status.value,
            "subject_name": assignment.subject_name,
            "due_date": assignment.due_date.isoformat() if assignment.due_date else None,
            "max_score": assignment.max_score,
            "total_submissions": total_submissions,
            "graded_submissions": graded_submissions,
            "created_at": assignment.created_at.isoformat()
        })
    
    return AssignmentListResponse(
        assignments=assignment_list,
        total_count=total_count
    )

@router.post("/problems")
async def create_problem(
    problem_data: ProblemCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """새 문제 생성"""
    check_professor_permission(current_user)
    
    # 새 문제 생성
    new_problem = ProblemBank(
        title=problem_data.title,
        question_text=problem_data.question_text,
        question_type=problem_data.question_type,
        options=problem_data.options,
        correct_answer=problem_data.correct_answer,
        difficulty=problem_data.difficulty,
        subject=problem_data.subject,
        tags=problem_data.tags,
        created_by=current_user.id
    )
    
    db.add(new_problem)
    db.commit()
    db.refresh(new_problem)
    
    return {
        "message": "문제가 성공적으로 생성되었습니다",
        "problem_id": new_problem.id
    }

@router.get("/problems", response_model=ProblemListResponse)
async def get_professor_problems(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    page: int = 1,
    size: int = 10
):
    """교수가 생성한 문제 목록 조회"""
    check_professor_permission(current_user)
    
    # 페이지네이션
    offset = (page - 1) * size
    
    # 문제 조회
    problems_query = db.query(ProblemBank).filter(
        ProblemBank.created_by == current_user.id
    ).order_by(desc(ProblemBank.created_at))
    
    total_count = problems_query.count()
    problems = problems_query.offset(offset).limit(size).all()
    
    problem_list = []
    for problem in problems:
        problem_list.append({
            "id": problem.id,
            "title": problem.title,
            "question_type": problem.question_type,
            "difficulty": problem.difficulty,
            "subject": problem.subject,
            "usage_count": problem.usage_count,
            "created_at": problem.created_at.isoformat()
        })
    
    return ProblemListResponse(
        problems=problem_list,
        total_count=total_count
    )

# ===== 새로운 분석 API들 =====

@router.get("/analytics")
async def get_learning_analytics(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """학습 분석 데이터 조회"""
    try:
        if current_user.role != "professor":
            raise HTTPException(status_code=403, detail="교수 권한이 필요합니다")
        
        # 같은 학교+학과 학생들 조회
        students = db.query(User).filter(
            User.role == "student",
            User.school == current_user.school,
            User.department == current_user.department
        ).all()
        
        student_ids = [s.id for s in students]
        
        # 학생별 성과 분석
        student_performance = []
        for student in students:
            activities = db.query(StudentActivity).filter(
                StudentActivity.student_id == student.id
            ).all()
            
            warnings = db.query(StudentWarning).filter(
                StudentWarning.student_id == student.id,
                StudentWarning.is_resolved == False
            ).count()
            
            # 최근 30일 활동
            recent_activities = len([a for a in activities if 
                (datetime.now().date() - a.activity_date).days <= 30])
            
            # 평균 점수 계산
            scores = [a.score for a in activities if a.score is not None]
            avg_score = sum(scores) / len(scores) if scores else 0
            
            # 총 학습 시간
            total_time = sum(a.time_spent_minutes for a in activities if a.time_spent_minutes)
            
            student_performance.append({
                "student_id": student.id,
                "name": student.name,
                "user_id": student.user_id,
                "total_activities": len(activities),
                "recent_activities": recent_activities,
                "avg_score": round(avg_score, 2),
                "total_study_time": total_time,
                "warning_count": warnings,
                "performance_level": "high" if avg_score >= 80 else "medium" if avg_score >= 60 else "low"
            })
        
        # 과목별 통계 (모의 데이터)
        subject_stats = [
            {"subject": "데이터베이스", "avg_score": 78.5, "completion_rate": 92, "students": len(students)},
            {"subject": "알고리즘", "avg_score": 72.3, "completion_rate": 85, "students": len(students)},
            {"subject": "웹프로그래밍", "avg_score": 83.7, "completion_rate": 96, "students": len(students)},
            {"subject": "머신러닝", "avg_score": 69.8, "completion_rate": 78, "students": len(students)}
        ]
        
        # 시간대별 활동 분석
        hourly_activity = {}
        for hour in range(24):
            hourly_activity[hour] = 0
            
        for student_id in student_ids:
            activities = db.query(StudentActivity).filter(
                StudentActivity.student_id == student_id
            ).all()
            
            for activity in activities:
                hour = activity.created_at.hour
                hourly_activity[hour] += 1
        
        # 성적 분포
        all_scores = []
        for student_id in student_ids:
            activities = db.query(StudentActivity).filter(
                StudentActivity.student_id == student_id,
                StudentActivity.score.isnot(None)
            ).all()
            all_scores.extend([a.score for a in activities])
        
        score_distribution = {
            "90-100": len([s for s in all_scores if s >= 90]),
            "80-89": len([s for s in all_scores if 80 <= s < 90]),
            "70-79": len([s for s in all_scores if 70 <= s < 80]),
            "60-69": len([s for s in all_scores if 60 <= s < 70]),
            "0-59": len([s for s in all_scores if s < 60])
        }
        
        # 학습 패턴 분석 (요일별)
        weekly_pattern = {day: 0 for day in ["월", "화", "수", "목", "금", "토", "일"]}
        for student_id in student_ids:
            activities = db.query(StudentActivity).filter(
                StudentActivity.student_id == student_id
            ).all()
            
            for activity in activities:
                weekday = activity.activity_date.weekday()
                day_names = ["월", "화", "수", "목", "금", "토", "일"]
                weekly_pattern[day_names[weekday]] += 1
        
        return {
            "student_performance": student_performance,
            "subject_stats": subject_stats,
            "hourly_activity": hourly_activity,
            "score_distribution": score_distribution,
            "weekly_pattern": weekly_pattern,
            "summary": {
                "total_students": len(students),
                "avg_class_score": round(sum(p["avg_score"] for p in student_performance) / len(student_performance), 2) if student_performance else 0,
                "high_performers": len([p for p in student_performance if p["performance_level"] == "high"]),
                "at_risk_students": len([p for p in student_performance if p["warning_count"] > 0])
            }
        }
        
    except Exception as e:
        print(f"학습 분석 조회 오류: {e}")
        raise HTTPException(status_code=500, detail="학습 분석 데이터 조회 실패")

@router.get("/monitoring")
async def get_student_monitoring(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """실시간 학생 모니터링 데이터"""
    try:
        if current_user.role != "professor":
            raise HTTPException(status_code=403, detail="교수 권한이 필요합니다")
        
        # 같은 학교+학과 학생들 조회
        students = db.query(User).filter(
            User.role == "student",
            User.school == current_user.school,
            User.department == current_user.department
        ).all()
        
        monitoring_data = []
        alerts = []
        
        for student in students:
            # 최근 활동
            recent_activity = db.query(StudentActivity).filter(
                StudentActivity.student_id == student.id
            ).order_by(StudentActivity.created_at.desc()).first()
            
            # 경고 사항
            warnings = db.query(StudentWarning).filter(
                StudentWarning.student_id == student.id,
                StudentWarning.is_resolved == False
            ).all()
            
            # 출석률 계산 (최근 30일 기준)
            thirty_days_ago = datetime.now() - timedelta(days=30)
            login_activities = db.query(StudentActivity).filter(
                StudentActivity.student_id == student.id,
                StudentActivity.activity_type == "login",
                StudentActivity.created_at >= thirty_days_ago
            ).count()
            
            attendance_rate = min(100, (login_activities / 30) * 100)
            
            # 학습 상태 판정
            status = "normal"
            if len(warnings) > 2:
                status = "critical"
            elif len(warnings) > 0 or attendance_rate < 70:
                status = "warning"
            elif recent_activity and (datetime.now() - recent_activity.created_at).days > 7:
                status = "inactive"
            
            # 실시간 상태 (모의 데이터)
            is_online = random.choice([True, False])
            current_activity = random.choice(["강의 수강", "과제 작성", "자료 다운로드", "오프라인"]) if is_online else "오프라인"
            
            student_data = {
                "student_id": student.id,
                "name": student.name,
                "user_id": student.user_id,
                "status": status,
                "is_online": is_online,
                "current_activity": current_activity,
                "attendance_rate": round(attendance_rate, 1),
                "warning_count": len(warnings),
                "last_activity": recent_activity.created_at.isoformat() if recent_activity else None,
                "last_login": recent_activity.created_at.isoformat() if recent_activity and recent_activity.activity_type == "login" else None
            }
            
            monitoring_data.append(student_data)
            
            # 알림 생성
            if status == "critical":
                alerts.append({
                    "type": "critical",
                    "student": student.name,
                    "message": f"{student.name} 학생이 심각한 경고 상태입니다.",
                    "timestamp": datetime.now().isoformat()
                })
            elif status == "warning":
                alerts.append({
                    "type": "warning", 
                    "student": student.name,
                    "message": f"{student.name} 학생의 출석률이 {attendance_rate:.1f}%로 저조합니다.",
                    "timestamp": datetime.now().isoformat()
                })
        
        # 전체 통계
        total_online = len([s for s in monitoring_data if s["is_online"]])
        avg_attendance = sum(s["attendance_rate"] for s in monitoring_data) / len(monitoring_data) if monitoring_data else 0
        
        return {
            "students": monitoring_data,
            "alerts": alerts[:10],  # 최근 10개 알림
            "summary": {
                "total_students": len(students),
                "online_students": total_online,
                "offline_students": len(students) - total_online,
                "avg_attendance_rate": round(avg_attendance, 1),
                "critical_students": len([s for s in monitoring_data if s["status"] == "critical"]),
                "warning_students": len([s for s in monitoring_data if s["status"] == "warning"])
            }
        }
        
    except Exception as e:
        print(f"학생 모니터링 조회 오류: {e}")
        raise HTTPException(status_code=500, detail="모니터링 데이터 조회 실패")

@router.get("/reports")
async def get_reports_data(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """리포트 생성을 위한 데이터"""
    try:
        if current_user.role != "professor":
            raise HTTPException(status_code=403, detail="교수 권한이 필요합니다")
        
        # 같은 학교+학과 학생들 조회
        students = db.query(User).filter(
            User.role == "student",
            User.school == current_user.school,
            User.department == current_user.department
        ).all()
        
        # 기간별 성과 분석 (최근 6개월)
        monthly_performance = []
        for i in range(6):
            month_start = datetime.now().replace(day=1) - timedelta(days=30*i)
            month_end = month_start + timedelta(days=30)
            
            month_activities = 0
            month_scores = []
            
            for student in students:
                activities = db.query(StudentActivity).filter(
                    StudentActivity.student_id == student.id,
                    StudentActivity.created_at >= month_start,
                    StudentActivity.created_at < month_end
                ).all()
                
                month_activities += len(activities)
                month_scores.extend([a.score for a in activities if a.score is not None])
            
            avg_score = sum(month_scores) / len(month_scores) if month_scores else 0
            
            monthly_performance.append({
                "month": month_start.strftime("%Y-%m"),
                "activities": month_activities,
                "avg_score": round(avg_score, 2),
                "students_active": len([s for s in students if 
                    db.query(StudentActivity).filter(
                        StudentActivity.student_id == s.id,
                        StudentActivity.created_at >= month_start,
                        StudentActivity.created_at < month_end
                    ).first() is not None
                ])
            })
        
        # 과제별 성과
        assignments = db.query(Assignment).filter(
            Assignment.professor_id == current_user.id
        ).all()
        
        assignment_performance = []
        for assignment in assignments:
            submissions = db.query(AssignmentSubmission).filter(
                AssignmentSubmission.assignment_id == assignment.id,
                AssignmentSubmission.score.isnot(None)
            ).all()
            
            if submissions:
                scores = [s.score for s in submissions]
                assignment_performance.append({
                    "assignment_title": assignment.title,
                    "assignment_type": assignment.assignment_type.value,
                    "total_submissions": len(submissions),
                    "avg_score": round(sum(scores) / len(scores), 2),
                    "max_score": max(scores),
                    "min_score": min(scores),
                    "completion_rate": round((len(submissions) / len(students)) * 100, 2) if students else 0
                })
        
        # 학과 비교 데이터 (모의 데이터)
        department_comparison = [
            {"department": "빅데이터과", "avg_score": 78.5, "attendance": 92, "is_current": True},
            {"department": "컴퓨터공학과", "avg_score": 75.2, "attendance": 89, "is_current": False},
            {"department": "정보보안과", "avg_score": 80.1, "attendance": 94, "is_current": False},
            {"department": "AI소프트웨어과", "avg_score": 82.3, "attendance": 91, "is_current": False}
        ]
        
        # 개별 학생 상세 리포트
        student_reports = []
        for student in students:
            activities = db.query(StudentActivity).filter(
                StudentActivity.student_id == student.id
            ).all()
            
            warnings = db.query(StudentWarning).filter(
                StudentWarning.student_id == student.id
            ).all()
            
            scores = [a.score for a in activities if a.score is not None]
            total_time = sum(a.time_spent_minutes for a in activities if a.time_spent_minutes)
            
            student_reports.append({
                "student_id": student.id,
                "name": student.name,
                "user_id": student.user_id,
                "total_activities": len(activities),
                "avg_score": round(sum(scores) / len(scores), 2) if scores else 0,
                "total_study_time": total_time,
                "total_warnings": len(warnings),
                "unresolved_warnings": len([w for w in warnings if not w.is_resolved]),
                "activity_trend": "increasing" if len(activities) > 10 else "stable" if len(activities) > 5 else "decreasing",
                "performance_ranking": 0  # 나중에 계산
            })
        
        # 성과 순위 계산
        student_reports.sort(key=lambda x: x["avg_score"], reverse=True)
        for i, report in enumerate(student_reports):
            report["performance_ranking"] = i + 1
        
        return {
            "monthly_performance": monthly_performance,
            "assignment_performance": assignment_performance,
            "department_comparison": department_comparison,
            "student_reports": student_reports,
            "summary": {
                "report_generated_at": datetime.now().isoformat(),
                "total_students": len(students),
                "total_assignments": len(assignments),
                "class_avg_score": round(sum(r["avg_score"] for r in student_reports) / len(student_reports), 2) if student_reports else 0,
                "department_rank": 2,  # 학과 순위 (모의)
                "school_rank": 3       # 학교 순위 (모의)
            }
        }
        
    except Exception as e:
        print(f"리포트 데이터 조회 오류: {e}")
        raise HTTPException(status_code=500, detail="리포트 데이터 조회 실패") 