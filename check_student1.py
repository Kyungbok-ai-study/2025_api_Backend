#!/usr/bin/env python3
"""student1 계정 정보 확인 스크립트"""

from app.db.database import get_db
from app.models.user import User

def check_student1():
    try:
        # 데이터베이스 연결
        db = next(get_db())
        
        # student1 계정 조회
        user = db.query(User).filter(User.user_id == 'student1').first()
        
        if user:
            print("=== student1 계정 정보 ===")
            print(f"사용자 ID: {user.user_id}")
            print(f"이름: {user.name}")
            print(f"역할(role): {user.role}")
            print(f"이메일: {user.email}")
            print(f"학교: {user.school}")
            print(f"학과: {user.department}")
            print(f"입학년도: {user.admission_year}")
            print(f"생성일: {user.created_at}")
            print(f"활성화 상태: {user.is_active}")
            print("=" * 30)
            
            # 역할 분석
            if user.role == 'unverified' or user.role is None or user.role == '':
                print("✅ 미인증 사용자로 올바르게 설정됨")
            else:
                print(f"⚠️ 예상과 다른 역할: {user.role}")
                
        else:
            print("❌ student1 계정을 찾을 수 없습니다.")
            
    except Exception as e:
        print(f"❌ 오류 발생: {e}")

if __name__ == "__main__":
    check_student1() 