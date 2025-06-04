#!/usr/bin/env python3
"""student1 계정을 미인증 상태로 되돌리는 스크립트"""

from app.db.database import get_db
from app.models.user import User

def reset_student1_to_unverified():
    try:
        # 데이터베이스 연결
        db = next(get_db())
        
        # student1 계정 조회
        user = db.query(User).filter(User.user_id == 'student1').first()
        
        if user:
            print(f"=== student1 계정 현재 상태 ===")
            print(f"현재 역할: {user.role}")
            
            # 미인증 상태로 변경
            user.role = 'unverified'
            db.commit()
            
            print(f"✅ student1 계정이 미인증 상태로 변경되었습니다.")
            print(f"변경된 역할: {user.role}")
            
        else:
            print("❌ student1 계정을 찾을 수 없습니다.")
            
    except Exception as e:
        print(f"❌ 오류 발생: {e}")
        db.rollback()

if __name__ == "__main__":
    reset_student1_to_unverified() 