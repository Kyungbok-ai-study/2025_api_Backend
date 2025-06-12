"""
앙상블 AI 시스템 서비스
DeepSeek + Gemini + OpenAI GPT 3단계 파이프라인 처리
"""

import asyncio
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime
import time

from app.services.deepseek_service import deepseek_service
from app.services.gemini_service import gemini_service
from app.services.openai_service import openai_service

logger = logging.getLogger(__name__)

class EnsembleService:
    """앙상블 AI 서비스 클래스"""
    
    def __init__(self):
        self.stats = {
            "total_requests": 0,
            "successful_completions": 0,
            "failed_requests": 0,
            "stage_failures": {
                "deepseek": 0,
                "gemini": 0,
                "openai": 0
            }
        }
    
    async def process_educational_content(
        self,
        question: str,
        difficulty_level: str = "medium",
        department: str = "일반학과",
        target_audience: str = "university_students"
    ) -> Dict[str, Any]:
        """
        교육 콘텐츠 3단계 앙상블 처리
        
        1단계: DeepSeek - 문제 분석 및 핵심 개념 추출
        2단계: Gemini - 교육적 설명 생성
        3단계: OpenAI - 한국어 문체 개선
        """
        start_time = time.time()
        self.stats["total_requests"] += 1
        
        try:
            logger.info(f"앙상블 처리 시작: {question[:50]}...")
            
            # 처리 결과 저장 구조
            result = {
                "success": False,
                "question": question,
                "final_content": "",
                "processing_stages": {},
                "metadata": {
                    "difficulty_level": difficulty_level,
                    "department": department,
                    "target_audience": target_audience,
                    "processing_time_seconds": 0,
                    "timestamp": datetime.now().isoformat()
                }
            }
            
            # 1단계: DeepSeek 분석
            logger.info("1단계: DeepSeek 분석 시작")
            try:
                deepseek_result = await deepseek_service.analyze_educational_content(
                    question=question,
                    difficulty_level=difficulty_level,
                    department=department
                )
                
                result["processing_stages"]["deepseek_analysis"] = deepseek_result
                
                if not deepseek_result.get("success", False):
                    self.stats["stage_failures"]["deepseek"] += 1
                    raise Exception("DeepSeek 분석 실패")
                
                logger.info("✅ DeepSeek 분석 완료")
                
            except Exception as e:
                logger.error(f"❌ DeepSeek 분석 오류: {e}")
                self.stats["stage_failures"]["deepseek"] += 1
                result["processing_stages"]["deepseek_analysis"] = {
                    "success": False,
                    "error": str(e)
                }
                raise e
            
            # 2단계: Gemini 교육적 설명 생성
            logger.info("2단계: Gemini 설명 생성 시작")
            try:
                # DeepSeek에서 추출한 핵심 개념 사용
                core_concepts = deepseek_result.get("analysis", {}).get("core_concepts", [])
                if not core_concepts:
                    core_concepts = [question]  # 기본값으로 질문 자체 사용
                
                gemini_result = await gemini_service.generate_educational_explanation(
                    question=question,
                    core_concepts=core_concepts,
                    difficulty_level=difficulty_level,
                    department=department,
                    target_audience=target_audience
                )
                
                result["processing_stages"]["gemini_explanation"] = gemini_result
                
                if not gemini_result.get("success", False):
                    self.stats["stage_failures"]["gemini"] += 1
                    raise Exception("Gemini 설명 생성 실패")
                
                logger.info("✅ Gemini 설명 생성 완료")
                
            except Exception as e:
                logger.error(f"❌ Gemini 설명 생성 오류: {e}")
                self.stats["stage_failures"]["gemini"] += 1
                result["processing_stages"]["gemini_explanation"] = {
                    "success": False,
                    "error": str(e)
                }
                raise e
            
            # 3단계: OpenAI 문체 개선
            logger.info("3단계: OpenAI 문체 개선 시작")
            try:
                # Gemini에서 생성된 설명 내용 사용
                content_to_improve = gemini_result.get("content", {}).get("explanation", "")
                if not content_to_improve:
                    content_to_improve = gemini_result.get("explanation", "")
                
                openai_result = await openai_service.improve_text_style(
                    content=content_to_improve,
                    style_type="educational",
                    target_audience=target_audience,
                    department=department
                )
                
                result["processing_stages"]["openai_improvement"] = openai_result
                
                if not openai_result.get("success", False):
                    self.stats["stage_failures"]["openai"] += 1
                    raise Exception("OpenAI 문체 개선 실패")
                
                logger.info("✅ OpenAI 문체 개선 완료")
                
                # 최종 결과 설정
                result["final_content"] = openai_result.get("improved_content", content_to_improve)
                
            except Exception as e:
                logger.error(f"❌ OpenAI 문체 개선 오류: {e}")
                self.stats["stage_failures"]["openai"] += 1
                result["processing_stages"]["openai_improvement"] = {
                    "success": False,
                    "error": str(e)
                }
                # OpenAI 실패시 Gemini 결과를 최종 결과로 사용
                result["final_content"] = gemini_result.get("content", {}).get("explanation", "")
            
            # 처리 완료
            processing_time = time.time() - start_time
            result["metadata"]["processing_time_seconds"] = processing_time
            result["success"] = True
            
            self.stats["successful_completions"] += 1
            logger.info(f"✅ 앙상블 처리 완료 (소요시간: {processing_time:.2f}초)")
            
            return result
            
        except Exception as e:
            self.stats["failed_requests"] += 1
            processing_time = time.time() - start_time
            
            logger.error(f"❌ 앙상블 처리 실패: {e}")
            
            return {
                "success": False,
                "question": question,
                "error": str(e),
                "processing_stages": result.get("processing_stages", {}),
                "metadata": {
                    "difficulty_level": difficulty_level,
                    "department": department,
                    "target_audience": target_audience,
                    "processing_time_seconds": processing_time,
                    "timestamp": datetime.now().isoformat()
                }
            }
    
    async def batch_process(
        self, 
        questions: List[Dict[str, Any]], 
        max_concurrent: int = 3
    ) -> List[Dict[str, Any]]:
        """배치 처리"""
        logger.info(f"배치 처리 시작: {len(questions)}개 질문, 최대 동시 처리: {max_concurrent}")
        
        # 세마포어를 사용하여 동시 처리 수 제한
        semaphore = asyncio.Semaphore(max_concurrent)
        
        async def process_single_question(question_data: Dict[str, Any]) -> Dict[str, Any]:
            async with semaphore:
                return await self.process_educational_content(
                    question=question_data.get("question", ""),
                    difficulty_level=question_data.get("difficulty_level", "medium"),
                    department=question_data.get("department", "일반학과"),
                    target_audience=question_data.get("target_audience", "university_students")
                )
        
        # 모든 질문을 병렬로 처리
        tasks = [process_single_question(q) for q in questions]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # 예외 처리
        processed_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                processed_results.append({
                    "success": False,
                    "question": questions[i].get("question", ""),
                    "error": str(result)
                })
            else:
                processed_results.append(result)
        
        logger.info(f"배치 처리 완료: {len(processed_results)}개 결과")
        return processed_results
    
    async def get_system_status(self) -> Dict[str, Any]:
        """시스템 상태 조회"""
        total_requests = self.stats["total_requests"]
        successful_requests = self.stats["successful_completions"]
        
        # 시스템 건강도 계산
        if total_requests == 0:
            success_rate = 1.0
            system_health = "healthy"
        else:
            success_rate = successful_requests / total_requests
            if success_rate >= 0.9:
                system_health = "healthy"
            elif success_rate >= 0.7:
                system_health = "warning"
            else:
                system_health = "critical"
        
        return {
            "system_health": system_health,
            "success_rate": success_rate,
            "ensemble_stats": self.stats.copy(),
            "services_status": {
                "deepseek": "available",
                "gemini": "available", 
                "openai": "available"
            },
            "timestamp": datetime.now().isoformat()
        }

# 전역 인스턴스 생성
ensemble_service = EnsembleService() 