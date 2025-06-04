#!/usr/bin/env python3
"""인증 요청 API 테스트 스크립트"""

from app.db.database import get_db
from app.models.verification import VerificationRequest
from app.models.user import User
from datetime import datetime
import json

def create_test_verification():
    try:
        db = next(get_db())
        
        # unverified 사용자 찾기
        unverified_user = db.query(User).filter(User.role == 'unverified').first()
        
        if not unverified_user:
            print("❌ unverified 역할의 사용자가 없습니다.")
            return
        
        print(f"✅ 테스트 사용자: {unverified_user.name} ({unverified_user.user_id})")
        
        # 이미 대기 중인 요청이 있는지 확인
        existing_request = db.query(VerificationRequest).filter(
            VerificationRequest.user_id == unverified_user.id,
            VerificationRequest.status == 'pending'
        ).first()
        
        if existing_request:
            print(f"⚠️ 이미 대기 중인 요청이 있습니다. ID: {existing_request.id}")
            return
        
        # 다음 요청 번호 생성
        last_request = db.query(VerificationRequest).order_by(
            VerificationRequest.request_number.desc()
        ).first()
        next_request_number = (last_request.request_number + 1) if last_request else 1
        
        # 테스트 문서 정보
        test_documents = [
            {
                "name": "재학증명서.pdf",
                "size": 1024000,
                "type": "application/pdf",
                "uploaded_at": datetime.now().isoformat()
            },
            {
                "name": "학생증_앞면.jpg",
                "size": 512000,
                "type": "image/jpeg",
                "uploaded_at": datetime.now().isoformat()
            }
        ]
        
        # 새 인증 요청 생성
        new_request = VerificationRequest(
            request_number=next_request_number,
            user_id=unverified_user.id,
            verification_type='student',
            reason='테스트용 재학생 인증 요청입니다. 캠퍼스온의 모든 기능을 이용하고 싶어서 신청합니다.',
            status='pending',
            submitted_at=datetime.now(),
            documents=json.dumps(test_documents, ensure_ascii=False)
        )
        
        db.add(new_request)
        db.commit()
        db.refresh(new_request)
        
        print(f"✅ 테스트 인증 요청 생성 완료!")
        print(f"   - 요청 ID: {new_request.id}")
        print(f"   - 요청 번호: {new_request.request_number}")
        print(f"   - 사용자: {unverified_user.name}")
        print(f"   - 유형: {new_request.verification_type}")
        print(f"   - 상태: {new_request.status}")
        
    except Exception as e:
        print(f"❌ 오류 발생: {e}")
        try:
            db.rollback()
        except:
            pass

if __name__ == "__main__":
    create_test_verification() 