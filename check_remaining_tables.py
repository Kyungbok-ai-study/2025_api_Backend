#!/usr/bin/env python3
"""
남은 정리 대상 테이블 확인 스크립트
"""
import json
import os

def check_remaining_tables():
    """남은 정리 대상 테이블 확인"""
    
    print("🔍 전체 테이블별 복잡도 재분석")
    print("=" * 60)
    
    if not os.path.exists('db_analysis_result.json'):
        print("❌ 분석 결과 파일이 없습니다. 먼저 analyze_db.py를 실행하세요.")
        return
    
    with open('db_analysis_result.json', 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    # 컬럼 수 기준으로 정렬
    tables_by_complexity = [(name, info['columns']) for name, info in data['tables'].items()]
    tables_by_complexity.sort(key=lambda x: x[1], reverse=True)
    
    print("📊 테이블별 컬럼 수 (많은 순):")
    
    completed_tables = ['users', 'questions']  # 이미 최적화 완료
    needs_optimization = []
    simple_tables = []
    
    for i, (table_name, column_count) in enumerate(tables_by_complexity, 1):
        if table_name in completed_tables:
            status = "✅ 정리완료"
        elif column_count >= 15:
            status = "🟡 정리필요"
            needs_optimization.append((table_name, column_count))
        elif column_count >= 10:
            status = "🔶 검토필요"
        else:
            status = "✅ 단순함"
            simple_tables.append((table_name, column_count))
        
        print(f"{i:2d}. {table_name:<30} {column_count:2d}개 컬럼  {status}")
    
    print("\n" + "=" * 60)
    print("📋 정리 현황 요약")
    print("=" * 60)
    
    print(f"✅ 정리 완료: {len(completed_tables)}개 테이블")
    for table in completed_tables:
        print(f"   - {table}")
    
    if needs_optimization:
        print(f"\n🟡 추가 정리 필요: {len(needs_optimization)}개 테이블")
        for table_name, column_count in needs_optimization:
            print(f"   - {table_name:<25} ({column_count}개 컬럼)")
    
    print(f"\n✅ 단순한 테이블: {len(simple_tables)}개 (정리 불필요)")
    
    # 우선순위 제안
    if needs_optimization:
        print("\n🎯 다음 정리 우선순위 제안:")
        priority_tables = sorted(needs_optimization, key=lambda x: x[1], reverse=True)[:3]
        for i, (table_name, column_count) in enumerate(priority_tables, 1):
            print(f"   {i}. {table_name} ({column_count}개 컬럼)")
    
    return needs_optimization

def suggest_next_optimization():
    """다음 최적화 제안"""
    
    print("\n💡 다음 단계 제안")
    print("=" * 60)
    
    remaining = check_remaining_tables()
    
    if not remaining:
        print("🎉 모든 복잡한 테이블 정리 완료!")
        print("✨ 이제 로컬 LLM 마이그레이션을 진행하시면 됩니다.")
        return
    
    # 가장 복잡한 테이블 3개 제안
    priority_tables = sorted(remaining, key=lambda x: x[1], reverse=True)[:3]
    
    print("🚀 권장 작업 순서:")
    print("1. 추가 테이블 최적화 (선택사항)")
    for i, (table_name, column_count) in enumerate(priority_tables, 1):
        benefit = "높음" if column_count > 20 else "중간" if column_count > 15 else "낮음"
        print(f"   {i}. {table_name} 최적화 - 효과: {benefit}")
    
    print("\n2. 로컬 LLM 마이그레이션 진행 (권장)")
    print("   - 현재 주요 테이블 정리 완료로 충분히 진행 가능")
    print("   - 나머지 테이블들은 추후 필요시 정리")
    
    print("\n⚡ 추천: 현재 상태에서 로컬 LLM 마이그레이션 우선 진행!")

if __name__ == "__main__":
    suggest_next_optimization() 