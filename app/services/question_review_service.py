"""
문제 검토 및 승인 서비스
"""
import json
import os
from typing import List, Dict, Any, Optional
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

logger = logging.getLogger(__name__)

class QuestionReviewService:
    """문제 검토 및 승인 서비스"""
    
    def __init__(self):
        self.save_parser_dir = Path("data/save_parser")
        self.save_parser_dir.mkdir(parents=True, exist_ok=True)
    
    def save_parsed_data_to_json(
        self,
        parsed_data: List[Dict[str, Any]],
        source_file_name: str,
        user_id: int
    ) -> str:
        """
        파싱된 데이터를 JSON 파일로 저장
        
        Returns:
            str: 저장된 JSON 파일 경로
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        safe_filename = f"{timestamp}_{user_id}_{source_file_name}"
        json_filename = f"{Path(safe_filename).stem}.json"
        json_path = self.save_parser_dir / json_filename
        
        # JSON 데이터 준비
        save_data = {
            "meta": {
                "source_file": source_file_name,
                "parsed_at": datetime.now().isoformat(),
                "parsed_by": user_id,
                "total_questions": len(parsed_data)
            },
            "questions": parsed_data
        }
        
        # JSON 파일 저장
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(save_data, f, ensure_ascii=False, indent=2)
        
        logger.info(f"파싱된 데이터 JSON 저장 완료: {json_path}")
        return str(json_path)
    
    def create_pending_questions(
        self,
        db: Session,
        parsed_data: List[Dict[str, Any]],
        source_file_path: str,
        parsed_data_path: str,
        user_id: int,
        file_title: str = None,
        file_category: str = None
    ) -> List[Question]:
        """
        파싱된 데이터로 대기 상태 문제들 생성
        """
        questions = []
        
        for item in parsed_data:
            try:
                # 난이도 변환 (직접 문자열 사용)
                difficulty_str = item.get("difficulty", "중")
                difficulty = "중"  # 기본값
                
                # 유효한 한글 난이도 값 확인
                if difficulty_str in ["하", "중", "상"]:
                    difficulty = difficulty_str
                
                # 문제 유형 결정 (선택지가 있으면 객관식, 없으면 주관식)
                question_type = "multiple_choice"
                options = item.get("options", {})
                if options and len(options) > 1:
                    question_type = "multiple_choice"
                else:
                    question_type = "short_answer"

                # 디버깅 정보 추가
                logger.info(f"문제 {item.get('question_number')} 생성 시도 중...")

                # content가 null이면 기본 문제 내용 생성
                content = item.get("content")
                if not content:
                    # 선택지가 있으면 그것을 기반으로 문제 생성
                    options = item.get("options", {})
                    if options:
                        content = f"문제 {item.get('question_number', '?')}번 - 다음 중 올바른 것은?"
                    else:
                        content = f"문제 {item.get('question_number', '?')}번"

                question = Question(
                    question_number=item.get("question_number", 1),
                    question_type=question_type,
                    content=content,
                    description=item.get("description"),
                    options=item.get("options", {}),
                    correct_answer=item.get("correct_answer", ""),
                    subject=item.get("subject", ""),
                    area_name=item.get("area_name", ""),
                    difficulty=difficulty,
                    year=item.get("year"),
                    approval_status="pending",
                    source_file_path=source_file_path,
                    parsed_data_path=parsed_data_path,
                    file_title=file_title,
                    file_category=file_category,
                    is_active=True,
                    last_modified_by=user_id,  # 교수 ID를 마지막 수정자로 설정
                    last_modified_at=datetime.now()
                )
                
                db.add(question)
                questions.append(question)
                logger.info(f"문제 {item.get('question_number')} 추가 완료")
                
            except Exception as e:
                logger.error(f"문제 생성 실패 (번호: {item.get('question_number')}): {e}")
                logger.error(f"상세 에러: {type(e).__name__}: {str(e)}")
                import traceback
                logger.error(f"스택 트레이스: {traceback.format_exc()}")
                continue
        
        try:
            db.commit()
            logger.info(f"대기 상태 문제 {len(questions)}개 생성 완료")
            return questions
        except Exception as e:
            logger.error(f"데이터베이스 커밋 실패: {e}")
            logger.error(f"커밋 상세 에러: {type(e).__name__}: {str(e)}")
            import traceback
            logger.error(f"커밋 스택 트레이스: {traceback.format_exc()}")
            db.rollback()
            raise e
    
    def get_pending_questions(
        self, 
        db: Session, 
        user_id: Optional[int] = None,
        limit: int = 50
    ) -> List[QuestionPreviewItem]:
        """
        승인 대기 중인 문제들 조회 (교수 ID 기반 지속성)
        """
        query = db.query(Question).filter(
            Question.approval_status == "pending"
        )
        
        if user_id:
            # last_modified_by로 교수 문제 필터링 (생성자 추적)
            query = query.filter(Question.last_modified_by == user_id)
        
        questions = query.order_by(desc(Question.created_at)).limit(limit).all()
        
        result = []
        for q in questions:
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
                file_title=q.file_title,
                file_category=q.file_category,
                last_modified_by=q.last_modified_by,
                last_modified_at=q.last_modified_at
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
            ).order_by(desc(Question.created_at)).all()
            
            # 상태별로 분류
            pending_questions = []
            approved_questions = []
            rejected_questions = []
            
            for q in all_questions:
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
                    last_modified_at=q.last_modified_at
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