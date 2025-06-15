"""
앙상블 AI 서비스
Gemini + Exaone 2단계 파이프라인 처리
"""

import asyncio
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime
import time

from app.services.gemini_service import gemini_service
from app.services.exaone_service import exaone_service

logger = logging.getLogger(__name__)

class EnsembleService:
    """앙상블 AI 서비스 - Gemini + Exaone 2단계 파이프라인"""
    
    def __init__(self):
        self.stats = {
            "total_requests": 0,
            "successful_completions": 0,
            "failed_completions": 0,
            "stage_failures": {
                "gemini": 0,
                "exaone": 0
            },
            "average_processing_time": 0.0
        }
        
        logger.info("✅ 앙상블 서비스 초기화 완료 (Gemini + Exaone)")

    async def process_educational_content(
        self,
        question: str,
        difficulty_level: str = "medium",
        department: str = "일반학과",
        target_audience: str = "university_students"
    ) -> Dict[str, Any]:
        """
        교육 컨텐츠 2단계 앙상블 처리
        
        1단계: Gemini - 구조화된 교육적 설명 생성
        2단계: Exaone - 한국어 문체 개선 및 최종 다듬기
        
        Args:
            question: 처리할 질문/주제
            difficulty_level: 난이도 수준
            department: 학과
            target_audience: 대상 사용자
        """
        start_time = datetime.now()
        self.stats["total_requests"] += 1
        
        result = {
            "success": False,
            "processing_stages": {},
            "final_content": "",
            "metadata": {
                "question": question,
                "difficulty_level": difficulty_level,
                "department": department,
                "target_audience": target_audience,
                "processing_time": 0,
                "stages_completed": 0
            }
        }
        
        try:
            # 1단계: Gemini 교육적 설명 생성
            logger.info("1단계: Gemini 교육적 설명 생성 시작")
            
            try:
                gemini_result = await gemini_service.generate_educational_explanation(
                    question=question,
                    core_concepts=[question],  # 기본값으로 질문 자체 사용
                    difficulty_level=difficulty_level,
                    department=department,
                    target_audience=target_audience
                )
                
                result["processing_stages"]["gemini_explanation"] = gemini_result
                
                if not gemini_result.get("success", False):
                    self.stats["stage_failures"]["gemini"] += 1
                    raise Exception("Gemini 설명 생성 실패")
                
                result["metadata"]["stages_completed"] = 1
                logger.info("✅ Gemini 설명 생성 완료")
                
            except Exception as e:
                logger.error(f"❌ Gemini 설명 생성 오류: {e}")
                self.stats["stage_failures"]["gemini"] += 1
                result["processing_stages"]["gemini_explanation"] = {
                    "success": False,
                    "error": str(e)
                }
                raise e
            
            # 2단계: Exaone 문체 개선 및 최종 다듬기
            logger.info("2단계: Exaone 문체 개선 시작")
            
            try:
                # Gemini에서 생성된 설명 내용 사용
                content_to_improve = gemini_result.get("content", {}).get("explanation", "")
                if not content_to_improve:
                    content_to_improve = gemini_result.get("explanation", "")
                
                exaone_result = await exaone_service.improve_text_style(
                    text=content_to_improve,
                    target_style="educational",
                    department=department
                )
                
                result["processing_stages"]["exaone_improvement"] = exaone_result
                
                if not exaone_result.get("success", False):
                    self.stats["stage_failures"]["exaone"] += 1
                    raise Exception("Exaone 문체 개선 실패")
                
                result["metadata"]["stages_completed"] = 2
                logger.info("✅ Exaone 문체 개선 완료")
                
                # 최종 컨텐츠 설정
                result["final_content"] = exaone_result.get("improved_content", content_to_improve)
                
            except Exception as e:
                logger.error(f"❌ Exaone 문체 개선 오류: {e}")
                self.stats["stage_failures"]["exaone"] += 1
                result["processing_stages"]["exaone_improvement"] = {
                    "success": False,
                    "error": str(e)
                }
                
                # Exaone 실패시 Gemini 결과를 최종 결과로 사용
                content_to_improve = gemini_result.get("content", {}).get("explanation", "")
                if not content_to_improve:
                    content_to_improve = gemini_result.get("explanation", "")
                result["final_content"] = content_to_improve
            
            # 처리 완료
            end_time = datetime.now()
            processing_time = (end_time - start_time).total_seconds()
            
            result["success"] = True
            result["metadata"]["processing_time"] = processing_time
            result["metadata"]["completed_at"] = end_time.isoformat()
            
            # 통계 업데이트
            self.stats["successful_completions"] += 1
            self._update_average_processing_time(processing_time)
            
            logger.info(f"✅ 앙상블 처리 완료 ({processing_time:.2f}초)")
            
            return result
            
        except Exception as e:
            # 전체 실패 처리
            end_time = datetime.now()
            processing_time = (end_time - start_time).total_seconds()
            
            result["metadata"]["processing_time"] = processing_time
            result["metadata"]["error"] = str(e)
            result["metadata"]["failed_at"] = end_time.isoformat()
            
            self.stats["failed_completions"] += 1
            
            logger.error(f"❌ 앙상블 처리 실패: {e}")
            
            return result

    async def process_document_content(
        self,
        file_path: str,
        department: str = "일반학과",
        processing_type: str = "comprehensive"
    ) -> Dict[str, Any]:
        """
        문서 컨텐츠 2단계 앙상블 처리
        
        1단계: Gemini - PDF 파싱 및 구조화
        2단계: Exaone - 컨텐츠 분석 및 분류
        """
        start_time = datetime.now()
        self.stats["total_requests"] += 1
        
        result = {
            "success": False,
            "processing_stages": {},
            "processed_content": {},
            "metadata": {
                "file_path": file_path,
                "department": department,
                "processing_type": processing_type,
                "processing_time": 0,
                "stages_completed": 0
            }
        }
        
        try:
            # 1단계: Gemini PDF 파싱
            logger.info("1단계: Gemini PDF 파싱 시작")
            
            parsing_result = await gemini_service.parse_pdf_document(
                file_path=file_path,
                department=department,
                extraction_type=processing_type
            )
            
            result["processing_stages"]["gemini_parsing"] = parsing_result
            
            if not parsing_result["success"]:
                self.stats["stage_failures"]["gemini"] += 1
                raise Exception("Gemini PDF 파싱 실패")
            
            result["metadata"]["stages_completed"] = 1
            logger.info("✅ Gemini PDF 파싱 완료")
            
            # 2단계: Exaone 컨텐츠 분석 및 분류
            logger.info("2단계: Exaone 컨텐츠 분석 시작")
            
            content = parsing_result.get("content", "")
            
            # 컨텐츠 분류
            classification_result = await exaone_service.classify_content(
                content=content,
                classification_type="department"
            )
            
            # 난이도 분석
            difficulty_result = await exaone_service.analyze_difficulty(
                question_content=content[:1000],  # 첫 1000자로 분석
                department=department
            )
            
            result["processing_stages"]["exaone_analysis"] = {
                "classification": classification_result,
                "difficulty_analysis": difficulty_result
            }
            
            result["metadata"]["stages_completed"] = 2
            logger.info("✅ Exaone 컨텐츠 분석 완료")
            
            # 최종 처리된 컨텐츠
            result["processed_content"] = {
                "raw_content": content,
                "parsed_metadata": parsing_result.get("metadata", {}),
                "classification": classification_result.get("classification", {}),
                "difficulty_analysis": difficulty_result.get("analysis", {}),
                "processed_by": ["Gemini", "Exaone"]
            }
            
            # 처리 완료
            end_time = datetime.now()
            processing_time = (end_time - start_time).total_seconds()
            
            result["success"] = True
            result["metadata"]["processing_time"] = processing_time
            result["metadata"]["completed_at"] = end_time.isoformat()
            
            self.stats["successful_completions"] += 1
            self._update_average_processing_time(processing_time)
            
            logger.info(f"✅ 문서 앙상블 처리 완료 ({processing_time:.2f}초)")
            
            return result
            
        except Exception as e:
            end_time = datetime.now()
            processing_time = (end_time - start_time).total_seconds()
            
            result["metadata"]["processing_time"] = processing_time
            result["metadata"]["error"] = str(e)
            result["metadata"]["failed_at"] = end_time.isoformat()
            
            self.stats["failed_completions"] += 1
            
            logger.error(f"❌ 문서 앙상블 처리 실패: {e}")
            
            return result

    async def generate_adaptive_question(
        self,
        topic: str,
        user_performance: Dict[str, Any],
        department: str = "일반학과"
    ) -> Dict[str, Any]:
        """
        적응형 문제 생성 (2단계 앙상블)
        
        1단계: Gemini - 구조화된 문제 개념 분석
        2단계: Exaone - 실제 문제 생성 및 최적화
        """
        try:
            # 사용자 성능 기반 난이도 조정
            user_score = user_performance.get("average_score", 70)
            if user_score >= 80:
                difficulty = "상"
            elif user_score >= 60:
                difficulty = "중"
            else:
                difficulty = "하"
            
            # 1단계: Gemini 개념 분석 (구조화된 설명 생성으로 대체)
            concept_analysis = await gemini_service.generate_educational_explanation(
                question=f"{topic} 관련 문제 출제를 위한 개념 분석",
                core_concepts=[topic],
                difficulty_level=difficulty,
                department=department,
                target_audience="students"
            )
            
            # 2단계: Exaone 문제 생성
            question_result = await exaone_service.generate_question(
                topic=topic,
                difficulty=difficulty,
                department=department,
                question_type="multiple_choice"
            )
            
            if question_result["success"]:
                return {
                    "success": True,
                    "question": question_result["question"],
                    "concept_analysis": concept_analysis,
                    "adapted_difficulty": difficulty,
                    "user_performance": user_performance,
                    "generated_by": "Gemini + Exaone Ensemble"
                }
            
        except Exception as e:
            logger.error(f"적응형 문제 생성 실패: {e}")
        
        return {
            "success": False,
            "error": "적응형 문제 생성 실패"
        }

    def _update_average_processing_time(self, processing_time: float):
        """평균 처리 시간 업데이트"""
        total_successful = self.stats["successful_completions"]
        current_avg = self.stats["average_processing_time"]
        
        new_avg = ((current_avg * (total_successful - 1)) + processing_time) / total_successful
        self.stats["average_processing_time"] = new_avg

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
        
        # 서비스 상태 확인
        gemini_status = "available" if gemini_service.model else "unavailable"
        exaone_status = "available"  # Exaone 상태 확인 로직 추가 가능
        
        return {
            "system_health": system_health,
            "success_rate": success_rate,
            "ensemble_stats": self.stats.copy(),
            "services_status": {
                "gemini": gemini_status,
                "exaone": exaone_status
            },
            "pipeline_stages": ["Gemini", "Exaone"],
            "timestamp": datetime.now().isoformat()
        }

    async def clear_caches(self):
        """모든 서비스 캐시 정리"""
        try:
            await exaone_service.clear_cache()
            logger.info("✅ 앙상블 서비스 캐시 정리 완료")
        except Exception as e:
            logger.error(f"캐시 정리 실패: {e}")

# 싱글톤 인스턴스
ensemble_service = EnsembleService() 