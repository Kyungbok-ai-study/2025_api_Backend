"""
딥시크 학습 세션 테이블 생성 마이그레이션

실행 방법:
python migration_create_deepseek_table.py
"""

import sys
import os
from pathlib import Path

# 프로젝트 루트를 Python path에 추가
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from sqlalchemy import create_engine, text
from app.core.config import get_settings
from app.models.deepseek import DeepSeekLearningSession
from app.database import Base

def create_deepseek_table():
    """딥시크 학습 세션 테이블 생성"""
    settings = get_settings()
    
    # 데이터베이스 연결
    engine = create_engine(settings.database_url)
    
    try:
        print("🔄 딥시크 학습 세션 테이블 생성 시작...")
        
        # 테이블 생성
        Base.metadata.create_all(bind=engine, tables=[DeepSeekLearningSession.__table__])
        
        # 테이블이 성공적으로 생성되었는지 확인
        with engine.connect() as conn:
            result = conn.execute(text("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = 'public' 
                AND table_name = 'deepseek_learning_sessions'
            """))
            
            if result.fetchone():
                print("✅ deepseek_learning_sessions 테이블이 성공적으로 생성되었습니다.")
                
                # 테이블 구조 확인
                result = conn.execute(text("""
                    SELECT column_name, data_type, is_nullable
                    FROM information_schema.columns
                    WHERE table_name = 'deepseek_learning_sessions'
                    ORDER BY ordinal_position
                """))
                
                print("\n📋 테이블 구조:")
                for row in result:
                    nullable = "NULL" if row[2] == "YES" else "NOT NULL"
                    print(f"  - {row[0]}: {row[1]} ({nullable})")
                    
                # 인덱스 확인
                result = conn.execute(text("""
                    SELECT indexname, indexdef 
                    FROM pg_indexes 
                    WHERE tablename = 'deepseek_learning_sessions'
                """))
                
                print("\n🔍 인덱스:")
                for row in result:
                    print(f"  - {row[0]}: {row[1]}")
                    
            else:
                print("❌ 테이블 생성에 실패했습니다.")
                
    except Exception as e:
        print(f"❌ 마이그레이션 실패: {e}")
        return False
    
    finally:
        engine.dispose()
    
    return True

def add_user_relationship():
    """User 모델에 딥시크 관계 추가 (이미 코드에서 추가됨)"""
    print("📝 User 모델에 딥시크 관계가 이미 추가되어 있습니다.")
    print("   - User.deepseek_sessions relationship")

def add_question_relationship():
    """Question 모델에 딥시크 관계 추가 (이미 코드에서 추가됨)"""
    print("📝 Question 모델에 딥시크 관계가 이미 추가되어 있습니다.")
    print("   - Question.deepseek_sessions relationship")

if __name__ == "__main__":
    print("🚀 딥시크 학습 시스템 데이터베이스 마이그레이션 시작\n")
    
    # 1. 테이블 생성
    if create_deepseek_table():
        print("\n✅ 딥시크 학습 세션 테이블 생성 완료")
    else:
        print("\n❌ 테이블 생성 실패")
        sys.exit(1)
    
    # 2. 관계 확인
    add_user_relationship()
    add_question_relationship()
    
    print("\n🎉 딥시크 학습 시스템 데이터베이스 마이그레이션 완료!")
    print("\n다음 단계:")
    print("1. 백엔드 서버 재시작")
    print("2. 교수가 문제 승인 시 자동으로 딥시크 학습 세션 생성됨")
    print("3. 어드민 대시보드에서 딥시크 학습 현황 모니터링 가능") 