#!/usr/bin/env python3
"""
실제 진단테스트 활동 데이터가 포함된 테스트 데이터베이스 생성
새벽 시간대 진단테스트 활동 등 실제 시나리오 포함
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from datetime import datetime, timedelta
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.database import Base
from app.models.user import User
from app.models.professor_student_match import ProfessorStudentMatch, StudentDiagnosisAlert
from app.models.unified_diagnosis import DiagnosisSession, DiagnosisTest, DiagnosisQuestion

# DB 설정
DATABASE_URL = "sqlite:///./test_monitoring.db"
engine = create_engine(DATABASE_URL, echo=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def create_test_database():
    """테스트 데이터베이스 생성"""
    print("🚀 테스트 데이터베이스 생성 시작...")
    
    # 테이블 생성
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    
    try:
        # 1. 기존 데이터 정리
        print("📝 기존 데이터 정리...")
        db.query(StudentDiagnosisAlert).delete()
        db.query(DiagnosisSession).delete()
        db.query(ProfessorStudentMatch).delete()
        db.query(DiagnosisQuestion).delete()
        db.query(DiagnosisTest).delete()
        db.query(User).delete()
        db.commit()
        
        # 2. 교수 계정 생성
        print("👨‍🏫 교수 계정 생성...")
        professors = [
            {
                "user_id": "prof_physics",
                "password": "password123",
                "name": "김교수",
                "school": "경복대학교",
                "department": "물리치료학과",
                "role": "professor"
            },
            {
                "user_id": "prof_nursing", 
                "password": "password123",
                "name": "이교수",
                "school": "경복대학교", 
                "department": "간호학과",
                "role": "professor"
            },
            {
                "user_id": "prof_ot",
                "password": "password123", 
                "name": "박교수",
                "school": "경복대학교",
                "department": "작업치료학과", 
                "role": "professor"
            }
        ]
        
        prof_objects = []
        for prof_data in professors:
            prof = User(
                user_id=prof_data["user_id"],
                password=prof_data["password"],  # 실제로는 해시 필요
                name=prof_data["name"],
                school=prof_data["school"],
                department=prof_data["department"],
                role=prof_data["role"],
                is_active=True,
                profile_info={"title": "교수", "expertise": prof_data["department"]}
            )
            db.add(prof)
            prof_objects.append(prof)
        
        # 3. 학생 계정 생성
        print("🎓 학생 계정 생성...")
        students = [
            {
                "user_id": "physics_student",
                "password": "password123",
                "name": "물리치료 학생",
                "school": "경복대학교",
                "department": "물리치료학과",
                "role": "student"
            },
            {
                "user_id": "nursing_student",
                "password": "password123",
                "name": "간호학 학생", 
                "school": "경복대학교",
                "department": "간호학과",
                "role": "student"
            },
            {
                "user_id": "ot_student",
                "password": "password123",
                "name": "작업치료 학생",
                "school": "경복대학교", 
                "department": "작업치료학과",
                "role": "student"
            },
            {
                "user_id": "night_active_student",
                "password": "password123",
                "name": "새벽활동 학생",
                "school": "경복대학교",
                "department": "물리치료학과", 
                "role": "student"
            }
        ]
        
        student_objects = []
        for student_data in students:
            student = User(
                user_id=student_data["user_id"],
                password=student_data["password"],  # 실제로는 해시 필요
                name=student_data["name"],
                school=student_data["school"],
                department=student_data["department"],
                role=student_data["role"],
                is_active=True,
                profile_info={"year": "2학년", "student_id": student_data["user_id"]}
            )
            db.add(student)
            student_objects.append(student)
        
        db.commit()
        print(f"✅ 교수 {len(prof_objects)}명, 학생 {len(student_objects)}명 생성 완료")
        
        # 4. 진단테스트 생성
        print("📋 진단테스트 생성...")
        diagnosis_test = DiagnosisTest(
            title="물리치료학과 종합진단테스트",
            description="물리치료사 국가고시 기반 진단테스트",
            department="물리치료학과",
            subject_area="물리치료",
            total_questions=30,
            time_limit_minutes=60,
            difficulty_level="mixed",
            is_active=True,
            test_metadata={
                "version": "2024.1",
                "category": "comprehensive",
                "exam_type": "national_exam_based"
            }
        )
        db.add(diagnosis_test)
        db.commit()
        
        # 5. 진단테스트 세션 생성 (실제 활동 데이터)
        print("🔬 진단테스트 세션 생성...")
        
        # 새벽 활동 학생 - 새벽 시간대에 8회 테스트
        night_student = student_objects[3]  # night_active_student
        physics_student = student_objects[0]  # physics_student
        
        # 새벽 활동 세션들 (00:00-06:00)
        night_sessions = []
        for i in range(8):
            night_time = datetime.now() - timedelta(hours=i*2 + 1)  # 새벽 시간대
            night_time = night_time.replace(hour=i % 6, minute=30)  # 새벽 0-5시
            
            session = DiagnosisSession(
                test_id=diagnosis_test.id,
                user_id=night_student.id,
                session_token=f"night_session_{i}_{night_student.id}",
                attempt_number=i + 1,
                status="completed",
                started_at=night_time,
                completed_at=night_time + timedelta(minutes=45),
                total_time_spent=45 * 60,  # 45분
                raw_score=25 + (i % 5),  # 25-29점 변동
                percentage_score=83.3 + (i % 5) * 2,  # 83-91% 변동
                response_stats={
                    "total_questions": 30,
                    "answered": 30,
                    "correct": 25 + (i % 5),
                    "incorrect": 5 - (i % 5),
                    "skipped": 0,
                    "average_time_per_question": 90
                },
                diagnosis_result={
                    "overall_level": "good",
                    "level_score": 85 + (i % 5),
                    "strengths": ["해부학", "생리학"],
                    "weaknesses": ["병리학"],
                    "recommendations": ["병리학 추가 학습 필요"]
                }
            )
            db.add(session)
            night_sessions.append(session)
        
        # 일반 학생 세션들 (주간 활동)
        day_sessions = []
        for i in range(5):
            day_time = datetime.now() - timedelta(days=i, hours=2)
            day_time = day_time.replace(hour=14 + i % 3, minute=0)  # 오후 시간대
            
            session = DiagnosisSession(
                test_id=diagnosis_test.id,
                user_id=physics_student.id,
                session_token=f"day_session_{i}_{physics_student.id}",
                attempt_number=i + 1,
                status="completed",
                started_at=day_time,
                completed_at=day_time + timedelta(minutes=50),
                total_time_spent=50 * 60,
                raw_score=22 + i,
                percentage_score=73.3 + i * 3,
                response_stats={
                    "total_questions": 30,
                    "answered": 29,
                    "correct": 22 + i,
                    "incorrect": 7 - i,
                    "skipped": 1,
                    "average_time_per_question": 103
                },
                diagnosis_result={
                    "overall_level": "average",
                    "level_score": 75 + i * 2,
                    "strengths": ["해부학"],
                    "weaknesses": ["생리학", "병리학"],
                    "recommendations": ["생리학 기초 복습 필요"]
                }
            )
            db.add(session)
            day_sessions.append(session)
        
        db.commit()
        print(f"✅ 진단테스트 세션 {len(night_sessions) + len(day_sessions)}개 생성 완료")
        
        # 6. 교수-학생 매칭 생성
        print("🤝 교수-학생 매칭 생성...")
        
        # 물리치료과 교수 - 물리치료과 학생들 매칭
        physics_prof = prof_objects[0]
        physics_matches = []
        
        for student in [student_objects[0], student_objects[3]]:  # physics_student, night_active_student
            match = ProfessorStudentMatch(
                professor_id=physics_prof.id,
                student_id=student.id,
                match_status="approved",
                match_criteria={
                    "school": "경복대학교",
                    "department": "물리치료학과",
                    "auto_matched": True
                },
                professor_decision={
                    "approved": True,
                    "decision_at": datetime.now().isoformat(),
                    "reason": "동일 학과 자동 승인"
                }
            )
            db.add(match)
            physics_matches.append(match)
        
        # 대기 중인 매칭도 몇 개 생성
        pending_match = ProfessorStudentMatch(
            professor_id=physics_prof.id,
            student_id=student_objects[1].id,  # nursing_student - 다른 학과지만 매칭 요청
            match_status="pending",
            match_criteria={
                "school": "경복대학교",
                "department": "간호학과",
                "cross_department": True
            }
        )
        db.add(pending_match)
        
        db.commit()
        print(f"✅ 교수-학생 매칭 {len(physics_matches) + 1}개 생성 완료")
        
        # 7. 진단테스트 알림 생성
        print("🔔 진단테스트 알림 생성...")
        
        alerts = []
        for session in night_sessions[-3:]:  # 최근 3개 새벽 세션에 대한 알림
            alert = StudentDiagnosisAlert(
                student_id=night_student.id,
                professor_id=physics_prof.id,
                diagnosis_info={
                    "test_type": "종합진단테스트",
                    "score": session.percentage_score,
                    "test_time": session.started_at.isoformat(),
                    "concern_level": "high" if session.started_at.hour < 6 else "normal",
                    "notes": f"새벽 {session.started_at.hour}시 테스트 수행"
                },
                alert_status="new"
            )
            db.add(alert)
            alerts.append(alert)
        
        db.commit()
        print(f"✅ 진단테스트 알림 {len(alerts)}개 생성 완료")
        
        # 8. 결과 요약
        print("\n" + "="*50)
        print("🎉 테스트 데이터베이스 생성 완료!")
        print("="*50)
        print(f"📊 데이터 요약:")
        print(f"  • 교수: {len(prof_objects)}명")
        print(f"  • 학생: {len(student_objects)}명")
        print(f"  • 진단테스트: 1개 (물리치료학과)")
        print(f"  • 진단세션: {len(night_sessions) + len(day_sessions)}개")
        print(f"    - 새벽 활동 세션: {len(night_sessions)}개 (새벽활동 학생)")
        print(f"    - 일반 세션: {len(day_sessions)}개 (물리치료 학생)")
        print(f"  • 교수-학생 매칭: {len(physics_matches) + 1}개")
        print(f"  • 진단테스트 알림: {len(alerts)}개")
        print()
        print("🔑 로그인 정보:")
        print("  교수 계정: prof_physics / password123")
        print("  학생 계정: physics_student / password123")
        print("  새벽활동 학생: night_active_student / password123")
        print()
        print("⚠️  새벽활동 학생이 새벽 시간대에 8회 진단테스트를 수행했습니다!")
        print("   학습 모니터링 페이지에서 확인해보세요.")
        print()
        print(f"📁 데이터베이스 파일: {DATABASE_URL}")
        
        return True
        
    except Exception as e:
        print(f"❌ 데이터베이스 생성 실패: {e}")
        db.rollback()
        return False
        
    finally:
        db.close()

if __name__ == "__main__":
    success = create_test_database()
    if success:
        print("\n✅ 성공! 이제 백엔드를 실행하고 학습 모니터링을 테스트해보세요.")
        print("   python -m uvicorn app.main:app --reload")
    else:
        print("\n❌ 실패! 오류를 확인하고 다시 시도해주세요.") 