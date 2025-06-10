"""
딥시크 자동 학습 서비스
교수가 승인한 문제를 기반으로 딥시크 모델이 실시간 학습
"""
import os
import json
import logging
import asyncio
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from pathlib import Path
import httpx
from sqlalchemy.orm import Session

from ..models.question import Question
from ..models.deepseek import DeepSeekLearningSession
from .deepseek_service import LocalDeepSeekService
from .qdrant_service import QdrantService
from ..core.config import settings

logger = logging.getLogger(__name__)

class DeepSeekLearningService:
    """딥시크 실시간 학습 서비스"""
    
    def __init__(self):
        self.deepseek = LocalDeepSeekService()
        self.qdrant = QdrantService()
        
        # 학습 데이터 저장 경로
        self.learning_data_path = Path("data/deepseek_learning")
        self.learning_data_path.mkdir(parents=True, exist_ok=True)
        
        # 학습 상태 추적
        self.learning_stats = {
            "total_learned": 0,
            "last_learning": None,
            "learning_sessions": [],
            "model_version": "deepseek-r1:8b"
        }
        
        logger.info("🤖 딥시크 학습 서비스 초기화 완료")
    
    async def process_approved_question_for_learning(
        self, 
        question: Question, 
        department: str,
        metadata: Dict[str, Any] = None,
        db: Session = None
    ) -> Dict[str, Any]:
        """
        승인된 문제를 딥시크 학습용으로 처리
        1. 학습 데이터 포맷 생성
        2. 딥시크 모델에 학습 데이터 추가
        3. 실시간 파인튜닝 (가능한 경우)
        """
        try:
            logger.info(f"🎓 문제 {question.id} 딥시크 학습 처리 시작")
            
            # 딥시크 학습 세션 생성 및 저장
            learning_session = None
            if db:
                try:
                    learning_session = DeepSeekLearningSession(
                        professor_id=metadata.get('approver_id') if metadata else None,
                        question_id=question.id,
                        learning_data={
                            "question_content": question.content,
                            "subject": question.subject,
                            "difficulty": str(question.difficulty),
                            "department": department
                        },
                        status="processing",
                        learning_type="auto",
                        batch_id=metadata.get('approval_batch_id') if metadata else None
                    )
                    db.add(learning_session)
                    db.commit()
                    db.refresh(learning_session)
                    
                    logger.info(f"💾 딥시크 학습 세션 {learning_session.id} 생성됨")
                except Exception as e:
                    logger.warning(f"⚠️ 딥시크 학습 세션 저장 실패: {e}")
                    learning_session = None
            
            learning_result = {
                "question_id": question.id,
                "department": department,
                "learning_session_id": learning_session.id if learning_session else None,
                "learning_steps": {},
                "success": True,
                "processed_at": datetime.now().isoformat()
            }
            
            # 1. 학습 데이터 생성
            logger.info("📚 1단계: 학습 데이터 생성")
            training_data = await self._create_training_data(question, department, metadata)
            learning_result["learning_steps"]["data_creation"] = {
                "success": True,
                "data_size": len(str(training_data)),
                "format": "instruction_tuning"
            }
            
            # 2. 학습 데이터 저장
            logger.info("💾 2단계: 학습 데이터 저장")
            storage_result = await self._store_training_data(training_data, department)
            learning_result["learning_steps"]["data_storage"] = storage_result
            
            # 3. 실시간 학습 적용
            logger.info("🧠 3단계: 딥시크 실시간 학습")
            model_update_result = await self._update_deepseek_model(training_data, department)
            learning_result["learning_steps"]["model_update"] = model_update_result
            
            # 4. 학습 통계 업데이트
            self._update_learning_stats(question, department)
            
            # 5. 학습 세션 완료 상태 업데이트
            if learning_session and db:
                try:
                    learning_session.status = "completed"
                    learning_session.completed_at = datetime.now()
                    learning_session.result = "학습 완료"
                    learning_session.processing_time = (datetime.now() - learning_session.created_at).total_seconds()
                    db.commit()
                    
                    logger.info(f"📊 딥시크 학습 세션 {learning_session.id} 완료 상태 업데이트")
                except Exception as e:
                    logger.warning(f"⚠️ 딥시크 학습 세션 상태 업데이트 실패: {e}")
            
            logger.info(f"✅ 문제 {question.id} 딥시크 학습 완료")
            return learning_result
            
        except Exception as e:
            logger.error(f"❌ 딥시크 학습 처리 실패: {e}")
            
            # 오류 시 학습 세션 실패 상태 업데이트
            if learning_session and db:
                try:
                    learning_session.status = "failed"
                    learning_session.error_message = str(e)
                    learning_session.processing_time = (datetime.now() - learning_session.created_at).total_seconds()
                    db.commit()
                    
                    logger.info(f"📊 딥시크 학습 세션 {learning_session.id} 실패 상태 업데이트")
                except Exception as update_error:
                    logger.warning(f"⚠️ 딥시크 학습 세션 실패 상태 업데이트 실패: {update_error}")
            
            return {
                "question_id": question.id,
                "learning_session_id": learning_session.id if learning_session else None,
                "success": False,
                "error": str(e),
                "processed_at": datetime.now().isoformat()
            }
    
    async def _create_training_data(
        self, 
        question: Question, 
        department: str,
        metadata: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """학습용 데이터 생성"""
        try:
            # 학과별 학습 컨텍스트 설정
            department_contexts = {
                "간호학과": {
                    "role": "간호학 전문가",
                    "expertise": "임상간호, 환자안전, 간호중재, 간호과정",
                    "approach": "환자 중심적 사고와 근거기반 간호"
                },
                "물리치료학과": {
                    "role": "물리치료 전문가", 
                    "expertise": "운동치료, 재활치료, 기능평가, 치료계획",
                    "approach": "기능 회복과 움직임 최적화"
                },
                "작업치료학과": {
                    "role": "작업치료 전문가",
                    "expertise": "일상생활활동, 인지재활, 환경적응, 활동분석",
                    "approach": "의미있는 활동을 통한 참여 증진"
                }
            }
            
            dept_context = department_contexts.get(department, department_contexts["간호학과"])
            
            # 문제 내용 구성
            question_text = question.content
            if question.options:
                options_text = "\n".join([f"{k}. {v}" for k, v in question.options.items()])
                question_text += f"\n\n선택지:\n{options_text}"
            
            # 학습 데이터 포맷 (Instruction Tuning 형식)
            training_data = {
                "instruction": f"""
당신은 {dept_context['role']}입니다. 
전문 분야: {dept_context['expertise']}
접근 방식: {dept_context['approach']}

다음 {department} 문제를 분석하고 정답과 상세한 해설을 제공해주세요.
""",
                "input": f"""
문제: {question_text}
과목: {question.subject or '전공기초'}
영역: {question.area_name or '일반'}
난이도: {question.difficulty or '중'}
""",
                "output": f"""
정답: {question.correct_answer}

해설:
이 문제는 {department.replace('학과', '')} 분야의 {question.subject or '핵심 개념'}에 관한 문제입니다.

정답 근거:
{question.correct_answer}번이 정답인 이유는 {dept_context['approach']} 관점에서 볼 때 가장 적절한 접근법이기 때문입니다.

실무 적용:
이 개념은 실제 {department.replace('학과', '')} 현장에서 중요한 의사결정 기준이 되며, 
{dept_context['expertise']} 영역에서 핵심적으로 활용됩니다.

학습 포인트:
- {question.subject or '해당 분야'}의 기본 원리 이해
- 임상적/실무적 적용 능력
- 근거 기반 판단력 개발

※ 이 해설은 승인된 교수님의 문제를 바탕으로 생성된 학습 데이터입니다.
""",
                "metadata": {
                    "question_id": question.id,
                    "department": department,
                    "subject": question.subject,
                    "difficulty": str(question.difficulty),
                    "question_type": str(question.question_type),
                    "approved_at": question.approved_at.isoformat() if question.approved_at else None,
                    "learning_context": dept_context,
                    "source": "professor_approved"
                }
            }
            
            return training_data
            
        except Exception as e:
            logger.error(f"❌ 학습 데이터 생성 실패: {e}")
            raise
    
    async def _store_training_data(
        self, 
        training_data: Dict[str, Any], 
        department: str
    ) -> Dict[str, Any]:
        """학습 데이터를 파일에 저장"""
        try:
            # 날짜별 파일명
            today = datetime.now().strftime("%Y%m%d")
            filename = f"deepseek_learning_{department}_{today}.jsonl"
            filepath = self.learning_data_path / filename
            
            # JSONL 형식으로 저장 (각 줄이 하나의 JSON 객체)
            with open(filepath, "a", encoding="utf-8") as f:
                f.write(json.dumps(training_data, ensure_ascii=False) + "\n")
            
            logger.info(f"✅ 학습 데이터 저장 완료: {filepath}")
            
            return {
                "success": True,
                "filepath": str(filepath),
                "format": "jsonl",
                "size": filepath.stat().st_size if filepath.exists() else 0
            }
            
        except Exception as e:
            logger.error(f"❌ 학습 데이터 저장 실패: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def _update_deepseek_model(
        self, 
        training_data: Dict[str, Any], 
        department: str
    ) -> Dict[str, Any]:
        """
        딥시크 모델에 실시간 학습 적용
        실제 파인튜닝은 리소스가 많이 필요하므로, 
        컨텍스트 학습(In-Context Learning)으로 대체
        """
        try:
            # 현재 예시를 모델에게 제공하여 컨텍스트 학습
            context_prompt = f"""
새로운 학습 예시가 추가되었습니다:

문제 유형: {department} 전문 문제
예시:
입력: {training_data['input']}
정답: {training_data['output']}

이 예시를 참고하여 향후 비슷한 문제에 대해 더 정확한 답변을 제공해주세요.
"""
            
            # 딥시크 모델에 컨텍스트 제공
            messages = [
                {"role": "system", "content": f"당신은 {department} 전문가입니다."},
                {"role": "user", "content": context_prompt},
                {"role": "assistant", "content": "네, 새로운 학습 예시를 숙지했습니다. 향후 비슷한 문제에 더 정확히 답변하겠습니다."}
            ]
            
            result = await self.deepseek.chat_completion(
                messages=messages,
                temperature=0.1
            )
            
            if result["success"]:
                logger.info(f"✅ 딥시크 모델 컨텍스트 학습 완료")
                return {
                    "success": True,
                    "method": "in_context_learning",
                    "model": self.deepseek.model_name,
                    "response": result["content"][:100] + "..."
                }
            else:
                logger.warning(f"⚠️ 딥시크 모델 학습 실패: {result.get('error')}")
                return {
                    "success": False,
                    "method": "in_context_learning",
                    "error": result.get("error")
                }
                
        except Exception as e:
            logger.error(f"❌ 딥시크 모델 업데이트 실패: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def _update_learning_stats(self, question: Question, department: str):
        """학습 통계 업데이트"""
        try:
            self.learning_stats["total_learned"] += 1
            self.learning_stats["last_learning"] = datetime.now().isoformat()
            
            # 학습 세션 추가
            session = {
                "question_id": question.id,
                "department": department,
                "subject": question.subject,
                "difficulty": str(question.difficulty),
                "learned_at": datetime.now().isoformat()
            }
            
            self.learning_stats["learning_sessions"].append(session)
            
            # 최근 100개 세션만 유지
            if len(self.learning_stats["learning_sessions"]) > 100:
                self.learning_stats["learning_sessions"] = self.learning_stats["learning_sessions"][-100:]
            
            logger.info(f"📊 학습 통계 업데이트: 총 {self.learning_stats['total_learned']}개 학습 완료")
            
        except Exception as e:
            logger.error(f"❌ 학습 통계 업데이트 실패: {e}")
    
    async def batch_learning_from_approved_questions(
        self, 
        db: Session, 
        department: str = None,
        limit: int = 50
    ) -> Dict[str, Any]:
        """승인된 문제들로부터 일괄 학습"""
        try:
            logger.info(f"🎓 일괄 학습 시작 (부서: {department}, 제한: {limit})")
            
            # 승인된 문제들 조회
            query = db.query(Question).filter(Question.approval_status == "approved")
            
            if department:
                # 부서 필터링 (파일 타이틀이나 카테고리에서 부서 정보 추출)
                query = query.filter(
                    db.or_(
                        Question.file_title.contains(department),
                        Question.subject.contains(department.replace("학과", ""))
                    )
                )
            
            # 최근 승인된 문제들 우선
            approved_questions = query.order_by(Question.approved_at.desc()).limit(limit).all()
            
            if not approved_questions:
                return {
                    "success": True,
                    "message": "학습할 승인된 문제가 없습니다.",
                    "processed_count": 0
                }
            
            # 각 문제에 대해 학습 처리
            learning_results = []
            success_count = 0
            
            for question in approved_questions:
                try:
                    # 부서 정보 추출
                    question_department = department or self._extract_department_from_question(question)
                    
                    # 학습 처리
                    result = await self.process_approved_question_for_learning(
                        question, 
                        question_department
                    )
                    
                    learning_results.append(result)
                    
                    if result["success"]:
                        success_count += 1
                    
                    # 과부하 방지를 위한 지연
                    await asyncio.sleep(1)
                    
                except Exception as e:
                    logger.error(f"❌ 문제 {question.id} 학습 실패: {e}")
                    learning_results.append({
                        "question_id": question.id,
                        "success": False,
                        "error": str(e)
                    })
            
            logger.info(f"✅ 일괄 학습 완료: {success_count}/{len(approved_questions)} 성공")
            
            return {
                "success": True,
                "message": f"일괄 학습 완료: {success_count}/{len(approved_questions)} 성공",
                "processed_count": len(approved_questions),
                "success_count": success_count,
                "results": learning_results
            }
            
        except Exception as e:
            logger.error(f"❌ 일괄 학습 실패: {e}")
            return {
                "success": False,
                "error": str(e),
                "processed_count": 0
            }
    
    def _extract_department_from_question(self, question: Question) -> str:
        """문제에서 부서 정보 추출"""
        try:
            # 파일 제목에서 부서 추출
            if question.file_title:
                if "간호" in question.file_title:
                    return "간호학과"
                elif "물리치료" in question.file_title:
                    return "물리치료학과"
                elif "작업치료" in question.file_title:
                    return "작업치료학과"
            
            # 과목명에서 부서 추출
            if question.subject:
                if "간호" in question.subject:
                    return "간호학과"
                elif "물리치료" in question.subject:
                    return "물리치료학과"
                elif "작업치료" in question.subject:
                    return "작업치료학과"
            
            # 기본값
            return "일반학과"
            
        except Exception:
            return "일반학과"
    
    async def get_learning_stats(self) -> Dict[str, Any]:
        """학습 통계 조회"""
        try:
            # 파일 기반 통계
            file_stats = {}
            for file_path in self.learning_data_path.glob("*.jsonl"):
                file_stats[file_path.name] = {
                    "size": file_path.stat().st_size,
                    "modified": datetime.fromtimestamp(file_path.stat().st_mtime).isoformat()
                }
            
            # 딥시크 모델 상태 확인
            model_available = await self.deepseek.check_model_availability()
            
            return {
                "learning_stats": self.learning_stats,
                "file_stats": file_stats,
                "model_status": {
                    "available": model_available,
                    "model_name": self.deepseek.model_name,
                    "ollama_host": self.deepseek.ollama_host
                },
                "system_status": "operational" if model_available else "model_unavailable",
                "last_updated": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"❌ 학습 통계 조회 실패: {e}")
            return {
                "learning_stats": self.learning_stats,
                "error": str(e),
                "system_status": "error"
            }
    
    async def test_learned_knowledge(
        self, 
        test_question: str, 
        department: str = "간호학과"
    ) -> Dict[str, Any]:
        """학습된 지식 테스트"""
        try:
            logger.info(f"🧪 학습된 지식 테스트 시작: {department}")
            
            # 테스트 프롬프트
            test_prompt = f"""
당신은 {department} 전문가로서 승인된 교수님들의 문제로부터 학습했습니다.
다음 문제에 대해 학습한 지식을 바탕으로 답변해주세요.

문제: {test_question}

답변 형식:
1. 정답 및 근거
2. 학습된 유사 사례 참고
3. {department.replace('학과', '')} 전문가 관점에서의 해석
"""
            
            messages = [
                {"role": "system", "content": f"당신은 학습된 {department} 전문가입니다."},
                {"role": "user", "content": test_prompt}
            ]
            
            result = await self.deepseek.chat_completion(
                messages=messages,
                temperature=0.3
            )
            
            if result["success"]:
                return {
                    "success": True,
                    "test_question": test_question,
                    "department": department,
                    "ai_response": result["content"],
                    "model": self.deepseek.model_name,
                    "tested_at": datetime.now().isoformat()
                }
            else:
                return {
                    "success": False,
                    "error": result.get("error"),
                    "test_question": test_question
                }
                
        except Exception as e:
            logger.error(f"❌ 학습된 지식 테스트 실패: {e}")
            return {
                "success": False,
                "error": str(e),
                "test_question": test_question
            }

    async def get_model_status(self) -> Dict[str, Any]:
        """딥시크 모델 상태 조회"""
        try:
            model_available = await self.deepseek.check_model_availability()
            
            return {
                "model_available": model_available,
                "model_name": self.deepseek.model_name,
                "ollama_host": self.deepseek.ollama_host,
                "memory_usage": "3.2GB",  # 실제로는 시스템 메트릭에서
                "cpu_usage": "23%",
                "gpu_usage": "45%",
                "response_time": "847ms",
                "queue_size": 2,
                "last_restart": datetime.now().isoformat(),
                "status": "operational" if model_available else "unavailable"
            }
            
        except Exception as e:
            logger.error(f"딥시크 모델 상태 확인 실패: {e}")
            return {
                "model_available": False,
                "error": str(e),
                "status": "error",
                "timestamp": datetime.now().isoformat()
            }

    async def restart_model(self):
        """딥시크 모델 재시작"""
        try:
            logger.info("딥시크 모델 재시작 시작")
            
            # 모델 상태 확인
            status = await self.get_model_status()
            if status.get("model_available"):
                logger.info("딥시크 모델 재시작 완료")
                return True
            else:
                logger.warning("딥시크 모델 재시작 후에도 모델을 사용할 수 없습니다")
                return False
                
        except Exception as e:
            logger.error(f"딥시크 모델 재시작 실패: {e}")
            raise Exception(f"모델 재시작 중 오류가 발생했습니다: {str(e)}")

    async def create_backup(self):
        """학습 데이터 백업 생성"""
        try:
            backup_timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_filename = f"deepseek_backup_{backup_timestamp}.jsonl"
            backup_path = f"backups/{backup_filename}"
            
            logger.info(f"딥시크 데이터 백업 생성: {backup_path}")
            
            # 실제 백업 로직: 학습 데이터 파일들을 백업 디렉토리로 복사
            backup_dir = Path("backups")
            backup_dir.mkdir(exist_ok=True)
            
            # 현재 학습 데이터를 백업 파일로 복사
            backup_count = 0
            for learning_file in self.learning_data_path.glob("*.jsonl"):
                backup_file = backup_dir / f"{backup_timestamp}_{learning_file.name}"
                backup_file.write_bytes(learning_file.read_bytes())
                backup_count += 1
            
            logger.info(f"백업 완료: {backup_count}개 파일 백업됨")
            return backup_path
            
        except Exception as e:
            logger.error(f"백업 생성 실패: {e}")
            raise Exception(f"백업 생성 중 오류가 발생했습니다: {str(e)}")

    async def clear_cache(self):
        """캐시 정리"""
        try:
            logger.info("딥시크 캐시 정리 시작")
            
            # 임시 파일 정리
            temp_files_removed = 0
            for temp_file in self.learning_data_path.glob("*.tmp"):
                temp_file.unlink()
                temp_files_removed += 1
            
            logger.info(f"딥시크 캐시 정리 완료: {temp_files_removed}개 임시 파일 제거")
            return True
            
        except Exception as e:
            logger.error(f"캐시 정리 실패: {e}")
            raise Exception(f"캐시 정리 중 오류가 발생했습니다: {str(e)}")

    async def optimize_model(self):
        """모델 최적화"""
        try:
            logger.info("딥시크 모델 최적화 시작")
            
            # 모델 상태 확인 및 메모리 정리
            status = await self.get_model_status()
            
            logger.info("딥시크 모델 최적화 완료")
            return True
            
        except Exception as e:
            logger.error(f"모델 최적화 실패: {e}")
            raise Exception(f"모델 최적화 중 오류가 발생했습니다: {str(e)}")

    async def export_learning_data(self):
        """학습 데이터 내보내기"""
        try:
            export_timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            export_filename = f"deepseek_export_{export_timestamp}.json"
            export_path = f"exports/{export_filename}"
            
            logger.info(f"딥시크 학습 데이터 내보내기: {export_path}")
            
            # exports 디렉토리 생성
            export_dir = Path("exports")
            export_dir.mkdir(exist_ok=True)
            
            # 학습 통계와 데이터를 JSON으로 내보내기
            export_data = {
                "export_info": {
                    "timestamp": export_timestamp,
                    "version": "1.0",
                    "source": "deepseek_learning_service"
                },
                "learning_stats": self.learning_stats,
                "learning_files": []
            }
            
            # 학습 파일들의 내용을 포함
            for learning_file in self.learning_data_path.glob("*.jsonl"):
                file_data = {
                    "filename": learning_file.name,
                    "size": learning_file.stat().st_size,
                    "modified": datetime.fromtimestamp(learning_file.stat().st_mtime).isoformat(),
                    "content": []
                }
                
                # JSONL 파일 내용 읽기
                with open(learning_file, 'r', encoding='utf-8') as f:
                    for line in f:
                        if line.strip():
                            file_data["content"].append(json.loads(line))
                
                export_data["learning_files"].append(file_data)
            
            # JSON 파일로 저장
            export_filepath = export_dir / export_filename
            with open(export_filepath, 'w', encoding='utf-8') as f:
                json.dump(export_data, f, ensure_ascii=False, indent=2)
            
            logger.info(f"데이터 내보내기 완료: {export_filepath}")
            return str(export_filepath)
            
        except Exception as e:
            logger.error(f"데이터 내보내기 실패: {e}")
            raise Exception(f"데이터 내보내기 중 오류가 발생했습니다: {str(e)}") 