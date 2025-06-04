#!/usr/bin/env python3
"""인증 요청 데이터 확인 스크립트"""

from app.db.database import get_db
from app.models.verification import VerificationRequest
from app.models.user import User

def check_verifications():
    try:
        db = next(get_db())
        
        # 전체 인증 요청 조회
        verifications = db.query(VerificationRequest).all()
        print(f'전체 인증 요청 수: {len(verifications)}')
        print("=" * 50)
        
        for v in verifications:
            user = db.query(User).filter(User.id == v.user_id).first()
            print(f'ID: {v.id}')
            print(f'User: {user.name if user else "None"} ({user.user_id if user else "None"})')
            print(f'Type: {v.verification_type}')
            print(f'Status: {v.status}')
            print(f'Created: {v.created_at}')
            print(f'Documents: {v.documents}')
            print("-" * 30)
        
        # 대기 중인 인증 요청만 조회
        pending_verifications = db.query(VerificationRequest).filter(
            VerificationRequest.status == 'pending'
        ).all()
        print(f'\n대기 중인 인증 요청 수: {len(pending_verifications)}')
        
        # 사용자별 역할 확인
        users = db.query(User).all()
        print(f'\n전체 사용자 수: {len(users)}')
        role_counts = {}
        for user in users:
            role = user.role or 'unverified'
            role_counts[role] = role_counts.get(role, 0) + 1
        
        print("역할별 사용자 수:")
        for role, count in role_counts.items():
            print(f"  {role}: {count}명")
            
    except Exception as e:
        print(f"오류 발생: {e}")

if __name__ == "__main__":
    check_verifications() 