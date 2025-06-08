#!/usr/bin/env python3
"""
최종 통합 시스템 테스트 (Event Loop 문제 해결)
DeepSeek + Qdrant + 백엔드-프론트엔드 연결 전체 검증
"""

import os
import sys
import asyncio
import json
from datetime import datetime
from dotenv import load_dotenv

# 환경 변수 로드
load_dotenv()

# 시스템 임포트
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

async def main():
    print("🚀 최종 통합 시스템 테스트 시작")
    print("=" * 60)

    # 1. 환경 설정 확인
    print("1️⃣ 환경 설정 확인...")
    env_status = {
        "GEMINI_API_KEY": bool(os.getenv("GEMINI_API_KEY")),
        "QDRANT_API_KEY": bool(os.getenv("QDRANT_API_KEY")), 
        "USE_LOCAL_DEEPSEEK": os.getenv("USE_LOCAL_DEEPSEEK", "false").lower() == "true",
        "DEEPSEEK_MODEL_NAME": os.getenv("DEEPSEEK_MODEL_NAME", "deepseek-r1:8b"),
        "QDRANT_HOST": os.getenv("QDRANT_HOST", "localhost"),
        "QDRANT_PORT": os.getenv("QDRANT_PORT", "6333")
    }

    for key, value in env_status.items():
        status = "✅" if value else "❌"
        print(f"   {status} {key}: {value}")

    if not all([env_status["GEMINI_API_KEY"], env_status["QDRANT_API_KEY"]]):
        print("❌ 필수 API 키가 설정되지 않았습니다!")
        return

    # 2. 서비스 임포트 테스트
    print("\n2️⃣ 서비스 임포트 테스트...")
    try:
        from app.services.deepseek_service import deepseek_service
        print("   ✅ DeepSeek 서비스 임포트 성공")
    except Exception as e:
        print(f"   ❌ DeepSeek 서비스 임포트 실패: {e}")
        return

    try:
        from app.services.qdrant_service import qdrant_service
        print("   ✅ Qdrant 서비스 임포트 성공")
    except Exception as e:
        print(f"   ❌ Qdrant 서비스 임포트 실패: {e}")
        return

    try:
        from app.services.rag_system import rag_system
        print("   ✅ RAG 시스템 임포트 성공")
    except Exception as e:
        print(f"   ❌ RAG 시스템 임포트 실패: {e}")
        return

    try:
        from app.services.ai_service import ai_service
        print("   ✅ AI 서비스 임포트 성공")
    except Exception as e:
        print(f"   ❌ AI 서비스 임포트 실패: {e}")
        return

    # 3. Ollama 연결 테스트
    print("\n3️⃣ Ollama 연결 테스트...")
    try:
        available = await deepseek_service.check_model_availability()
        if available:
            print("   ✅ Ollama 서버 및 DeepSeek 모델 사용 가능")
            ollama_ok = True
        else:
            print("   ❌ DeepSeek 모델을 사용할 수 없습니다")
            ollama_ok = False
    except Exception as e:
        print(f"   ❌ Ollama 연결 실패: {e}")
        ollama_ok = False

    # 4. Qdrant 연결 테스트
    print("\n4️⃣ Qdrant 연결 테스트...")
    try:
        info = qdrant_service.get_collection_info()
        if info["success"]:
            print("   ✅ Qdrant 서버 연결 성공")
            print(f"   📊 컬렉션: {info.get('collection_name', 'N/A')}")
            qdrant_ok = True
        else:
            print(f"   ❌ Qdrant 연결 실패: {info.get('error', 'Unknown')}")
            qdrant_ok = False
    except Exception as e:
        print(f"   ❌ Qdrant 테스트 실패: {e}")
        qdrant_ok = False

    # 5. DeepSeek 채팅 테스트
    print("\n5️⃣ DeepSeek 채팅 테스트...")
    try:
        messages = [
            {"role": "system", "content": "당신은 간호학과 학습 도우미입니다."},
            {"role": "user", "content": "혈압 측정 시 주의사항을 간단히 설명해주세요."}
        ]
        
        result = await deepseek_service.chat_completion(messages, max_tokens=200)
        
        if result["success"]:
            print("   ✅ DeepSeek 채팅 응답 성공")
            print(f"   💬 응답: {result['content'][:100]}...")
            deepseek_chat_ok = True
        else:
            print(f"   ❌ DeepSeek 채팅 실패: {result.get('error', 'Unknown')}")
            deepseek_chat_ok = False
    except Exception as e:
        print(f"   ❌ DeepSeek 채팅 테스트 실패: {e}")
        deepseek_chat_ok = False

    # 6. DeepSeek 임베딩 테스트
    print("\n6️⃣ DeepSeek 임베딩 테스트...")
    try:
        test_texts = [
            "심장의 구조와 기능에 대해 설명하시오.",
            "혈압 측정의 올바른 방법은 무엇인가?"
        ]
        
        result = await deepseek_service.create_embeddings(test_texts)
        
        if result["success"] and result["embeddings"]:
            print(f"   ✅ DeepSeek 임베딩 생성 성공 (차원: {len(result['embeddings'][0])})")
            deepseek_embed_ok = True
        else:
            print(f"   ❌ DeepSeek 임베딩 실패: {result.get('error', 'Unknown')}")
            deepseek_embed_ok = False
    except Exception as e:
        print(f"   ❌ DeepSeek 임베딩 테스트 실패: {e}")
        deepseek_embed_ok = False

    # 7. Qdrant 벡터 연산 테스트
    print("\n7️⃣ Qdrant 벡터 연산 테스트...")
    try:
        # 테스트 데이터 추가
        test_texts = ["심장의 구조", "혈압 측정법"]
        test_metadata = [
            {"type": "question", "subject": "해부생리학"},
            {"type": "question", "subject": "기본간호학"}
        ]
        
        # 벡터 추가
        add_result = await qdrant_service.add_vectors(
            texts=test_texts,
            metadatas=test_metadata
        )
        
        if not add_result["success"]:
            print(f"   ❌ 벡터 추가 실패: {add_result.get('error', 'Unknown')}")
            qdrant_ops_ok = False
        else:
            print(f"   ✅ 벡터 추가 성공 ({add_result['added_count']}개)")
            
            # 벡터 검색
            search_result = await qdrant_service.search_vectors(
                query_text="심장과 관련된 내용",
                limit=2
            )
            
            if search_result["success"] and search_result["results"]:
                print(f"   ✅ 벡터 검색 성공 ({len(search_result['results'])}개 결과)")
                qdrant_ops_ok = True
            else:
                print(f"   ❌ 벡터 검색 실패: {search_result.get('error', 'Unknown')}")
                qdrant_ops_ok = False
                
    except Exception as e:
        print(f"   ❌ Qdrant 벡터 연산 테스트 실패: {e}")
        qdrant_ops_ok = False

    # 8. RAG 시스템 테스트
    print("\n8️⃣ RAG 시스템 테스트...")
    try:
        # 문서 추가
        documents = [
            "혈압은 심장이 수축할 때 동맥벽에 가해지는 압력입니다. 정상 혈압은 수축기 120mmHg, 이완기 80mmHg 미만입니다.",
            "체온 측정은 구강, 직장, 겨드랑이, 고막에서 할 수 있으며, 정상 체온은 36.5-37.5°C입니다."
        ]
        
        for i, doc in enumerate(documents):
            await rag_system.add_document(f"doc_{i}", doc, {"type": "기본간호학"})
        
        print("   ✅ RAG 문서 추가 완료")
        
        # RAG 질의응답
        query = "정상 혈압 수치는 얼마인가요?"
        response = await rag_system.generate_answer(query, department="간호학과")
        
        if response and "120" in response:
            print("   ✅ RAG 질의응답 성공")
            print(f"   💡 응답: {response[:100]}...")
            rag_ok = True
        else:
            print("   ❌ RAG 질의응답 실패")
            rag_ok = False
            
    except Exception as e:
        print(f"   ❌ RAG 시스템 테스트 실패: {e}")
        rag_ok = False

    # 9. AI 서비스 테스트
    print("\n9️⃣ AI 서비스 테스트...")
    try:
        # 문제 생성 테스트
        topic = "혈압 측정"
        difficulty = "중"
        
        question_result = await ai_service.generate_question(
            topic=topic,
            difficulty=difficulty,
            question_type="multiple_choice",
            department="간호학과"
        )
        
        if question_result["success"]:
            print("   ✅ AI 문제 생성 성공")
            print(f"   📝 문제: {question_result['question'][:50]}...")
            ai_ok = True
        else:
            print(f"   ❌ AI 문제 생성 실패: {question_result.get('error', 'Unknown')}")
            ai_ok = False
            
    except Exception as e:
        print(f"   ❌ AI 서비스 테스트 실패: {e}")
        ai_ok = False

    # 10. 종합 결과
    print("\n" + "=" * 60)
    print("📊 최종 통합 테스트 결과")
    print("=" * 60)

    test_results = [
        ("환경 설정", all([env_status["GEMINI_API_KEY"], env_status["QDRANT_API_KEY"]])),
        ("Ollama 연결", ollama_ok),
        ("Qdrant 연결", qdrant_ok), 
        ("DeepSeek 채팅", deepseek_chat_ok),
        ("DeepSeek 임베딩", deepseek_embed_ok),
        ("Qdrant 벡터 연산", qdrant_ops_ok),
        ("RAG 시스템", rag_ok),
        ("AI 서비스", ai_ok)
    ]

    success_count = 0
    for test_name, result in test_results:
        status = "✅" if result else "❌"
        print(f"{status} {test_name}")
        if result:
            success_count += 1

    total_tests = len(test_results)
    success_rate = (success_count / total_tests) * 100

    print(f"\n📈 성공률: {success_count}/{total_tests} ({success_rate:.1f}%)")

    if success_rate >= 80:
        print("🎉 시스템이 정상적으로 작동합니다!")
        print("\n✅ 백엔드 실행 준비 완료")
        print("✅ 프론트엔드 연결 준비 완료") 
        print("✅ DeepSeek + Qdrant 아키텍처 완성")
        
        print("\n🚀 실행 명령어:")
        print("백엔드: uvicorn main:app --reload --host 0.0.0.0 --port 8000")
        print("프론트엔드: 기존 프론트엔드 서버 실행")
        
    elif success_rate >= 60:
        print("⚠️ 일부 기능에 문제가 있지만 기본 동작은 가능합니다.")
    else:
        print("❌ 시스템에 심각한 문제가 있습니다. 설정을 다시 확인하세요.")

    # 결과 저장
    result_data = {
        "timestamp": datetime.now().isoformat(),
        "success_rate": success_rate,
        "test_results": dict(test_results),
        "environment": env_status
    }

    with open("final_test_results.json", "w", encoding="utf-8") as f:
        json.dump(result_data, f, ensure_ascii=False, indent=2)

    print(f"\n📁 상세 결과가 final_test_results.json에 저장되었습니다.")

if __name__ == "__main__":
    asyncio.run(main()) 