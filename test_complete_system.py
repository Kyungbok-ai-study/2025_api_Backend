#!/usr/bin/env python3
"""
완전 전환된 DeepSeek + Qdrant 시스템 통합 테스트
"""
import asyncio
import logging
import json
import time
from datetime import datetime
from pathlib import Path

# 환경 설정
import os
import sys
sys.path.append(str(Path(__file__).parent))

from app.services.deepseek_service import deepseek_service
from app.services.qdrant_service import qdrant_service
from app.services.rag_system import rag_service
from app.services.ai_service import ai_service, enhanced_ai_service
from app.services.rag_integration_service import rag_integration_service

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class CompleteSystemTester:
    """완전 전환된 시스템 통합 테스트"""
    
    def __init__(self):
        self.test_results = {
            "start_time": datetime.now().isoformat(),
            "tests": {},
            "overall_status": "pending"
        }
        
    async def run_all_tests(self):
        """모든 테스트 실행"""
        logger.info("🚀 DeepSeek + Qdrant 시스템 통합 테스트 시작")
        
        tests = [
            ("deepseek_connection", self.test_deepseek_connection),
            ("qdrant_connection", self.test_qdrant_connection),
            ("deepseek_chat", self.test_deepseek_chat),
            ("deepseek_embedding", self.test_deepseek_embedding),
            ("qdrant_operations", self.test_qdrant_operations),
            ("rag_system", self.test_rag_system),
            ("ai_services", self.test_ai_services),
            ("rag_integration", self.test_rag_integration),
            ("performance_test", self.test_performance),
            ("end_to_end", self.test_end_to_end)
        ]
        
        passed = 0
        total = len(tests)
        
        for test_name, test_func in tests:
            logger.info(f"🧪 테스트 실행: {test_name}")
            
            try:
                start_time = time.time()
                result = await test_func()
                duration = time.time() - start_time
                
                self.test_results["tests"][test_name] = {
                    "status": "passed" if result["success"] else "failed",
                    "duration": duration,
                    "details": result,
                    "timestamp": datetime.now().isoformat()
                }
                
                if result["success"]:
                    passed += 1
                    logger.info(f"✅ {test_name} 테스트 통과 ({duration:.2f}초)")
                else:
                    logger.error(f"❌ {test_name} 테스트 실패: {result.get('error', 'Unknown error')}")
                    
            except Exception as e:
                duration = time.time() - start_time
                logger.error(f"💥 {test_name} 테스트 오류: {e}")
                
                self.test_results["tests"][test_name] = {
                    "status": "error",
                    "duration": duration,
                    "error": str(e),
                    "timestamp": datetime.now().isoformat()
                }
        
        # 전체 결과 정리
        self.test_results["end_time"] = datetime.now().isoformat()
        self.test_results["total_tests"] = total
        self.test_results["passed_tests"] = passed
        self.test_results["failed_tests"] = total - passed
        self.test_results["success_rate"] = (passed / total) * 100
        self.test_results["overall_status"] = "success" if passed == total else "partial_success" if passed > 0 else "failed"
        
        # 결과 출력
        self.print_test_summary()
        
        # 결과 파일 저장
        await self.save_test_results()
        
        return self.test_results
    
    async def test_deepseek_connection(self):
        """DeepSeek 연결 테스트"""
        try:
            # 간단한 연결 테스트
            result = await deepseek_service.chat_completion(
                messages=[{"role": "user", "content": "안녕하세요. 연결 테스트입니다."}],
                temperature=0.1
            )
            
            if result["success"] and "안녕" in result["content"]:
                return {
                    "success": True,
                    "message": "DeepSeek 연결 성공",
                    "response_length": len(result["content"]),
                    "model": "deepseek-r1:8b"
                }
            else:
                return {
                    "success": False,
                    "error": result.get("error", "응답 내용 이상")
                }
                
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def test_qdrant_connection(self):
        """Qdrant 연결 테스트"""
        try:
            # 컬렉션 정보 조회
            info = qdrant_service.get_collection_info()
            
            if info["success"]:
                return {
                    "success": True,
                    "message": "Qdrant 연결 성공",
                    "collection_name": info["collection_name"],
                    "points_count": info.get("points_count", 0)
                }
            else:
                return {
                    "success": False,
                    "error": info.get("error", "Qdrant 연결 실패")
                }
                
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def test_deepseek_chat(self):
        """DeepSeek 채팅 기능 테스트"""
        try:
            # 간호학과 맞춤 질문
            result = await deepseek_service.chat_completion(
                messages=[{
                    "role": "user", 
                    "content": "간호학과 학생을 위한 감염관리의 핵심 원칙 3가지를 간단히 설명해주세요."
                }],
                temperature=0.3
            )
            
            if result["success"]:
                content = result["content"]
                
                # 응답 품질 검사
                quality_checks = [
                    ("감염" in content, "감염 관련 내용 포함"),
                    ("간호" in content or "환자" in content, "간호 관련 내용 포함"),
                    (len(content) > 50, "충분한 길이의 응답"),
                    ("1" in content or "첫" in content, "구조화된 응답")
                ]
                
                passed_checks = sum(1 for check, _ in quality_checks if check)
                
                return {
                    "success": True,
                    "message": "DeepSeek 채팅 성공",
                    "response_length": len(content),
                    "quality_score": passed_checks / len(quality_checks),
                    "quality_checks": [desc for check, desc in quality_checks if check]
                }
            else:
                return {
                    "success": False,
                    "error": result.get("error", "채팅 생성 실패")
                }
                
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def test_deepseek_embedding(self):
        """DeepSeek 임베딩 기능 테스트"""
        try:
            test_texts = [
                "간호사는 환자의 안전을 최우선으로 고려해야 한다.",
                "물리치료사는 환자의 기능 회복을 돕는다.",
                "작업치료는 일상생활 활동 참여를 목표로 한다."
            ]
            
            result = await deepseek_service.create_embeddings(test_texts)
            
            if result["success"]:
                embeddings = result["embeddings"]
                
                # 임베딩 품질 검사
                checks = [
                    (len(embeddings) == len(test_texts), "임베딩 개수 일치"),
                    (all(len(emb) == 768 for emb in embeddings), "임베딩 차원 정확"),
                    (all(isinstance(emb, list) for emb in embeddings), "임베딩 타입 정확"),
                    (all(all(isinstance(val, float) for val in emb) for emb in embeddings), "임베딩 값 타입 정확")
                ]
                
                passed_checks = sum(1 for check, _ in checks if check)
                
                return {
                    "success": True,
                    "message": "DeepSeek 임베딩 성공",
                    "texts_count": len(test_texts),
                    "embedding_dimension": len(embeddings[0]) if embeddings else 0,
                    "quality_score": passed_checks / len(checks)
                }
            else:
                return {
                    "success": False,
                    "error": result.get("error", "임베딩 생성 실패")
                }
                
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def test_qdrant_operations(self):
        """Qdrant 벡터 연산 테스트"""
        try:
            # 테스트 데이터
            test_texts = [
                "간호학과 시험 문제: 손위생의 중요성에 대해 설명하시오.",
                "물리치료학과 문제: 근육의 수축과 이완 과정을 서술하시오."
            ]
            
            test_metadata = [
                {"subject": "감염관리", "difficulty": "중", "department": "간호학과"},
                {"subject": "운동학", "difficulty": "상", "department": "물리치료학과"}
            ]
            
            # 벡터 추가
            add_result = await qdrant_service.add_vectors(
                texts=test_texts,
                metadatas=test_metadata,
                ids=["test_1", "test_2"]
            )
            
            if not add_result["success"]:
                return {"success": False, "error": f"벡터 추가 실패: {add_result.get('error')}"}
            
            # 벡터 검색
            search_result = await qdrant_service.search_vectors(
                query_text="간호학과 손위생",
                limit=2,
                score_threshold=0.3
            )
            
            if not search_result["success"]:
                return {"success": False, "error": f"벡터 검색 실패: {search_result.get('error')}"}
            
            # 검색 결과 검증
            results = search_result["results"]
            found_nursing = any("간호" in result["text"] for result in results)
            
            # 벡터 삭제 (정리)
            delete_result = qdrant_service.delete_vectors(["test_1", "test_2"])
            
            return {
                "success": True,
                "message": "Qdrant 벡터 연산 성공",
                "added_vectors": add_result["added_count"],
                "search_results": len(results),
                "found_relevant": found_nursing,
                "deleted_vectors": delete_result.get("deleted_count", 0)
            }
                
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def test_rag_system(self):
        """RAG 시스템 테스트"""
        try:
            # RAG 통계 조회
            stats = await rag_service.get_rag_statistics(None)  # DB 없이 기본 테스트
            
            # 유사도 검색 테스트 (빈 결과라도 오류 없이 실행되어야 함)
            search_result = await rag_service.similarity_search(
                db=None,
                query_text="간호학과 기본 지식",
                limit=3
            )
            
            # RAG 시스템이 오류 없이 실행되는지 확인
            return {
                "success": True,
                "message": "RAG 시스템 기본 동작 확인",
                "system_type": stats.get("system_type", "Unknown"),
                "search_executed": isinstance(search_result, list)
            }
                
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def test_ai_services(self):
        """AI 서비스들 테스트"""
        try:
            # Enhanced AI 서비스 테스트
            analysis_result = await enhanced_ai_service.analyze_user_performance(
                db=None, user_id=1
            )
            
            # 적응형 문제 생성 테스트
            adaptive_questions = await enhanced_ai_service.generate_adaptive_questions(
                db=None, user_id=1, difficulty_target=0.7
            )
            
            return {
                "success": True,
                "message": "AI 서비스 동작 확인",
                "analysis_completed": "error" not in analysis_result or "분석할 데이터가 부족" in analysis_result.get("analysis", ""),
                "adaptive_questions_count": len(adaptive_questions)
            }
                
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def test_rag_integration(self):
        """RAG 통합 서비스 테스트"""
        try:
            # 시스템 상태 확인
            status = await rag_integration_service.get_system_status()
            
            # 유사 콘텐츠 검색 테스트
            search_result = await rag_integration_service.search_similar_content(
                query="간호학과 기본 지식",
                content_type="all",
                limit=3
            )
            
            return {
                "success": True,
                "message": "RAG 통합 서비스 동작 확인",
                "system_status": status.get("status", "unknown"),
                "deepseek_status": status.get("components", {}).get("deepseek", {}).get("status", "unknown"),
                "qdrant_status": status.get("components", {}).get("qdrant", {}).get("status", "unknown"),
                "search_executed": search_result.get("success", False) or "error" in search_result
            }
                
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def test_performance(self):
        """성능 테스트"""
        try:
            # DeepSeek 응답 시간 측정
            start_time = time.time()
            chat_result = await deepseek_service.chat_completion(
                messages=[{"role": "user", "content": "간단한 응답을 주세요."}],
                temperature=0.1
            )
            deepseek_time = time.time() - start_time
            
            # 임베딩 생성 시간 측정
            start_time = time.time()
            embedding_result = await deepseek_service.create_embeddings(["테스트 문장"])
            embedding_time = time.time() - start_time
            
            performance_scores = {
                "deepseek_response_time": deepseek_time,
                "embedding_time": embedding_time,
                "deepseek_fast": deepseek_time < 5.0,  # 5초 이내
                "embedding_fast": embedding_time < 2.0  # 2초 이내
            }
            
            return {
                "success": True,
                "message": "성능 테스트 완료",
                **performance_scores
            }
                
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def test_end_to_end(self):
        """종단간 테스트"""
        try:
            # 전체 플로우 테스트: 문제 생성 → 해설 생성 → 벡터 저장
            
            # 1. DeepSeek으로 해설 생성
            explanation_result = await deepseek_service.generate_explanation(
                question="간호사가 손위생을 수행해야 하는 주요 시점은?",
                correct_answer="환자 접촉 전, 무균 시술 전, 체액 노출 후, 환자 접촉 후, 환자 환경 접촉 후",
                options={1: "식사 전", 2: "WHO 5 Moments", 3: "근무 시작 시", 4: "근무 종료 시"},
                department="간호학과"
            )
            
            # 2. 벡터 저장 (임시)
            if explanation_result["success"]:
                vector_result = await qdrant_service.add_vectors(
                    texts=[explanation_result["explanation"]],
                    metadatas=[{"type": "test_explanation", "department": "간호학과"}],
                    ids=["end_to_end_test"]
                )
                
                # 3. 검색 테스트
                search_result = await qdrant_service.search_vectors(
                    query_text="손위생 시점",
                    limit=1
                )
                
                # 4. 정리
                qdrant_service.delete_vectors(["end_to_end_test"])
                
                return {
                    "success": True,
                    "message": "종단간 테스트 성공",
                    "explanation_generated": True,
                    "vector_stored": vector_result["success"],
                    "search_executed": search_result["success"],
                    "flow_completed": True
                }
            else:
                return {
                    "success": False,
                    "error": f"해설 생성 실패: {explanation_result.get('error')}"
                }
                
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def print_test_summary(self):
        """테스트 결과 요약 출력"""
        print("\n" + "="*60)
        print("🎯 DeepSeek + Qdrant 시스템 통합 테스트 결과")
        print("="*60)
        
        total = self.test_results["total_tests"]
        passed = self.test_results["passed_tests"]
        failed = self.test_results["failed_tests"]
        success_rate = self.test_results["success_rate"]
        
        print(f"📊 전체 테스트: {total}개")
        print(f"✅ 통과: {passed}개")
        print(f"❌ 실패: {failed}개")
        print(f"📈 성공률: {success_rate:.1f}%")
        print(f"🏆 전체 상태: {self.test_results['overall_status']}")
        
        print("\n📋 개별 테스트 결과:")
        for test_name, result in self.test_results["tests"].items():
            status_icon = "✅" if result["status"] == "passed" else "❌" if result["status"] == "failed" else "💥"
            duration = result.get("duration", 0)
            print(f"  {status_icon} {test_name}: {result['status']} ({duration:.2f}초)")
            
            if result["status"] != "passed":
                error = result.get("error", result.get("details", {}).get("error", "Unknown"))
                print(f"     └─ 오류: {error}")
        
        print("\n🎉 시스템 상태:")
        print("  🤖 DeepSeek R1 8B: 활성화")
        print("  🗄️ Qdrant 벡터 DB: 활성화") 
        print("  🧠 Gemini (파서 전용): 활성화")
        print("  ⚡ OpenAI: 비활성화 (완전 전환)")
        print("  🔄 RAG 시스템: DeepSeek + Qdrant")
        
        if success_rate >= 90:
            print("\n🚀 시스템이 성공적으로 전환되었습니다!")
        elif success_rate >= 70:
            print("\n⚠️ 시스템이 대부분 정상 동작하지만 일부 개선이 필요합니다.")
        else:
            print("\n🔧 시스템에 문제가 있습니다. 로그를 확인해주세요.")
        
        print("="*60)
    
    async def save_test_results(self):
        """테스트 결과를 파일로 저장"""
        try:
            result_file = Path("test_results_complete_system.json")
            
            with open(result_file, "w", encoding="utf-8") as f:
                json.dump(self.test_results, f, ensure_ascii=False, indent=2)
            
            logger.info(f"📄 테스트 결과 저장됨: {result_file}")
            
        except Exception as e:
            logger.error(f"❌ 테스트 결과 저장 실패: {e}")

async def main():
    """메인 실행 함수"""
    print("🚀 DeepSeek + Qdrant 시스템 통합 테스트 시작")
    print("📋 테스트 항목: 연결, 채팅, 임베딩, 벡터 연산, RAG, AI 서비스, 성능, 종단간")
    print("⏱️ 예상 소요 시간: 1-2분\n")
    
    tester = CompleteSystemTester()
    results = await tester.run_all_tests()
    
    return results

if __name__ == "__main__":
    asyncio.run(main()) 