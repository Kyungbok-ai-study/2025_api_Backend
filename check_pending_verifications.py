#!/usr/bin/env python3
"""대기 중인 인증 요청 확인 스크립트"""

from app.db.database import get_db
from app.models.verification import VerificationRequest
from app.models.user import User

def check_pending_verifications():
    try:
        db = next(get_db())
        
        # 대기 중인 인증 요청만 조회
        pending_verifications = db.query(VerificationRequest).filter(
            VerificationRequest.status == 'pending'
        ).all()
        
        print(f'대기 중인 인증 요청 수: {len(pending_verifications)}')
        print("=" * 50)
        
        for v in pending_verifications:
            user = db.query(User).filter(User.id == v.user_id).first()
            print(f'✅ ID: {v.id}')
            print(f'   요청번호: {v.request_number}')
            print(f'   사용자: {user.name if user else "None"} ({user.user_id if user else "None"})')
            print(f'   유형: {v.verification_type}')
            print(f'   상태: {v.status}')
            print(f'   신청일: {v.created_at}')
            print(f'   사유: {v.reason[:50]}...' if len(v.reason) > 50 else f'   사유: {v.reason}')
            print("-" * 30)
        
        # 관리자 API에서 사용하는 쿼리와 동일하게 테스트
        from sqlalchemy.orm import joinedload
        
        query = db.query(VerificationRequest).options(joinedload(VerificationRequest.user))
        query = query.filter(VerificationRequest.status == 'pending')
        verifications = query.order_by(VerificationRequest.created_at.desc()).all()
        
        print(f'\n관리자 API 형식으로 조회한 대기 중인 요청 수: {len(verifications)}')
        
    except Exception as e:
        print(f"오류 발생: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    check_pending_verifications() 