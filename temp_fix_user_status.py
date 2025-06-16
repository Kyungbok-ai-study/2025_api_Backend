#!/usr/bin/env python3
"""
임시 스크립트: 사용자 진단테스트 완료 상태 직접 업데이트
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from datetime import datetime
from app.database import get_db
from app.models.user import User

def fix_user_diagnostic_status(user_id: int = 33):
    """사용자의 진단테스트 완료 상태를 직접 업데이트"""
    
    # 데이터베이스 연결
    db = next(get_db())
    
    try:
        # 사용자 조회
        user = db.query(User).filter(User.id == user_id).first()
        
        if not user:
            print(f"❌ 사용자 ID {user_id}를 찾을 수 없습니다.")
            return
        
        print(f"👤 사용자 정보: {user.name} (ID: {user.id})")
        print(f"📊 현재 diagnosis_info: {user.diagnosis_info}")
        print(f"🎯 현재 diagnostic_test_completed: {user.diagnostic_test_completed}")
        
        # 진단테스트 완료 상태 업데이트
        user.set_diagnostic_test_info(
            completed=True,
            completed_at=datetime.utcnow().isoformat(),
            latest_score=85.0,  # 임시 점수
            test_count=1
        )
        user.updated_at = datetime.utcnow()
        
        # 데이터베이스 커밋
        db.commit()
        db.refresh(user)
        
        print(f"✅ 업데이트 완료!")
        print(f"📊 새로운 diagnosis_info: {user.diagnosis_info}")
        print(f"🎯 새로운 diagnostic_test_completed: {user.diagnostic_test_completed}")
        
    except Exception as e:
        print(f"❌ 오류 발생: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    fix_user_diagnostic_status() 