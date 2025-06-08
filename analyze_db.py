#!/usr/bin/env python3
"""
데이터베이스 구조 분석 스크립트
"""
import os
import sys
import json
from datetime import datetime
from sqlalchemy import inspect, text, MetaData, create_engine
from sqlalchemy.orm import sessionmaker

# 환경 설정
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def analyze_database():
    """데이터베이스 구조 분석"""
    
    print("🔍 데이터베이스 구조 분석 시작")
    print("=" * 60)
    
    try:
        # 데이터베이스 연결
        from app.db.database import engine
        
        inspector = inspect(engine)
        tables = inspector.get_table_names()
        
        analysis_result = {
            "timestamp": datetime.now().isoformat(),
            "total_tables": len(tables),
            "tables": {}
        }
        
        print(f"📊 총 {len(tables)}개 테이블 발견")
        print()
        
        # 각 테이블 분석
        for table_name in sorted(tables):
            columns = inspector.get_columns(table_name)
            indexes = inspector.get_indexes(table_name)
            foreign_keys = inspector.get_foreign_keys(table_name)
            
            table_info = {
                "columns": len(columns),
                "indexes": len(indexes),
                "foreign_keys": len(foreign_keys),
                "column_details": []
            }
            
            # 컬럼 상세 정보
            for col in columns:
                col_info = {
                    "name": col["name"],
                    "type": str(col["type"]),
                    "nullable": col["nullable"],
                    "primary_key": col.get("primary_key", False)
                }
                table_info["column_details"].append(col_info)
            
            analysis_result["tables"][table_name] = table_info
            
            print(f"📋 {table_name}")
            print(f"   - 컬럼: {len(columns)}개")
            print(f"   - 인덱스: {len(indexes)}개") 
            print(f"   - 외래키: {len(foreign_keys)}개")
            
            # 중복 가능성이 높은 컬럼 체크
            column_names = [col["name"] for col in columns]
            duplicates = []
            
            if "created_at" in column_names and "updated_at" in column_names:
                duplicates.append("timestamp fields")
            if any("id" in name and name != "id" for name in column_names):
                duplicates.append("multiple ID fields")
                
            if duplicates:
                print(f"   ⚠️  중복 가능: {', '.join(duplicates)}")
            
            print()
        
        # 정리 대상 식별
        print("🧹 정리 대상 식별")
        print("=" * 60)
        
        # 1. 중복 컬럼이 많은 테이블
        complex_tables = [(name, info) for name, info in analysis_result["tables"].items() 
                         if info["columns"] > 15]
        
        if complex_tables:
            print("📊 복잡한 테이블 (15개 이상 컬럼):")
            for table_name, info in complex_tables:
                print(f"   - {table_name}: {info['columns']}개 컬럼")
        
        # 2. 외래키가 많은 테이블 (관계 복잡도)
        related_tables = [(name, info) for name, info in analysis_result["tables"].items() 
                         if info["foreign_keys"] > 2]
        
        if related_tables:
            print("\n🔗 관계가 복잡한 테이블 (3개 이상 외래키):")
            for table_name, info in related_tables:
                print(f"   - {table_name}: {info['foreign_keys']}개 외래키")
        
        # 결과 저장
        with open("db_analysis_result.json", "w", encoding="utf-8") as f:
            json.dump(analysis_result, f, indent=2, ensure_ascii=False)
        
        print(f"\n✅ 분석 완료! 결과가 'db_analysis_result.json'에 저장되었습니다.")
        
        return analysis_result
        
    except Exception as e:
        print(f"❌ 분석 중 오류 발생: {e}")
        return None

def suggest_optimization():
    """최적화 제안"""
    
    print("\n💡 최적화 제안")
    print("=" * 60)
    
    suggestions = [
        "1. User 모델: student_id와 user_id 통합 검토",
        "2. Question 모델: subject_name과 area_name 통합",
        "3. 분석 테이블들: StudentActivity, LearningAnalytics 등 통합 검토",
        "4. Timestamp 필드들: 표준화 (모두 timezone-aware로)",
        "5. JSON 필드 활용: 여러 boolean 필드들을 JSON으로 통합",
        "6. 인덱스 최적화: 자주 조회되는 조합 필드에 복합 인덱스 추가"
    ]
    
    for suggestion in suggestions:
        print(f"✨ {suggestion}")

if __name__ == "__main__":
    result = analyze_database()
    if result:
        suggest_optimization() 