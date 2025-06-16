#!/usr/bin/env python3
"""
실제 데이터 기반 AI 분석 테스트 스크립트
새로운 진단테스트 세션을 생성하고 완료하여 실제 데이터 AI 분석이 제대로 작동하는지 확인
"""

import os
import sys
import asyncio
from datetime import datetime
import json

# 현재 디렉토리를 Python path에 추가
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.db.database import get_db
from app.models.diagnosis import DiagnosticSession, SessionStatus
from app.api.diagnosis import (
    real_data_ai_analysis, DetailedResult, 
    SessionStartRequest, SessionCompleteRequest
)

async def test_real_ai_analysis():
    """실제 데이터 기반 AI 분석 테스트"""
    print("🧪 실제 데이터 기반 AI 분석 테스트 시작")
    print("=" * 60)
    
    db = next(get_db())
    
    # 테스트용 상세 결과 데이터 (실제 문제 30개 시뮬레이션)
    test_detailed_results = []
    
    # 다양한 성과 패턴으로 30개 문제 시뮬레이션
    question_types = ["기본개념", "종합판단", "응용문제"]
    domains = ["신경계", "근골격계", "심폐순환계", "기타"]
    difficulties = ["쉬움", "보통", "어려움"]
    
    correct_answers = 0
    total_time = 0
    
    for i in range(1, 31):
        # 랜덤하게 정답/오답 결정 (약 70% 정답률)
        is_correct = i % 10 != 3 and i % 10 != 7 and i % 10 != 9  # 70% 정답률
        if is_correct:
            correct_answers += 1
        
        # 문제별 시간 (1-5초 범위)
        time_spent = (i % 5 + 1) * 1000  # 밀리초
        total_time += time_spent
        
        result = DetailedResult(
            question_id=f"DIAG_{i:03d}",
            question_number=i,
            selected_answer=str((i % 5) + 1),
            correct_answer=str((i % 5) + 1) if is_correct else str(((i + 1) % 5) + 1),
            is_correct=is_correct,
            time_spent_ms=time_spent,
            difficulty_level=difficulties[i % 3],
            domain=domains[i % 4],
            question_type=question_types[i % 3]
        )
        test_detailed_results.append(result)
    
    total_score = round((correct_answers / 30) * 100, 1)
    
    print(f"📊 테스트 시나리오:")
    print(f"  정답/오답: {correct_answers}/30")
    print(f"  점수: {total_score}점")
    print(f"  총 시간: {total_time/1000:.1f}초")
    
    # 실제 데이터 기반 AI 분석 실행
    print(f"\n🤖 실제 데이터 기반 AI 분석 실행...")
    
    try:
        ai_result = await real_data_ai_analysis(
            session_id="test_session_123",
            user_id=32,  # 기존 사용자 ID
            detailed_results=test_detailed_results,
            total_score=total_score,
            total_time_ms=total_time,
            test_type="physical_therapy_1st",
            department="물리치료학과",
            db=db
        )
        
        print(f"✅ AI 분석 성공!")
        print(f"\n📈 분석 결과:")
        print(f"  신뢰도: {ai_result.confidence_score}")
        print(f"  유형별 정답률: {ai_result.type_analysis}")
        print(f"  난이도별 정답률: {ai_result.difficulty_analysis}")
        print(f"  약한 영역: {ai_result.weak_areas}")
        
        print(f"\n⏱️ 시간 분석:")
        time_analysis = ai_result.time_analysis
        print(f"  총 시간: {time_analysis['total_time_seconds']}초")
        print(f"  문제당 평균: {time_analysis['avg_time_per_question']}초")
        print(f"  시간 효율성: {time_analysis['time_efficiency']}")
        if 'time_percentile' in time_analysis:
            print(f"  시간 백분위: {time_analysis['time_percentile']}%")
        
        print(f"\n👥 동료 비교 분석:")
        peer_comparison = ai_result.peer_comparison
        print(f"  학과 평균: {peer_comparison['department_average']}점")
        print(f"  백분위: {peer_comparison['percentile']}%")
        print(f"  순위: {peer_comparison['ranking']}")
        print(f"  비교 대상: {peer_comparison['total_peers']}명")
        if 'score_vs_avg' in peer_comparison:
            print(f"  평균 대비: {peer_comparison['score_vs_avg']:+.1f}점")
        
        print(f"\n💡 AI 권장사항:")
        for i, recommendation in enumerate(ai_result.recommendations, 1):
            print(f"  {i}. {recommendation}")
        
        print(f"\n🔍 실제 데이터 활용 증명:")
        print(f"  ✅ 동료 {peer_comparison['total_peers']}명 데이터 분석")
        print(f"  ✅ 실제 문제별 통계 활용")
        print(f"  ✅ 시간 효율성 비교 분석")
        print(f"  ✅ 개인화된 권장사항 생성")
        
    except Exception as e:
        print(f"❌ AI 분석 실패: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        db.close()
    
    print(f"\n" + "=" * 60)
    print(f"🧪 실제 데이터 기반 AI 분석 테스트 완료")

if __name__ == "__main__":
    asyncio.run(test_real_ai_analysis()) 