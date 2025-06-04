#!/usr/bin/env python3
"""User 테이블에 진단테스트 관련 컬럼 추가 스크립트"""

from app.db.database import engine
from sqlalchemy import text

def add_diagnostic_columns():
    try:
        # 트랜잭션 사용
        with engine.begin() as conn:
            # diagnostic_test_completed 컬럼 추가
            try:
                conn.execute(text('ALTER TABLE users ADD COLUMN diagnostic_test_completed BOOLEAN DEFAULT FALSE NOT NULL'))
                print('✅ diagnostic_test_completed 컬럼 추가 완료')
            except Exception as e:
                print(f'⚠️ diagnostic_test_completed 컬럼 추가 실패 (이미 존재할 수 있음): {e}')
            
            # diagnostic_test_completed_at 컬럼 추가  
            try:
                conn.execute(text('ALTER TABLE users ADD COLUMN diagnostic_test_completed_at TIMESTAMP'))
                print('✅ diagnostic_test_completed_at 컬럼 추가 완료')
            except Exception as e:
                print(f'⚠️ diagnostic_test_completed_at 컬럼 추가 실패 (이미 존재할 수 있음): {e}')
            
            print('✅ 데이터베이스 수정 완료')
            
    except Exception as e:
        print(f'❌ 오류 발생: {e}')

if __name__ == "__main__":
    add_diagnostic_columns() 