"""
교수-학생 매칭 상태 확인 스크립트
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.db.database import SessionLocal, engine
from app.models.user import User
from app.models.professor_student_match import ProfessorStudentMatch
from sqlalchemy.orm import Session

def check_matching_status():
    """교수-학생 매칭 상태 확인"""
    db = SessionLocal()
    
    try:
        print("🔍 교수-학생 매칭 상태 확인")
        print("=" * 50)
        
        # 모든 교수 조회
        professors = db.query(User).filter(User.role == "professor").all()
        print(f"📚 총 교수 수: {len(professors)}")
        
        for prof in professors:
            print(f"\n교수: {prof.name} ({prof.school} - {prof.department})")
            
            # 해당 교수의 매칭 조회
            matches = db.query(ProfessorStudentMatch).filter(
                ProfessorStudentMatch.professor_id == prof.id
            ).all()
            
            print(f"  매칭된 학생 수: {len(matches)}")
            
            for match in matches:
                student = db.query(User).filter(User.id == match.student_id).first()
                if student:
                    print(f"    - {student.name} ({student.school} - {student.department}) | 상태: {match.match_status}")
        
        print("\n" + "=" * 50)
        
        # 모든 학생 조회
        students = db.query(User).filter(User.role == "student").all()
        print(f"👥 총 학생 수: {len(students)}")
        
        matched_students = 0
        for student in students:
            matches = db.query(ProfessorStudentMatch).filter(
                ProfessorStudentMatch.student_id == student.id,
                ProfessorStudentMatch.match_status == "approved"
            ).count()
            
            if matches > 0:
                matched_students += 1
                
        print(f"📊 매칭된 학생 수: {matched_students}")
        print(f"📊 매칭 안된 학생 수: {len(students) - matched_students}")
        
        # 매칭 권장사항
        print("\n💡 권장사항:")
        if matched_students == 0:
            print("   ⚠️ 매칭된 학생이 없습니다!")
            print("   📍 모니터링 페이지에서 '👥 자동 매칭' 버튼을 클릭하세요")
        elif matched_students < len(students):
            print(f"   ⚠️ {len(students) - matched_students}명의 학생이 매칭되지 않았습니다")
            print("   📍 모니터링 페이지에서 '👥 자동 매칭' 버튼을 클릭하세요")
        else:
            print("   ✅ 모든 학생이 매칭되었습니다!")
            
    except Exception as e:
        print(f"❌ 오류 발생: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    check_matching_status() 