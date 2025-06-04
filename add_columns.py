#!/usr/bin/env python3
"""VerificationRequest 테이블에 컬럼 추가 스크립트"""

from app.db.database import engine
from sqlalchemy import text

def add_columns():
    try:
        # 트랜잭션 사용
        with engine.begin() as conn:
            # reviewed_by 컬럼 추가
            try:
                conn.execute(text('ALTER TABLE verification_requests ADD COLUMN reviewed_by VARCHAR(50)'))
                print('✅ reviewed_by 컬럼 추가 완료')
            except Exception as e:
                print(f'⚠️ reviewed_by 컬럼 추가 실패 (이미 존재할 수 있음): {e}')
            
            # rejection_reason 컬럼 추가  
            try:
                conn.execute(text('ALTER TABLE verification_requests ADD COLUMN rejection_reason TEXT'))
                print('✅ rejection_reason 컬럼 추가 완료')
            except Exception as e:
                print(f'⚠️ rejection_reason 컬럼 추가 실패 (이미 존재할 수 있음): {e}')
            
            print('✅ 데이터베이스 수정 완료')
            
    except Exception as e:
        print(f'❌ 오류 발생: {e}')

if __name__ == "__main__":
    add_columns() 