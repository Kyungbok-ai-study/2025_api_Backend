#!/usr/bin/env python3
"""
교수 대시보드용 샘플 데이터 생성 스크립트
"""

from sqlalchemy.orm import sessionmaker
from app.db.database import engine
from app.models.assignment import Assignment, AssignmentSubmission, AssignmentStatus, AssignmentType, ProblemBank
from app.models.analytics import StudentActivity, StudentWarning, LearningAnalytics
from app.models.user import User
from datetime import datetime, date, timedelta
import random

Session = sessionmaker(bind=engine)
session = Session()

def create_sample_data():
    try:
        print("📋 샘플 데이터 생성 시작...")
        
        # 교수와 학생 정보 가져오기
        professors = session.query(User).filter(User.role == 'professor').all()
        students = session.query(User).filter(User.role == 'student').all()
        
        print(f"🎓 교수 {len(professors)}명, 학생 {len(students)}명 발견")
        
        if not professors:
            print("❌ 교수가 없습니다.")
            return
            
        if not students:
            print("❌ 학생이 없습니다.")
            return
        
        # 경복대학교 빅데이터과 교수와 학생들로 필터링
        kb_professors = [p for p in professors if p.school == '경복대학교' and p.department == '빅데이터과']
        kb_students = [s for s in students if s.school == '경복대학교' and s.department == '빅데이터과']
        
        print(f"🏫 경복대학교 빅데이터과: 교수 {len(kb_professors)}명, 학생 {len(kb_students)}명")
        
        if not kb_professors:
            print("❌ 경복대학교 빅데이터과 교수가 없습니다.")
            return
        
        professor = kb_professors[0]  # 첫 번째 교수 사용
        print(f"👨‍🏫 샘플 데이터 생성 대상 교수: {professor.name} ({professor.user_id})")
        
        # 1. 과제 생성
        subjects = ['자료구조', '알고리즘', '데이터베이스', '웹프로그래밍', '파이썬프로그래밍']
        assignment_types = [AssignmentType.HOMEWORK, AssignmentType.PROJECT, AssignmentType.QUIZ]
        
        assignments = []
        for i in range(10):
            assignment = Assignment(
                title=f"{random.choice(subjects)} 과제 {i+1}",
                description=f"과제 {i+1}에 대한 설명입니다.",
                assignment_type=random.choice(assignment_types),
                status=random.choice([AssignmentStatus.PUBLISHED, AssignmentStatus.CLOSED, AssignmentStatus.GRADED]),
                professor_id=professor.id,
                professor_school=professor.school,
                professor_department=professor.department,
                subject_name=random.choice(subjects),
                created_at=datetime.now() - timedelta(days=random.randint(1, 30)),
                due_date=datetime.now() + timedelta(days=random.randint(1, 14)),
                max_score=100.0
            )
            assignments.append(assignment)
        
        session.add_all(assignments)
        session.commit()
        print(f"✅ 과제 {len(assignments)}개 생성 완료")
        
        # 2. 과제 제출 기록 생성
        submissions = []
        for assignment in assignments:
            # 일부 학생들만 제출
            submitted_students = random.sample(kb_students, min(len(kb_students), random.randint(3, 7)))
            
            for student in submitted_students:
                score = random.randint(60, 100) if random.random() > 0.3 else None  # 30%는 미채점
                submission = AssignmentSubmission(
                    assignment_id=assignment.id,
                    student_id=student.id,
                    submission_text=f"{student.name}의 {assignment.title} 제출물",
                    submitted_at=assignment.created_at + timedelta(days=random.randint(1, 7)),
                    score=score,
                    feedback="잘 작성되었습니다." if score else None,
                    graded_at=datetime.now() - timedelta(days=random.randint(1, 5)) if score else None
                )
                submissions.append(submission)
        
        session.add_all(submissions)
        session.commit()
        print(f"✅ 과제 제출 기록 {len(submissions)}개 생성 완료")
        
        # 3. 학생 활동 기록 생성
        activities = []
        for student in kb_students:
            # 최근 30일 동안의 활동 생성
            for day in range(30):
                activity_date = date.today() - timedelta(days=day)
                
                # 무작위로 활동 생성 (일부 날짜는 활동 없음)
                if random.random() > 0.3:  # 70% 확률로 활동 있음
                    activity_count = random.randint(1, 5)
                    for _ in range(activity_count):
                        activity = StudentActivity(
                            student_id=student.id,
                            activity_type=random.choice(['login', 'assignment_submit', 'test_take', 'study']),
                            activity_description=f"{student.name}의 학습 활동",
                            activity_date=activity_date,
                            score=random.randint(70, 100) if random.random() > 0.5 else None,
                            time_spent_minutes=random.randint(10, 120),
                            created_at=datetime.combine(activity_date, datetime.min.time()) + timedelta(hours=random.randint(8, 22))
                        )
                        activities.append(activity)
        
        session.add_all(activities)
        session.commit()
        print(f"✅ 학생 활동 기록 {len(activities)}개 생성 완료")
        
        # 4. 경고 시스템 데이터 생성
        warnings = []
        warning_students = random.sample(kb_students, min(len(kb_students), 3))  # 일부 학생에게만 경고
        
        warning_types = [
            ('missing_assignment', 'high', '연속 3회 과제 미제출'),
            ('low_score', 'medium', '평균 점수 50점 이하'),
            ('no_activity', 'medium', '5일 이상 로그인 안함')
        ]
        
        for i, student in enumerate(warning_students):
            warning_type, severity, description = warning_types[i % len(warning_types)]
            warning = StudentWarning(
                student_id=student.id,
                professor_id=professor.id,
                warning_type=warning_type,
                severity=severity,
                title=f"{student.name} 학습 경고",
                description=description,
                created_at=datetime.now() - timedelta(days=random.randint(1, 7))
            )
            warnings.append(warning)
        
        session.add_all(warnings)
        session.commit()
        print(f"✅ 학습 경고 {len(warnings)}개 생성 완료")
        
        # 5. 문제 은행 데이터 생성
        problems = []
        problem_types = ['multiple_choice', 'short_answer', 'essay', 'true_false']
        
        for i in range(15):
            problem = ProblemBank(
                title=f"{random.choice(subjects)} 문제 {i+1}",
                content=f"이것은 {random.choice(subjects)} 관련 문제입니다. 다음 중 올바른 답을 선택하세요.",
                problem_type=random.choice(problem_types),
                subject=random.choice(subjects),
                difficulty=random.randint(1, 5),
                correct_answer="A" if random.choice(problem_types) == 'multiple_choice' else "정답입니다",
                choices=['선택지 1', '선택지 2', '선택지 3', '선택지 4'] if random.choice(problem_types) == 'multiple_choice' else None,
                explanation="이 문제의 정답은 다음과 같은 이유로 결정됩니다...",
                created_by=professor.id,
                school=professor.school,
                department=professor.department,
                usage_count=random.randint(0, 10)
            )
            problems.append(problem)
        
        session.add_all(problems)
        session.commit()
        print(f"✅ 문제 은행 {len(problems)}개 생성 완료")
        
        print("\n🎉 모든 샘플 데이터 생성 완료!")
        print(f"📊 생성된 데이터 요약:")
        print(f"   - 과제: {len(assignments)}개")
        print(f"   - 과제 제출: {len(submissions)}개")
        print(f"   - 학생 활동: {len(activities)}개")
        print(f"   - 학습 경고: {len(warnings)}개")
        print(f"   - 문제 은행: {len(problems)}개")
        
    except Exception as e:
        print(f"❌ 샘플 데이터 생성 중 오류 발생: {e}")
        import traceback
        traceback.print_exc()
        session.rollback()
    finally:
        session.close()

if __name__ == "__main__":
    create_sample_data() 