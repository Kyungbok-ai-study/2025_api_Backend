"""
앙상블 AI 시스템 종합 테스트
DeepSeek + Gemini + OpenAI GPT 파이프라인 검증
"""

import asyncio
import httpx
import json
from datetime import datetime

# 테스트 설정
BASE_URL = "http://localhost:8000"

async def test_ensemble_system():
    """앙상블 시스템 종합 테스트"""
    
    print("🚀 앙상블 AI 시스템 테스트 시작")
    print("=" * 60)
    
    async with httpx.AsyncClient() as client:
        
        # 1. 시스템 상태 확인
        print("\n📊 1. 시스템 상태 확인")
        try:
            response = await client.get(f"{BASE_URL}/ensemble/status")
            if response.status_code == 200:
                status = response.json()
                print("✅ 시스템 상태 조회 성공")
                print(f"   - 총 요청 수: {status.get('ensemble_stats', {}).get('total_requests', 0)}")
                print(f"   - 성공 완료: {status.get('ensemble_stats', {}).get('successful_completions', 0)}")
            else:
                print(f"❌ 시스템 상태 조회 실패: {response.status_code}")
        except Exception as e:
            print(f"❌ 시스템 상태 확인 오류: {e}")
        
        # 2. 단일 질문 처리 테스트
        print("\n🎯 2. 단일 질문 처리 테스트")
        test_question = {
            "question": "간호학에서 감염관리의 중요성과 주요 원칙에 대해 설명해주세요.",
            "difficulty_level": "medium",
            "department": "간호학과",
            "target_audience": "university_students"
        }
        
        try:
            response = await client.post(
                f"{BASE_URL}/ensemble/process",
                json=test_question
            )
            
            if response.status_code == 200:
                result = response.json()
                print("✅ 앙상블 처리 성공")
                print(f"   - 성공 여부: {result.get('success', False)}")
                print(f"   - 처리 시간: {result.get('metadata', {}).get('processing_time_seconds', 0):.2f}초")
                
                # 최종 답변 미리보기
                final_content = result.get('final_content', '')
                if final_content:
                    print(f"   - 답변 길이: {len(final_content)} 문자")
                    print(f"   - 답변 미리보기: {final_content[:100]}...")
                
                # 단계별 처리 결과
                stages = result.get('processing_stages', {})
                print("   📋 단계별 처리 결과:")
                
                deepseek = stages.get('deepseek_analysis', {})
                print(f"      1️⃣ DeepSeek 분석: {'✅' if deepseek.get('success') else '❌'}")
                
                gemini = stages.get('gemini_explanation', {})
                print(f"      2️⃣ Gemini 설명: {'✅' if gemini.get('success') else '❌'}")
                
                openai = stages.get('openai_improvement', {})
                print(f"      3️⃣ OpenAI 개선: {'✅' if openai.get('success') else '❌'}")
                
            else:
                print(f"❌ 앙상블 처리 실패: {response.status_code}")
                print(f"   오류 내용: {response.text}")
                
        except Exception as e:
            print(f"❌ 단일 질문 처리 오류: {e}")
        
        # 3. 배치 처리 테스트
        print("\n📦 3. 배치 처리 테스트")
        batch_questions = {
            "questions": [
                {
                    "question": "물리치료에서 관절가동범위 운동의 종류와 적용법은?",
                    "difficulty_level": "easy",
                    "department": "물리치료학과"
                },
                {
                    "question": "작업치료에서 인지재활의 접근방법과 평가도구에 대해 설명하세요.",
                    "difficulty_level": "medium",
                    "department": "작업치료학과"
                }
            ],
            "max_concurrent": 2
        }
        
        try:
            response = await client.post(
                f"{BASE_URL}/ensemble/batch",
                json=batch_questions
            )
            
            if response.status_code == 200:
                result = response.json()
                print("✅ 배치 처리 성공")
                print(f"   - 총 처리량: {result.get('total_processed', 0)}")
                
                results = result.get('results', [])
                for i, res in enumerate(results):
                    success = res.get('success', False)
                    print(f"   - 질문 {i+1}: {'✅' if success else '❌'}")
                    
            else:
                print(f"❌ 배치 처리 실패: {response.status_code}")
                
        except Exception as e:
            print(f"❌ 배치 처리 오류: {e}")
        
        # 4. 최종 상태 확인
        print("\n📈 4. 최종 시스템 상태")
        try:
            response = await client.get(f"{BASE_URL}/ensemble/status")
            if response.status_code == 200:
                status = response.json()
                ensemble_stats = status.get('ensemble_stats', {})
                print("✅ 최종 통계:")
                print(f"   - 총 요청: {ensemble_stats.get('total_requests', 0)}")
                print(f"   - 성공 완료: {ensemble_stats.get('successful_completions', 0)}")
                print(f"   - 실패 요청: {ensemble_stats.get('failed_requests', 0)}")
                
                # 각 단계별 실패 통계
                stage_failures = ensemble_stats.get('stage_failures', {})
                print("   📊 단계별 실패 통계:")
                print(f"      - DeepSeek: {stage_failures.get('deepseek', 0)}")
                print(f"      - Gemini: {stage_failures.get('gemini', 0)}")
                print(f"      - OpenAI: {stage_failures.get('openai', 0)}")
                
                # 시스템 건강도
                system_health = status.get('system_health', 'unknown')
                health_emoji = "💚" if system_health == "healthy" else "⚠️"
                print(f"   {health_emoji} 시스템 건강도: {system_health}")
                
        except Exception as e:
            print(f"❌ 최종 상태 확인 오류: {e}")
    
    print("\n" + "=" * 60)
    print("🏁 앙상블 AI 시스템 테스트 완료")

async def test_individual_services():
    """개별 서비스 테스트"""
    
    print("\n🔍 개별 서비스 상태 테스트")
    print("-" * 40)
    
    # DeepSeek 서비스 테스트
    try:
        from app.services.deepseek_service import deepseek_service
        result = await deepseek_service.analyze_educational_content(
            question="테스트 질문입니다",
            difficulty_level="easy"
        )
        deepseek_status = "✅" if result.get("success") else "❌"
        print(f"DeepSeek 서비스: {deepseek_status}")
    except Exception as e:
        print(f"DeepSeek 서비스: ❌ ({e})")
    
    # Gemini 서비스 테스트
    try:
        from app.services.gemini_service import gemini_service
        result = await gemini_service.generate_educational_explanation(
            question="테스트 질문입니다",
            core_concepts=["테스트"],
            difficulty_level="easy"
        )
        gemini_status = "✅" if result.get("success") else "❌"
        print(f"Gemini 서비스: {gemini_status}")
    except Exception as e:
        print(f"Gemini 서비스: ❌ ({e})")
    
    # OpenAI 서비스 테스트
    try:
        from app.services.openai_service import openai_service
        result = await openai_service.improve_text_style(
            content="테스트 텍스트입니다.",
            style_type="educational"
        )
        openai_status = "✅" if result.get("success") else "❌"
        print(f"OpenAI 서비스: {openai_status}")
    except Exception as e:
        print(f"OpenAI 서비스: ❌ ({e})")

if __name__ == "__main__":
    print("🧪 앙상블 AI 시스템 테스트 슈트")
    print(f"테스트 시작 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # 개별 서비스 테스트
    asyncio.run(test_individual_services())
    
    # 전체 시스템 테스트
    asyncio.run(test_ensemble_system())
    
    print(f"\n테스트 완료 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}") 