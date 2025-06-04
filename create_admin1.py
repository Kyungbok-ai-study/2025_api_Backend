#!/usr/bin/env python3
"""admin1 관리자 계정 생성 스크립트"""

from app.db.database import get_db
from app.models.user import User
from app.utils.auth import get_password_hash
from datetime import datetime

def create_admin1():
    try:
        # 데이터베이스 연결
        db = next(get_db())
        
        # 기존 admin1 계정 확인
        existing_user = db.query(User).filter(User.user_id == 'admin1').first()
        
        if existing_user:
            print("⚠️ admin1 계정이 이미 존재합니다.")
            print("기존 계정의 비밀번호를 bcrypt로 업데이트합니다...")
            
            # bcrypt 해시로 비밀번호 업데이트
            password = "admin1"
            existing_user.hashed_password = get_password_hash(password)
            db.commit()
            
            print("✅ admin1 계정의 비밀번호가 bcrypt로 업데이트되었습니다!")
            print(f"기존 계정 정보:")
            print(f"- 이름: {existing_user.name}")
            print(f"- 역할: {existing_user.role}")
            print(f"- 이메일: {existing_user.email}")
            print(f"- 아이디: admin1")
            print(f"- 비밀번호: admin1")
            return
        
        # bcrypt를 사용한 비밀번호 해싱
        password = "admin1"
        hashed_password = get_password_hash(password)
        
        # 새 관리자 계정 생성
        admin_user = User(
            user_id="admin1",
            hashed_password=hashed_password,
            name="시스템 관리자",
            email="admin1@campus-on.kr",
            school="경복대학교",
            department="전산정보팀",
            admission_year=2024,
            role="admin",
            is_active=True,
            terms_agreed=True,
            privacy_agreed=True,
            age_verified=True,
            created_at=datetime.now()
        )
        
        db.add(admin_user)
        db.commit()
        
        print("✅ admin1 관리자 계정이 성공적으로 생성되었습니다!")
        print("=== 생성된 계정 정보 ===")
        print(f"아이디: admin1")
        print(f"비밀번호: admin1")
        print(f"이름: {admin_user.name}")
        print(f"역할: {admin_user.role}")
        print(f"이메일: {admin_user.email}")
        print(f"학교: {admin_user.school}")
        print(f"부서: {admin_user.department}")
        print("=" * 30)
        
    except Exception as e:
        print(f"❌ 오류 발생: {e}")
        try:
            db.rollback()
        except:
            pass

if __name__ == "__main__":
    create_admin1() 