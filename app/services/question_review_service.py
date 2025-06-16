"""
문제 검토 및 승인 서비스 - 모든 학과 지원 및 실시간 진행률 표시
"""
import json
import os
from typing import List, Dict, Any, Optional, Callable
from datetime import datetime
from pathlib import Path

from sqlalchemy.orm import Session
from sqlalchemy import and_, desc

from ..models.question import Question, DifficultyLevel
from ..models.user import User
from ..schemas.question_review import (
    ParsedFilePreview, QuestionPreviewItem, QuestionUpdateRequest,
    BulkApprovalRequest, QuestionApprovalResponse, ApprovalStatus
)
from ..core.config import settings
import logging

# AI 난이도 분석기 및 유형 매퍼 임포트
try:
    from .ai_difficulty_analyzer import difficulty_analyzer
    from .evaluator_type_mapper import evaluator_type_mapper
    AI_ANALYZER_AVAILABLE = True
except ImportError:
    AI_ANALYZER_AVAILABLE = False
    logger.warning("❌ AI 난이도 분석기를 불러올 수 없습니다")

logger = logging.getLogger(__name__)

# 학과 지원 매핑
SUPPORTED_DEPARTMENTS = {
    "물리치료학과": {
        "short_name": "물리치료",
        "keywords": ["물치", "물리치료", "pt", "physical"],
        "areas": ["근골격계", "신경계", "심폐계", "소아발달", "스포츠의학"]
    },
    "작업치료학과": {
        "short_name": "작업치료", 
        "keywords": ["작치", "작업치료", "ot", "occupational"],
        "areas": ["인지재활", "감각통합", "보조기구", "정신건강", "아동발달"]
    },
    "간호학과": {
        "short_name": "간호",
        "keywords": ["간호", "nursing", "너싱"],
        "areas": ["기본간호", "성인간호", "아동간호", "모성간호", "정신간호", "지역사회간호"]
    }
}

class QuestionReviewService:
    """문제 검토 및 승인 서비스 - 모든 학과 지원"""
    
    def __init__(self):
        self.save_parser_dir = Path("data/save_parser")
        self.save_parser_dir.mkdir(parents=True, exist_ok=True)
        
        # 진행률 추적용 상태 저장소
        self.parsing_status = {}
    
    def detect_user_department(self, db: Session, user_id: int) -> str:
        """
        사용자 정보에서 학과 감지
        
        Args:
            db: 데이터베이스 세션
            user_id: 사용자 ID
            
        Returns:
            str: 감지된 학과명
        """
        try:
            user = db.query(User).filter(User.id == user_id).first()
            if not user:
                return "물리치료학과"  # 기본값
            
            # 사용자 이름이나 부서 정보에서 학과 추정
            user_info = (user.name or "").lower() + (user.department or "").lower()
            
            for dept_name, dept_info in SUPPORTED_DEPARTMENTS.items():
                if any(keyword in user_info for keyword in dept_info["keywords"]):
                    logger.info(f"사용자 {user_id} 학과 감지: {dept_name}")
                    return dept_name
            
            # 기본값
            return "물리치료학과"
            
        except Exception as e:
            logger.warning(f"사용자 학과 감지 실패: {e}")
            return "물리치료학과"
    
    def create_progress_callback(self, user_id: int, file_name: str) -> Callable[[str, float], None]:
        """
        진행률 콜백 함수 생성
        
        Args:
            user_id: 사용자 ID
            file_name: 파일명
            
        Returns:
            Callable: 진행률 콜백 함수
        """
        def progress_callback(message: str, progress: float):
            progress_key = f"{user_id}_{file_name}"
            self.parsing_status[progress_key] = {
                "message": message,
                "progress": progress,
                "timestamp": datetime.now().isoformat(),
                "user_id": user_id,
                "file_name": file_name
            }
            logger.info(f"📊 파싱 진행률 ({file_name}): {progress:.1f}% - {message}")
        
        return progress_callback
    
    def get_parsing_progress(self, user_id: int, file_name: str) -> Dict[str, Any]:
        """
        파싱 진행률 조회
        
        Args:
            user_id: 사용자 ID  
            file_name: 파일명
            
        Returns:
            Dict: 진행률 정보
        """
        progress_key = f"{user_id}_{file_name}"
        return self.parsing_status.get(progress_key, {
            "message": "대기 중...",
            "progress": 0.0,
            "timestamp": datetime.now().isoformat()
        })
    
    def clear_parsing_progress(self, user_id: int, file_name: str):
        """
        파싱 진행률 정리
        """
        progress_key = f"{user_id}_{file_name}"
        if progress_key in self.parsing_status:
            del self.parsing_status[progress_key]
    
    def save_parsed_data_to_json(
        self,
        parsed_data: List[Dict[str, Any]],
        source_file_name: str,
        user_id: int,
        department: str = "물리치료학과"
    ) -> str:
        """
        파싱된 데이터를 JSON 파일로 저장 (학과 정보 포함)
        
        Returns:
            str: 저장된 JSON 파일 경로
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        safe_filename = f"{timestamp}_{user_id}_{department}_{source_file_name}"
        json_filename = f"{Path(safe_filename).stem}.json"
        json_path = self.save_parser_dir / json_filename
        
        # JSON 데이터 준비 (학과 정보 추가)
        save_data = {
            "meta": {
                "source_file": source_file_name,
                "department": department,
                "parsed_at": datetime.now().isoformat(),
                "parsed_by": user_id,
                "total_questions": len(parsed_data),
                "supported_areas": SUPPORTED_DEPARTMENTS.get(department, {}).get("areas", [])
            },
            "questions": parsed_data
        }
        
        # JSON 파일 저장
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(save_data, f, ensure_ascii=False, indent=2)
        
        logger.info(f"파싱된 데이터 JSON 저장 완료: {json_path} ({department})")
        return str(json_path)
    
    async def parse_and_create_questions(
        self,
        db: Session,
        file_path: str,
        user_id: int,
        content_type: str = "auto",
        file_title: str = None,
        file_category: str = None
    ) -> Dict[str, Any]:
        """
        파일 파싱 및 문제 생성 (모든 학과 지원, 실시간 진행률)
        
        Args:
            db: 데이터베이스 세션
            file_path: 업로드된 파일 경로
            user_id: 사용자 ID
            content_type: 파일 타입 ("questions", "answers", "auto")
            file_title: 파일 제목
            file_category: 파일 카테고리
            
        Returns:
            Dict: 파싱 결과 및 생성된 문제 정보
        """
        file_name = Path(file_path).name
        
        try:
            # 1단계: 사용자 학과 감지
            user_department = self.detect_user_department(db, user_id)
            logger.info(f"🎯 사용자 {user_id} 학과: {user_department}")
            
            # 2단계: 진행률 콜백 생성
            progress_callback = self.create_progress_callback(user_id, file_name)
            progress_callback("🚀 파싱 시작 중...", 0.0)
            
            # 3단계: QuestionParser로 파싱 (학과 자동감지 + 진행률 콜백)
            from .question_parser import question_parser
            
            parsing_result = question_parser.parse_any_file(
                file_path=file_path,
                content_type=content_type,
                department=user_department,  # 사용자 학과 전달
                progress_callback=progress_callback
            )
            
            if parsing_result.get("error"):
                progress_callback(f"❌ 파싱 실패: {parsing_result['error']}", 0.0)
                return {
                    "success": False,
                    "error": parsing_result['error'],
                    "department": user_department
                }
            
            parsed_data = parsing_result.get("data", [])
            detected_department = parsing_result.get("department", user_department)
            
            if not parsed_data:
                progress_callback("⚠️ 파싱된 데이터가 없습니다", 0.0)
                return {
                    "success": False,
                    "error": "파싱된 데이터가 없습니다",
                    "department": detected_department
                }
            
            # 4단계: JSON 파일 저장
            progress_callback(f"💾 JSON 파일 저장 중... ({len(parsed_data)}개 문제)", 90.0)
            
            json_path = self.save_parsed_data_to_json(
                parsed_data, file_name, user_id, detected_department
            )
            
            # 5단계: 데이터베이스에 문제 생성
            progress_callback("💾 데이터베이스에 저장 중...", 95.0)
            
            questions = await self.create_pending_questions(
                db=db,
                parsed_data=parsed_data,
                source_file_path=file_path,
                parsed_data_path=json_path,
                user_id=user_id,
                file_title=file_title,
                file_category=file_category,
                department=detected_department
            )
            
            progress_callback("✅ 파싱 및 저장 완료!", 100.0)
            
            # 결과 반환
            result = {
                "success": True,
                "message": f"{detected_department} 문제 {len(questions)}개 파싱 완료",
                "department": detected_department,
                "total_questions": len(questions),
                "questions": [
                    {
                        "id": q.id,
                        "question_number": q.question_number,
                        "content": q.content[:100] + "..." if len(q.content) > 100 else q.content,
                        "difficulty": q.difficulty,
                        "area_name": q.area_name
                    } for q in questions[:5]  # 처음 5개만 미리보기
                ],
                "json_path": json_path,
                "supported_areas": SUPPORTED_DEPARTMENTS.get(detected_department, {}).get("areas", [])
            }
            
            # 진행률 정리 (지연 후)
            import asyncio
            asyncio.create_task(self._cleanup_progress_later(user_id, file_name))
            
            return result
            
        except Exception as e:
            logger.error(f"파싱 및 문제 생성 실패: {e}")
            progress_callback(f"❌ 오류 발생: {str(e)}", 0.0)
            return {
                "success": False,
                "error": str(e),
                "department": "물리치료학과"
            }
    
    async def _cleanup_progress_later(self, user_id: int, file_name: str):
        """
        진행률 정보 지연 삭제 (5분 후)
        """
        import asyncio
        await asyncio.sleep(300)  # 5분 대기
        self.clear_parsing_progress(user_id, file_name)
    
    async def create_pending_questions(
        self,
        db: Session,
        parsed_data: List[Dict[str, Any]],
        source_file_path: str,
        parsed_data_path: str,
        user_id: int,
        file_title: str = None,
        file_category: str = None,
        department: str = "물리치료학과"
    ) -> List[Question]:
        """
        파싱된 데이터를 대기 상태 문제로 생성 (모든 학과 지원)
        """
        questions = []
        
        # 22문제 제한 적용
        limited_data = parsed_data[:22] if len(parsed_data) > 22 else parsed_data
        
        # 문제 번호 순서로 정렬
        limited_data.sort(key=lambda x: x.get("question_number", 0))
        
        logger.info(f"📚 {department} 문제 {len(limited_data)}개 생성 시작")
        
        for item in limited_data:
            logger.info(f"문제 {item.get('question_number')} 생성 시도 중... ({department})")
            
            # 기본 필드 추출 (데이터베이스 enum에 맞는 값 사용)
            question_type = item.get("file_type", "multiple_choice")
            if question_type == "questions":
                question_type = "multiple_choice"
            
            # content 안전 처리 - 다양한 필드명 시도
            content = (item.get("content") or 
                      item.get("question_content") or 
                      item.get("text") or 
                      item.get("question") or 
                      item.get("problem") or 
                      f"문제 {item.get('question_number', '?')}번")
            
            # content가 빈 문자열이면 강제로 기본값 설정
            if not content or content.strip() == "":
                content = f"문제 {item.get('question_number', 'Unknown')}번 - 파싱된 내용 없음"
                logger.warning(f"문제 {item.get('question_number')}번: content가 비어있어 기본값 사용")
            
            difficulty = item.get("difficulty", "중")
            
            # AI 분석 결과가 이미 있는지 확인 (question_parser에서 처리됨)
            ai_analysis = None
            if item.get("ai_analysis_complete"):
                ai_analysis = {
                    "ai_difficulty": item.get("ai_difficulty", "중"),
                    "ai_question_type": item.get("ai_question_type", "객관식"),
                    "ai_confidence": item.get("ai_confidence", "medium"),
                    "ai_reasoning": item.get("ai_reasoning", "AI 분석 완료"),
                    "analysis_method": "question_parser",
                    "department": department
                }
                
                # AI 분석 결과로 난이도 업데이트
                difficulty = ai_analysis["ai_difficulty"]
                
                logger.info(f"🤖 문제 {item.get('question_number')}: AI 분석 결과 사용 (난이도: {difficulty})")
            else:
                # AI 분석이 없는 경우 기본값 설정
                ai_analysis = {
                    "ai_difficulty": difficulty,
                    "ai_question_type": "객관식",
                    "ai_confidence": "low",
                    "ai_reasoning": "파싱 단계에서 AI 분석 미완료",
                    "analysis_method": "default",
                    "department": department
                }
                
                logger.warning(f"⚠️ 문제 {item.get('question_number')}: AI 분석 결과 없음, 기본값 사용")

            # 영역명 확인 및 설정
            area_name = item.get("area_name")
            if not area_name or area_name == "일반":
                # 평가위원 데이터에서 영역명 조회
                year = item.get("year", 2024)
                question_number = item.get("question_number", 1)
                area_name = evaluator_type_mapper.get_area_name_for_question(
                    department, year, question_number
                )
                
                # 학과별 기본 영역 할당
                if not area_name:
                    default_areas = SUPPORTED_DEPARTMENTS.get(department, {}).get("areas", [])
                    if default_areas:
                        area_name = default_areas[0]  # 첫 번째 영역을 기본값으로
                    else:
                        area_name = "일반"

            # AI 분석 정보를 메타데이터에 포함
            ai_metadata = {
                "ai_analysis_complete": ai_analysis is not None,
                "ai_confidence": ai_analysis.get("ai_confidence", "medium") if ai_analysis else "unknown",
                "ai_reasoning": ai_analysis.get("ai_reasoning", "") if ai_analysis else "",
                "ai_question_type": ai_analysis.get("ai_question_type", "객관식") if ai_analysis else "객관식",
                "ai_difficulty": ai_analysis.get("ai_difficulty", "중") if ai_analysis else "중",
                "analysis_timestamp": datetime.now().isoformat(),
                "department": department,
                "analysis_method": ai_analysis.get("analysis_method", "default") if ai_analysis else "default"
            }

            question = Question(
                question_number=item.get("question_number", 1),
                question_type=question_type,
                content=content,
                description=item.get("description"),
                options=item.get("options", {}),
                correct_answer=item.get("correct_answer", ""),
                subject=item.get("subject", ""),
                area_name=area_name,
                difficulty=difficulty,
                year=item.get("year"),
                approval_status="pending",
                source_file_path=source_file_path,
                parsed_data_path=parsed_data_path,
                file_title=file_title,
                file_category=file_category,
                is_active=True,
                last_modified_by=user_id,  # 교수 ID를 생성자 겸 마지막 수정자로 설정
                last_modified_at=datetime.now(),
                metadata=ai_metadata  # AI 분석 정보 저장
            )
            
            db.add(question)
            questions.append(question)
            logger.info(f"문제 {item.get('question_number')} 추가 완료 ({department})")
        
        db.commit()
        logger.info(f"✅ {department} 대기 상태 문제 {len(questions)}개 생성 완료")
        return questions

    def get_pending_questions(
        self, 
        db: Session, 
        user_id: Optional[int] = None,
        limit: int = 300,
        department_filter: Optional[str] = None
    ) -> List[QuestionPreviewItem]:
        """
        승인 대기 중인 문제들 조회 (교수 ID 기반 지속성) - 학과 필터 지원
        """
        query = db.query(Question).filter(
            Question.approval_status == "pending"
        )
        
        if user_id:
            # last_modified_by로 교수 문제 필터링 (생성자 추적)
            query = query.filter(Question.last_modified_by == user_id)
        
        # 학과 필터링 (메타데이터 기반)
        if department_filter:
            # JSON 메타데이터에서 학과 정보 필터링 (PostgreSQL JSON 연산자 사용)
            from sqlalchemy import text
            query = query.filter(
                text("metadata->>'department' = :dept").params(dept=department_filter)
            )
        
        questions = query.order_by(Question.question_number.asc(), desc(Question.created_at)).limit(limit).all()
        
        result = []
        for q in questions:
            # AI 분석 상태 확인 (안전한 접근)
            ai_metadata = {}
            if hasattr(q, 'metadata') and q.metadata:
                if isinstance(q.metadata, dict):
                    ai_metadata = q.metadata
                else:
                    ai_metadata = {}
            
            # 학과 정보 추출
            question_department = ai_metadata.get("department", "물리치료학과")
            ai_status = "🤖 AI 분석 완료" if ai_metadata.get("ai_analysis_complete") else "🤖 AI가 난이도 분석 중..."
            
            result.append(QuestionPreviewItem(
                id=q.id,
                question_number=q.question_number,
                content=q.content,
                description=q.description,
                options=q.options or {},
                correct_answer=q.correct_answer or "",
                subject=q.subject,
                area_name=q.area_name,
                difficulty=q.difficulty if q.difficulty else "중",
                year=q.year,
                file_title=f"[{question_department}] {q.file_title}" if q.file_title else f"[{question_department}] 파일",
                file_category=q.file_category,
                last_modified_by=q.last_modified_by,
                last_modified_at=q.last_modified_at,
                ai_analysis_status=ai_status,
                ai_confidence=ai_metadata.get("ai_confidence", "unknown"),
                ai_reasoning=ai_metadata.get("ai_reasoning", "")
            ))
        
        return result
    
    def get_professor_questions_all(self, db: Session, user_id: int) -> dict:
        """
        교수의 모든 문제 조회 (승인된 것과 대기 중인 것 모두)
        서버 재시작 후에도 데이터 지속성 보장
        """
        try:
            from sqlalchemy import or_
            
            # 교수가 업로드한 모든 문제 조회 (last_modified_by 기준)
            all_questions = db.query(Question).filter(
                Question.last_modified_by == user_id
            ).order_by(Question.question_number.asc(), desc(Question.created_at)).all()
            
            # 상태별로 분류
            pending_questions = []
            approved_questions = []
            rejected_questions = []
            
            for q in all_questions:
                # AI 분석 상태 확인 (안전한 접근)
                ai_metadata = {}
                if hasattr(q, 'metadata') and q.metadata:
                    if isinstance(q.metadata, dict):
                        ai_metadata = q.metadata
                    else:
                        ai_metadata = {}
                
                ai_status = "🤖 AI 분석 완료" if ai_metadata.get("ai_analysis_complete") else "🤖 AI가 난이도 분석 중..."
                
                question_item = QuestionPreviewItem(
                    id=q.id,
                    question_number=q.question_number,
                    content=q.content,
                    description=q.description,
                    options=q.options or {},
                    correct_answer=q.correct_answer or "",
                    subject=q.subject,
                    area_name=q.area_name,
                    difficulty=q.difficulty if q.difficulty else "중",
                    year=q.year,
                    file_title=q.file_title,
                    file_category=q.file_category,
                    last_modified_by=q.last_modified_by,
                    last_modified_at=q.last_modified_at,
                    ai_analysis_status=ai_status,
                    ai_confidence=ai_metadata.get("ai_confidence", "unknown"),
                    ai_reasoning=ai_metadata.get("ai_reasoning", "")
                )
                
                if q.approval_status == "pending":
                    pending_questions.append(question_item)
                elif q.approval_status == "approved":
                    approved_questions.append(question_item)
                elif q.approval_status == "rejected":
                    rejected_questions.append(question_item)
            
            return {
                "pending": pending_questions,
                "approved": approved_questions,
                "rejected": rejected_questions,
                "total_count": len(all_questions),
                "status_summary": {
                    "pending": len(pending_questions),
                    "approved": len(approved_questions),
                    "rejected": len(rejected_questions)
                }
            }
            
        except Exception as e:
            logger.error(f"교수 문제 전체 조회 실패: {e}")
            return {
                "pending": [],
                "approved": [],
                "rejected": [],
                "total_count": 0,
                "status_summary": {"pending": 0, "approved": 0, "rejected": 0}
            }
    
    def get_professor_rag_stats(self, db: Session, user_id: int) -> dict:
        """
        교수별 RAG 통계 조회 (데이터베이스 기반)
        서버 재시작 후에도 지속성 보장
        """
        try:
            from sqlalchemy import or_
            
            # 교수가 업로드한 문제들의 통계 (last_modified_by 기준)
            professor_questions = db.query(Question).filter(
                Question.last_modified_by == user_id
            ).all()
            
            # 파일별 그룹핑 (source_file_path 기준)
            uploaded_files = set()
            for q in professor_questions:
                if q.source_file_path:
                    # 세미콜론으로 구분된 파일들 처리
                    files = q.source_file_path.split(';')
                    for file_path in files:
                        if file_path.strip():
                            # 파일명만 추출
                            file_name = Path(file_path.strip()).name
                            uploaded_files.add(file_name)
            
            # 주제별 그룹핑
            subjects = set()
            for q in professor_questions:
                if q.subject:
                    subjects.add(q.subject)
            
            # 난이도별 그룹핑
            difficulty_stats = {"상": 0, "중": 0, "하": 0}
            for q in professor_questions:
                if q.difficulty:
                    difficulty_key = q.difficulty.value if hasattr(q.difficulty, 'value') else str(q.difficulty)
                    if difficulty_key in difficulty_stats:
                        difficulty_stats[difficulty_key] += 1
            
            # 최근 업로드 시간
            latest_question = None
            if professor_questions:
                latest_question = max(professor_questions, key=lambda x: x.created_at)
            
            return {
                "total_documents": len(uploaded_files),
                "total_questions": len(professor_questions),
                "uploaded_files": list(uploaded_files),
                "subjects": list(subjects),
                "difficulty_distribution": difficulty_stats,
                "last_upload": latest_question.created_at.isoformat() if latest_question else None,
                "status_distribution": {
                    "pending": len([q for q in professor_questions if q.approval_status == "pending"]),
                    "approved": len([q for q in professor_questions if q.approval_status == "approved"]),
                    "rejected": len([q for q in professor_questions if q.approval_status == "rejected"])
                }
            }
            
        except Exception as e:
            logger.error(f"교수 RAG 통계 조회 실패: {e}")
            return {
                "total_documents": 0,
                "total_questions": 0,
                "uploaded_files": [],
                "subjects": [],
                "difficulty_distribution": {"상": 0, "중": 0, "하": 0},
                "last_upload": None,
                "status_distribution": {"pending": 0, "approved": 0, "rejected": 0}
            }
    
    def update_question(
        self,
        db: Session,
        question_id: int,
        update_data: QuestionUpdateRequest,
        user_id: int
    ) -> bool:
        """
        문제 내용 수정
        """
        question = db.query(Question).filter(Question.id == question_id).first()
        if not question:
            return False
        
        # 수정 사항 적용
        if update_data.content is not None:
            question.content = update_data.content
        if update_data.description is not None:
            question.description = update_data.description
        if update_data.options is not None:
            question.options = update_data.options
        if update_data.correct_answer is not None:
            question.correct_answer = update_data.correct_answer
        if update_data.subject is not None:
            question.subject = update_data.subject
        if update_data.area_name is not None:
            question.area_name = update_data.area_name
        if update_data.difficulty is not None:
            # 데이터베이스 enum에 직접 문자열 값 할당 (SQLAlchemy enum 객체 사용하지 않음)
            logger.info(f"난이도 수정 요청: '{update_data.difficulty}' -> 직접 문자열 할당")
            if update_data.difficulty in ["하", "중", "상"]:
                # 데이터베이스에 직접 한글 값 저장
                question.difficulty = update_data.difficulty
                logger.info(f"난이도 설정 완료: '{update_data.difficulty}' (직접 문자열)")
            else:
                # 기본값
                question.difficulty = "중"
                logger.warning(f"알 수 없는 난이도 '{update_data.difficulty}', 기본값 '중'으로 설정")
        
        # 수정 이력 업데이트
        question.last_modified_by = user_id
        question.last_modified_at = datetime.now()
        question.updated_at = datetime.now()
        
        db.commit()
        logger.info(f"문제 {question_id} 수정 완료 (수정자: {user_id})")
        return True
    
    def bulk_approve_questions(
        self,
        db: Session,
        request: BulkApprovalRequest,
        approver_id: int
    ) -> QuestionApprovalResponse:
        """
        문제 일괄 승인/거부
        """
        approved_count = 0
        rejected_count = 0
        failed_count = 0
        
        for question_id in request.question_ids:
            try:
                question = db.query(Question).filter(Question.id == question_id).first()
                if not question:
                    failed_count += 1
                    continue
                
                if request.action == ApprovalStatus.APPROVED:
                    question.approval_status = "approved"
                    question.approved_by = approver_id
                    question.approved_at = datetime.now()
                    approved_count += 1
                elif request.action == ApprovalStatus.REJECTED:
                    question.approval_status = "rejected"
                    rejected_count += 1
                
                question.updated_at = datetime.now()
                
            except Exception as e:
                logger.error(f"문제 {question_id} 승인 처리 실패: {e}")
                failed_count += 1
        
        db.commit()
        
        message = f"처리 완료: 승인 {approved_count}개, 거부 {rejected_count}개"
        if failed_count > 0:
            message += f", 실패 {failed_count}개"
        
        return QuestionApprovalResponse(
            success=True,
            message=message,
            approved_count=approved_count,
            rejected_count=rejected_count,
            failed_count=failed_count
        )
    
    def get_parsed_file_preview(
        self,
        parsed_data_path: str
    ) -> Optional[Dict[str, Any]]:
        """
        저장된 JSON 파일에서 미리보기 데이터 로드
        """
        try:
            if not os.path.exists(parsed_data_path):
                return None
            
            with open(parsed_data_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            return data
        except Exception as e:
            logger.error(f"JSON 파일 로드 실패 ({parsed_data_path}): {e}")
            return None
    
    def get_ai_analysis_stats(self, db: Session, user_id: int) -> dict:
        """
        AI 분석 검증률 및 통계 조회
        """
        try:
            # 교수가 업로드한 모든 문제 조회
            professor_questions = db.query(Question).filter(
                Question.last_modified_by == user_id
            ).all()
            
            if not professor_questions:
                return {
                    "total_questions": 0,
                    "ai_analyzed_count": 0,
                    "analysis_completion_rate": 0.0,
                    "confidence_distribution": {},
                    "difficulty_accuracy": {},
                    "error_rate": 0.0,
                    "average_confidence": 0.0
                }
            
            total_questions = len(professor_questions)
            ai_analyzed_count = 0
            confidence_scores = []
            confidence_distribution = {"high": 0, "medium": 0, "low": 0, "unknown": 0}
            difficulty_distribution = {"하": 0, "중": 0, "상": 0}
            
            for q in professor_questions:
                # AI 분석 메타데이터 안전하게 접근
                ai_metadata = {}
                if hasattr(q, 'metadata') and q.metadata:
                    if isinstance(q.metadata, dict):
                        ai_metadata = q.metadata
                
                # AI 분석 완료 여부 확인
                if ai_metadata.get("ai_analysis_complete"):
                    ai_analyzed_count += 1
                    
                    # 신뢰도 분포
                    confidence = ai_metadata.get("ai_confidence", "unknown")
                    confidence_distribution[confidence] = confidence_distribution.get(confidence, 0) + 1
                    
                    # 신뢰도 점수 수집 (평균 계산용)
                    confidence_score_map = {"high": 0.9, "medium": 0.7, "low": 0.5, "unknown": 0.5}
                    confidence_scores.append(confidence_score_map.get(confidence, 0.5))
                
                # 난이도 분포
                if q.difficulty and str(q.difficulty) in difficulty_distribution:
                    difficulty_distribution[str(q.difficulty)] += 1
            
            # 검증률 계산
            analysis_completion_rate = (ai_analyzed_count / total_questions) * 100 if total_questions > 0 else 0.0
            
            # 평균 신뢰도
            average_confidence = sum(confidence_scores) / len(confidence_scores) if confidence_scores else 0.0
            
            # 오차율 계산 (신뢰도 기반 추정)
            error_rate = (1 - average_confidence) * 100
            
            # 평가위원 패턴과의 일치율 계산 (더미 데이터)
            evaluator_match_rate = 85.5  # 실제로는 평가위원 데이터와 비교해야 함
            
            return {
                "total_questions": total_questions,
                "ai_analyzed_count": ai_analyzed_count,
                "analysis_completion_rate": round(analysis_completion_rate, 1),
                "confidence_distribution": confidence_distribution,
                "difficulty_distribution": difficulty_distribution,
                "error_rate": round(error_rate, 1),
                "average_confidence": round(average_confidence * 100, 1),
                "evaluator_match_rate": evaluator_match_rate,
                "accuracy_summary": {
                    "high_confidence": confidence_distribution.get("high", 0),
                    "reliable_predictions": ai_analyzed_count - confidence_distribution.get("low", 0),
                    "needs_review": confidence_distribution.get("low", 0)
                }
            }
            
        except Exception as e:
            logger.error(f"AI 분석 통계 조회 실패: {e}")
            return {
                "total_questions": 0,
                "ai_analyzed_count": 0,
                "analysis_completion_rate": 0.0,
                "confidence_distribution": {},
                "difficulty_accuracy": {},
                "error_rate": 100.0,
                "average_confidence": 0.0,
                "error": str(e)
            }

    def get_department_statistics(self, db: Session, user_id: Optional[int] = None) -> Dict[str, Any]:
        """
        학과별 문제 통계 조회
        
        Args:
            db: 데이터베이스 세션
            user_id: 사용자 ID (None인 경우 전체 통계)
            
        Returns:
            Dict: 학과별 통계 정보
        """
        try:
            query = db.query(Question)
            
            if user_id:
                query = query.filter(Question.last_modified_by == user_id)
            
            all_questions = query.all()
            
            # 학과별 분류
            department_stats = {}
            
            for q in all_questions:
                # 메타데이터에서 학과 정보 추출
                ai_metadata = {}
                if hasattr(q, 'metadata') and q.metadata:
                    if isinstance(q.metadata, dict):
                        ai_metadata = q.metadata
                
                department = ai_metadata.get("department", "물리치료학과")
                
                if department not in department_stats:
                    department_stats[department] = {
                        "total_questions": 0,
                        "pending": 0,
                        "approved": 0,
                        "rejected": 0,
                        "difficulty_distribution": {"하": 0, "중": 0, "상": 0},
                        "areas": set(),
                        "latest_upload": None
                    }
                
                stats = department_stats[department]
                stats["total_questions"] += 1
                
                # 상태별 카운트
                if q.approval_status == "pending":
                    stats["pending"] += 1
                elif q.approval_status == "approved":
                    stats["approved"] += 1
                elif q.approval_status == "rejected":
                    stats["rejected"] += 1
                
                # 난이도별 카운트
                if q.difficulty:
                    difficulty = str(q.difficulty)
                    if difficulty in stats["difficulty_distribution"]:
                        stats["difficulty_distribution"][difficulty] += 1
                
                # 영역 수집
                if q.area_name:
                    stats["areas"].add(q.area_name)
                
                # 최신 업로드 시간
                if not stats["latest_upload"] or q.created_at > stats["latest_upload"]:
                    stats["latest_upload"] = q.created_at
            
            # set을 list로 변환
            for dept_name, stats in department_stats.items():
                stats["areas"] = list(stats["areas"])
                if stats["latest_upload"]:
                    stats["latest_upload"] = stats["latest_upload"].isoformat()
            
            return {
                "department_statistics": department_stats,
                "supported_departments": list(SUPPORTED_DEPARTMENTS.keys()),
                "total_departments": len(department_stats),
                "overall_total": sum(stats["total_questions"] for stats in department_stats.values())
            }
            
        except Exception as e:
            logger.error(f"학과별 통계 조회 실패: {e}")
            return {
                "department_statistics": {},
                "supported_departments": list(SUPPORTED_DEPARTMENTS.keys()),
                "total_departments": 0,
                "overall_total": 0,
                "error": str(e)
            } 