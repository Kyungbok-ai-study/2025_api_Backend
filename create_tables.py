#!/usr/bin/env python3
"""
새로운 테이블들을 생성하는 스크립트
"""

from app.db.database import engine, Base
from app.models.assignment import Assignment, AssignmentSubmission, ProblemBank
from app.models.analytics import StudentActivity, StudentWarning, LearningAnalytics, ClassStatistics, ProfessorDashboardData

def create_tables():
    try:
        print("📋 테이블 생성 시작...")
        Base.metadata.create_all(bind=engine)
        print("✅ 모든 테이블이 성공적으로 생성되었습니다!")
        
        # 생성된 테이블 확인
        from sqlalchemy import inspect
        inspector = inspect(engine)
        tables = inspector.get_table_names()
        
        print("\n📊 현재 데이터베이스 테이블 목록:")
        print("=" * 50)
        for table in sorted(tables):
            print(f"- {table}")
            
    except Exception as e:
        print(f"❌ 테이블 생성 중 오류 발생: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    create_tables() 