"""
현재 데이터베이스에 있는 학생들 확인 및 교수와 매칭
"""
from sqlalchemy.orm import Session
from app.db.database import get_db
from app.models.user import User

def check_existing_students():
    """현재 데이터베이스의 학생 현황 확인"""
    db = next(get_db())
    
    print("=== 현재 데이터베이스 사용자 현황 ===")
    
    # 전체 사용자 조회
    all_users = db.query(User).all()
    print(f"전체 사용자 수: {len(all_users)}명")
    
    # 역할별 분류
    professors = db.query(User).filter(User.role == "professor").all()
    students = db.query(User).filter(User.role == "student").all()
    
    print(f"교수: {len(professors)}명")
    print(f"학생: {len(students)}명")
    
    print("\n=== 교수 목록 ===")
    for prof in professors:
        print(f"- {prof.name} ({prof.user_id}) | {prof.school} {prof.department}")
    
    print("\n=== 학생 목록 ===")
    for student in students:
        grade_info = getattr(student, 'grade', '정보없음')
        print(f"- {student.name} ({student.user_id}) | {student.school} {student.department} | {grade_info}학년")
    
    # 홍길동 교수와 같은 학교+학과 학생 확인
    hgd_prof = db.query(User).filter(User.user_id == "hgd123").first()
    if hgd_prof:
        print(f"\n=== 홍길동 교수와 매칭 가능한 학생 ===")
        print(f"교수 정보: {hgd_prof.name} | {hgd_prof.school} {hgd_prof.department}")
        
        matched_students = db.query(User).filter(
            User.role == "student",
            User.school == hgd_prof.school,
            User.department == hgd_prof.department
        ).all()
        
        print(f"매칭된 학생 수: {len(matched_students)}명")
        for student in matched_students:
            print(f"- {student.name} ({student.user_id})")
    
    return students

def update_student_info_for_matching():
    """기존 학생들의 학교+학과 정보를 교수와 매칭되도록 업데이트"""
    db = next(get_db())
    
    # 홍길동 교수 정보 조회
    professor = db.query(User).filter(User.user_id == "hgd123").first()
    if not professor:
        print("홍길동 교수를 찾을 수 없습니다.")
        return
    
    # 현재 학생들 조회
    students = db.query(User).filter(User.role == "student").all()
    print(f"업데이트할 학생 수: {len(students)}명")
    
    updated_count = 0
    for student in students:
        # 학생의 학교+학과를 교수와 동일하게 설정
        if student.school != professor.school or student.department != professor.department:
            student.school = professor.school
            student.department = professor.department
            # grade 필드가 있다면 기본값 설정
            if hasattr(student, 'grade') and student.grade is None:
                student.grade = 2  # 기본 2학년으로 설정
            updated_count += 1
            print(f"업데이트: {student.name} ({student.user_id}) -> {professor.school} {professor.department}")
    
    db.commit()
    print(f"\n총 {updated_count}명의 학생 정보가 업데이트되었습니다.")
    print(f"모든 학생이 {professor.school} {professor.department} 소속으로 설정되었습니다.")

if __name__ == "__main__":
    print("1. 현재 학생 현황 확인")
    check_existing_students()
    
    print("\n" + "="*50)
    print("2. 학생 정보를 교수와 매칭되도록 업데이트하시겠습니까? (y/n)")
    choice = input().lower()
    
    if choice == 'y':
        update_student_info_for_matching()
        print("\n업데이트 완료 후 다시 확인:")
        check_existing_students()
    else:
        print("업데이트를 건너뛰었습니다.") 