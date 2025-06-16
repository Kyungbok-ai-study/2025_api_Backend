"""
교수-학생 매칭 시스템 초기 설정 및 자동 매칭 실행
"""
import asyncio
import sys
import os

# 경로 설정
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.database import SessionLocal
from app.models.user import User
from app.models.professor_student_match import ProfessorStudentMatch, StudentDiagnosisAlert
from app.services.professor_student_service import professor_student_service
from app.services.diagnosis_alert_hook import diagnosis_alert_hook
from datetime import datetime

async def setup_and_run_matching():
    """교수-학생 매칭 시스템 설정 및 실행"""
    
    db = SessionLocal()
    
    try:
        print("🎯 교수-학생 매칭 시스템 초기화 시작")
        
        # 1. 현재 데이터 확인
        professors = db.query(User).filter(User.role == "professor").all()
        students = db.query(User).filter(User.role == "student").all()
        
        print(f"📊 현재 데이터:")
        print(f"   - 교수: {len(professors)}명")
        print(f"   - 학생: {len(students)}명")
        
        # 교수 정보 출력
        print(f"👨‍🏫 교수 목록:")
        for prof in professors:
            print(f"   - {prof.name} | {prof.school} | {prof.department}")
        
        # 학생 정보 출력 (일부만)
        print(f"👨‍🎓 학생 목록 (처음 10명):")
        for student in students[:10]:
            print(f"   - {student.name} | {student.school} | {student.department}")
        
        # 2. 자동 매칭 실행
        print(f"\n🚀 자동 매칭 실행 중...")
        matching_result = await professor_student_service.auto_match_students_to_professors(db)
        
        if "error" in matching_result:
            print(f"❌ 매칭 실패: {matching_result['error']}")
            return
        
        print(f"✅ 자동 매칭 완료!")
        print(f"   - 총 교수: {matching_result['total_professors']}명")
        print(f"   - 총 학생: {matching_result['total_students']}명")
        print(f"   - 새로 매칭된 관계: {matching_result['new_matches']}개")
        
        # 3. 매칭 결과 확인
        print(f"\n📋 매칭 결과 확인:")
        for prof in professors:
            matches = await professor_student_service.get_professor_student_matches(
                db, prof.id, "pending"
            )
            if matches:
                print(f"   {prof.name} 교수 -> {len(matches)}명의 학생 매칭 대기 중")
                for match in matches[:3]:  # 처음 3명만 표시
                    print(f"     - {match['student_name']} ({match['student_department']})")
        
        # 4. 테스트용 진단테스트 알림 생성
        if students:
            print(f"\n🧪 테스트용 진단테스트 알림 생성...")
            test_student = students[0]
            
            # 임의의 진단테스트 결과 생성
            diagnosis_result = {
                "test_type": "종합진단테스트",
                "score": 85.5,
                "total_questions": 50,
                "correct_answers": 42,
                "time_taken": 1800,  # 30분
                "difficulty_areas": ["해부학", "생리학"],
                "performance_summary": {
                    "strong_areas": ["간호학 기초"],
                    "weak_areas": ["해부학"],
                    "recommendation": "해부학 추가 학습 필요"
                }
            }
            
            alert_result = await diagnosis_alert_hook.on_diagnosis_completed(
                db, test_student.id, diagnosis_result
            )
            
            if alert_result["success"]:
                print(f"✅ 테스트 알림 생성 완료: {alert_result['alerts_created']}개")
            
        print(f"\n🎉 교수-학생 매칭 시스템 설정 완료!")
        print(f"📝 다음 단계:")
        print(f"   1. 교수 로그인 후 /professor/student-monitoring-dashboard 확인")
        print(f"   2. /professor/my-students?status=pending 에서 대기 중인 학생 확인")
        print(f"   3. /professor/approve-student/{{match_id}} 로 학생 승인/거부")
        print(f"   4. /professor/diagnosis-alerts 에서 진단테스트 알림 확인")
        
    except Exception as e:
        print(f"❌ 오류 발생: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        db.close()

if __name__ == "__main__":
    print("🔧 교수-학생 매칭 시스템 설정 시작...")
    asyncio.run(setup_and_run_matching()) 