"""
기존 학생들에게 활동 및 경고 데이터 추가
"""
from sqlalchemy.orm import Session
from app.db.database import get_db
from app.models.user import User
from app.models.analytics import StudentActivity, StudentWarning
from datetime import datetime, timedelta
import random

def add_student_activities():
    """기존 학생들에게 활동 데이터 추가"""
    db = next(get_db())
    
    # 홍길동 교수와 매칭된 학생들 조회
    professor = db.query(User).filter(User.user_id == "hgd123").first()
    students = db.query(User).filter(
        User.role == "student",
        User.school == professor.school,
        User.department == professor.department
    ).all()
    
    print(f"활동 데이터를 추가할 학생 수: {len(students)}명")
    
    # 기존 활동 데이터 삭제 (중복 방지)
    for student in students:
        db.query(StudentActivity).filter(StudentActivity.student_id == student.id).delete()
        db.query(StudentWarning).filter(StudentWarning.student_id == student.id).delete()
    
    db.commit()
    print("기존 활동/경고 데이터 삭제 완료")
    
    # 새로운 활동 데이터 생성
    for student in students:
        print(f"학생 {student.name} ({student.user_id}) 활동 데이터 생성 중...")
        
        # 최근 30일간 랜덤 활동 생성
        activity_count = random.randint(15, 40)
        for i in range(activity_count):
            activity_date = datetime.now() - timedelta(days=random.randint(0, 30))
            
            activity = StudentActivity(
                student_id=student.id,
                activity_type=random.choice([
                    "login", "assignment_submit", "quiz_complete", 
                    "video_watch", "discussion_post", "file_download",
                    "lecture_attend", "material_download", "forum_post"
                ]),
                activity_description=f"{student.name} 학습 활동 - {random.choice(['강의 수강', '과제 제출', '퀴즈 응시', '자료 다운로드', '토론 참여'])}",
                activity_date=activity_date.date(),
                time_spent_minutes=random.randint(10, 180),
                created_at=activity_date
            )
            
            db.add(activity)
        
        print(f"  - {activity_count}개의 활동 생성")
    
    # 일부 학생에게 경고 추가 (30% 확률)
    warning_student_count = max(1, int(len(students) * 0.3))
    warning_students = random.sample(students, k=warning_student_count)
    
    print(f"\n경고 데이터를 추가할 학생 수: {len(warning_students)}명")
    
    for student in warning_students:
        warning_count = random.randint(1, 3)
        
        for i in range(warning_count):
            warning = StudentWarning(
                student_id=student.id,
                professor_id=professor.id,
                warning_type=random.choice([
                    "attendance", "assignment_delay", "low_grade", 
                    "behavior", "system_abuse", "participation"
                ]),
                severity=random.choice(["low", "medium", "high", "critical"]),
                title=f"{student.name} 학습 관련 경고",
                description=random.choice([
                    "출석률 저조로 인한 경고",
                    "과제 제출 지연이 반복됨",
                    "성적이 기준점 이하로 떨어짐",
                    "온라인 수업 참여도 부족",
                    "토론 참여가 소극적임"
                ]),
                is_resolved=random.choice([True, False, False]),  # 70% 확률로 미해결
                created_at=datetime.now() - timedelta(days=random.randint(1, 20))
            )
            
            db.add(warning)
        
        print(f"  - {student.name}: {warning_count}개의 경고 생성")
    
    db.commit()
    print(f"\n총 {len(students)}명의 학생에게 활동 및 경고 데이터가 추가되었습니다!")
    
    # 결과 확인
    print("\n=== 생성된 데이터 요약 ===")
    for student in students:
        activity_count = db.query(StudentActivity).filter(StudentActivity.student_id == student.id).count()
        warning_count = db.query(StudentWarning).filter(
            StudentWarning.student_id == student.id,
            StudentWarning.is_resolved == False
        ).count()
        
        last_activity = db.query(StudentActivity).filter(
            StudentActivity.student_id == student.id
        ).order_by(StudentActivity.created_at.desc()).first()
        
        last_activity_date = last_activity.created_at.strftime("%Y-%m-%d %H:%M") if last_activity else "없음"
        
        print(f"- {student.name} ({student.user_id}): 활동 {activity_count}건, 미해결 경고 {warning_count}건, 최근활동 {last_activity_date}")

if __name__ == "__main__":
    add_student_activities() 