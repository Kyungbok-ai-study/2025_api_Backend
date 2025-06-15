"""
문제 서비스 모듈

이 모듈은 파싱된 문제 데이터를 데이터베이스에 저장하고 관리하는 서비스를 제공합니다.
- 문제 생성 및 저장
- 임베딩 생성 및 업데이트
- 메타데이터 관리
"""
from typing import List, Dict, Any, Optional, Union, Tuple
import json
import logging
from datetime import datetime, timezone

from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError

from ..db.database import get_db
from ..core.config import settings
from ..models.question import (
    Question, AnswerOption, CorrectAnswer, Explanation,
    Tag, Subject, Source, QuestionType, DifficultyLevel
)
# deepseek_service import 제로됨 (Exaone으로 전환)

logger = logging.getLogger(__name__)


def create_question_from_parsed_data(
    db: Session,
    question_data: Dict[str, Any],
    subject_id: Optional[int] = None,
    source_id: Optional[int] = None,
    create_embedding_vector: bool = True,
    user_id: Optional[int] = None
) -> Tuple[Question, bool]:
    """
    question_parser.py의 convert_to_db_format 결과를 기반으로 문제 생성
    
    Args:
        db (Session): 데이터베이스 세션
        question_data (Dict[str, Any]): convert_to_db_format에서 변환된 문제 데이터
        subject_id (int, optional): 과목 ID (우선순위 높음)
        source_id (int, optional): 출처 ID (우선순위 높음)
        create_embedding_vector (bool): 임베딩 벡터 생성 여부
        user_id (int, optional): 생성자 ID
        
    Returns:
        Tuple[Question, bool]: 저장된 문제 객체와 성공 여부
    """
    try:
        # 필수 필드 확인
        content = question_data.get("content")
        if not content:
            logger.error("문제 내용이 없습니다.")
            return None, False
        
        # 난이도 결정
        difficulty_str = question_data.get("difficulty", "중")
        try:
            difficulty = DifficultyLevel(difficulty_str)
        except ValueError:
            difficulty = DifficultyLevel.MEDIUM
        
        # 문제 객체 생성 (새로운 스키마 사용)
        question = Question(
            question_number=question_data.get("question_number", 1),
            content=content,
            description=question_data.get("description"),
            options=question_data.get("options", {}),
            correct_answer=question_data.get("correct_answer", ""),
            subject=question_data.get("subject", ""),
            area_name=question_data.get("area_name", ""),
            difficulty=difficulty,
            year=question_data.get("year")
        )
        
        # 임베딩 생성 부분 - Exaone으로 전환 예정 (현재는 임시 비활성화)
        if create_embedding_vector and content:
            try:
                # TODO: Exaone 임베딩 서비스로 대체 예정
                logger.info(f"임베딩 생성 요청 (Exaone 전환 예정): {question.question_number}")
                # 임시로 None 설정 - Exaone 서비스 구현 후 활성화
                question.embedding = None
            except Exception as e:
                logger.warning(f"임베딩 생성 실패: {e}")
        
        # 데이터베이스에 저장
        db.add(question)
        db.flush()
        
        return question, True
    
    except Exception as e:
        logger.error(f"문제 저장 오류: {str(e)}")
        return None, False


def create_answer_options_from_parsed_data(
    db: Session,
    answer_options_data: List[Dict[str, Any]],
    question_id_mapping: Dict[int, int]
) -> int:
    """
    convert_to_db_format에서 변환된 답안 선택지 데이터를 저장
    
    Args:
        db (Session): 데이터베이스 세션
        answer_options_data (List[Dict]): 답안 선택지 데이터
        question_id_mapping (Dict): 원본 question_id -> 실제 DB question_id 매핑
        
    Returns:
        int: 저장된 선택지 수
    """
    saved_count = 0
    
    for option_data in answer_options_data:
        try:
            original_question_id = option_data.get("question_id")
            actual_question_id = question_id_mapping.get(original_question_id)
            
            if not actual_question_id:
                logger.warning(f"문제 ID {original_question_id}에 대한 매핑을 찾을 수 없습니다.")
                continue
            
            option = AnswerOption(
                question_id=actual_question_id,
                option_text=option_data.get("option_text", ""),
                option_label=option_data.get("option_label", ""),
                display_order=option_data.get("display_order", 0)
            )
            
            db.add(option)
            saved_count += 1
            
        except Exception as e:
            logger.error(f"선택지 저장 오류: {e}")
            continue
    
    return saved_count


def create_correct_answers_from_parsed_data(
    db: Session,
    correct_answers_data: List[Dict[str, Any]],
    question_id_mapping: Dict[int, int]
) -> int:
    """
    convert_to_db_format에서 변환된 정답 데이터를 저장
    
    Args:
        db (Session): 데이터베이스 세션
        correct_answers_data (List[Dict]): 정답 데이터
        question_id_mapping (Dict): 원본 question_id -> 실제 DB question_id 매핑
        
    Returns:
        int: 저장된 정답 수
    """
    saved_count = 0
    
    for answer_data in correct_answers_data:
        try:
            original_question_id = answer_data.get("question_id")
            actual_question_id = question_id_mapping.get(original_question_id)
            
            if not actual_question_id:
                logger.warning(f"문제 ID {original_question_id}에 대한 매핑을 찾을 수 없습니다.")
                continue
            
            correct_answer = CorrectAnswer(
                question_id=actual_question_id,
                answer_text=answer_data.get("answer_text", "")
            )
            
            db.add(correct_answer)
            saved_count += 1
            
        except Exception as e:
            logger.error(f"정답 저장 오류: {e}")
            continue
    
    return saved_count


def save_converted_db_format_data(
    db: Session,
    db_format_data: Dict[str, List[Dict[str, Any]]],
    source_name: str,
    create_embeddings: bool = True,
    user_id: Optional[int] = None
) -> Dict[str, Any]:
    """
    question_parser.py의 convert_to_db_format 결과를 데이터베이스에 저장
    
    Args:
        db (Session): 데이터베이스 세션
        db_format_data (Dict): convert_to_db_format 반환 데이터
        source_name (str): 출처 이름
        create_embeddings (bool): 임베딩 생성 여부
        user_id (int, optional): 사용자 ID
        
    Returns:
        Dict[str, Any]: 저장 결과
    """
    try:
        # 출처 찾기 또는 생성
        source = db.query(Source).filter(Source.name == source_name).first()
        if not source:
            # db_format_data에서 연도 추출 시도
            year = None
            if db_format_data.get("questions"):
                first_question = db_format_data["questions"][0]
                metadata = first_question.get("question_metadata", {})
                year = metadata.get("year")
            
            source = Source(
                name=source_name,
                description=f"{source_name} 기출문제",
                type="국가고시",
                year=year
            )
            db.add(source)
            db.flush()
        
        # 1. 문제 저장
        questions_data = db_format_data.get("questions", [])
        question_id_mapping = {}  # 원본 ID -> 실제 DB ID
        saved_questions = 0
        
        for question_data in questions_data:
            original_id = question_data.get("id")
            question, success = create_question_from_parsed_data(
                db=db,
                question_data=question_data,
                source_id=source.id,
                create_embedding_vector=create_embeddings,
                user_id=user_id
            )
            
            if success and question:
                question_id_mapping[original_id] = question.id
                saved_questions += 1
        
        # 2. 답안 선택지 저장
        answer_options_data = db_format_data.get("answer_options", [])
        saved_options = create_answer_options_from_parsed_data(
            db=db,
            answer_options_data=answer_options_data,
            question_id_mapping=question_id_mapping
        )
        
        # 3. 정답 저장
        correct_answers_data = db_format_data.get("correct_answers", [])
        saved_answers = create_correct_answers_from_parsed_data(
            db=db,
            correct_answers_data=correct_answers_data,
            question_id_mapping=question_id_mapping
        )
        
        # 커밋
        db.commit()
        
        return {
            "success": True,
            "total_questions": len(questions_data),
            "saved_questions": saved_questions,
            "saved_options": saved_options,
            "saved_answers": saved_answers,
            "source_name": source_name
        }
        
    except Exception as e:
        db.rollback()
        logger.error(f"DB 형식 데이터 저장 오류: {e}")
        return {
            "success": False,
            "error": str(e)
        }


def process_files_with_gemini_parser(
    db: Session,
    question_file_path: str,
    answer_file_path: Optional[str] = None,
    source_name: Optional[str] = None,
    create_embeddings: bool = True,
    user_id: Optional[int] = None,
    gemini_api_key: Optional[str] = None
) -> Dict[str, Any]:
    """
    개선된 question_parser.py를 사용하여 파일들을 처리하고 저장
    
    Args:
        db (Session): 데이터베이스 세션
        question_file_path (str): 문제 파일 경로
        answer_file_path (str, optional): 정답 파일 경로
        source_name (str, optional): 출처 이름
        create_embeddings (bool): 임베딩 생성 여부
        user_id (int, optional): 사용자 ID
        gemini_api_key (str, optional): Gemini API 키
        
    Returns:
        Dict[str, Any]: 처리 결과
    """
    try:
        from .question_parser import QuestionParser
        
        # 파서 초기화
        parser = QuestionParser(api_key=gemini_api_key or settings.GEMINI_API_KEY)
        
        # 출처 이름 기본값 설정
        if not source_name:
            import os
            file_name = os.path.basename(question_file_path)
            source_name = os.path.splitext(file_name)[0]
        
        # 1. 문제 파일 파싱
        questions_result = parser.parse_any_file(question_file_path, content_type="questions")
        if "error" in questions_result:
            return {
                "success": False,
                "error": f"문제 파일 파싱 오류: {questions_result['error']}"
            }
        
        questions_data = questions_result.get("data", [])
        if not questions_data:
            return {
                "success": False,
                "error": "파싱된 문제가 없습니다."
            }
        
        # 2. 정답 파일 파싱 (있는 경우)
        answers_data = []
        if answer_file_path:
            answers_result = parser.parse_any_file(answer_file_path, content_type="answers")
            if "error" not in answers_result:
                answers_data = answers_result.get("data", [])
        
        # 3. 문제와 정답 매칭 (정답이 있는 경우)
        if answers_data:
            matched_data = parser.match_questions_with_answers(questions_data, answers_data)
        else:
            matched_data = questions_data
        
        # 4. DB 형식으로 변환
        db_format_data = parser.convert_to_db_format(matched_data)
        
        # 5. 데이터베이스에 저장
        save_result = save_converted_db_format_data(
            db=db,
            db_format_data=db_format_data,
            source_name=source_name,
            create_embeddings=create_embeddings,
            user_id=user_id
        )
        
        # 결과 통합
        save_result.update({
            "question_file": question_file_path,
            "answer_file": answer_file_path,
            "matched_count": len(matched_data),
            "questions_parsed": len(questions_data),
            "answers_parsed": len(answers_data)
        })
        
        return save_result
        
    except Exception as e:
        logger.error(f"파일 처리 오류: {e}")
        return {
            "success": False,
            "error": str(e)
        }


# 기존 함수들 유지 (하위 호환성)
def create_question_from_data(
    db: Session,
    question_data: Dict[str, Any],
    subject_id: Optional[int] = None,
    source_id: Optional[int] = None,
    create_embedding_vector: bool = True,
    user_id: Optional[int] = None
) -> Tuple[Question, bool]:
    """
    레거시 함수 - 하위 호환성을 위해 유지
    새로운 코드에서는 create_question_from_parsed_data 사용 권장
    """
    try:
        # 필수 필드 확인
        content = question_data.get("content")
        if not content:
            logger.error("문제 내용이 없습니다.")
            return None, False
        
        # 난이도 결정
        difficulty_str = question_data.get("difficulty", "중")
        try:
            difficulty = DifficultyLevel(difficulty_str)
        except ValueError:
            difficulty = DifficultyLevel.MEDIUM
        
        # 문제 객체 생성 (새로운 스키마 사용)
        question = Question(
            question_number=question_data.get("question_number", 1),
            content=content,
            description=question_data.get("description"),
            options=question_data.get("options", {}),
            correct_answer=question_data.get("correct_answer", ""),
            subject=question_data.get("subject", ""),
            area_name=question_data.get("area_name", ""),
            difficulty=difficulty,
            year=question_data.get("year")
        )
        
        # 임베딩 생성 (필요한 경우)
        if create_embedding_vector and content:
            # 임베딩용 텍스트 생성 (문제 내용 + 선택지)
            embedding_text = content
            options = question_data.get("options", {})
            if options:
                embedding_text += " " + " ".join(options.values())
            
            try:
                # OpenAI 임베딩 생성
                # DeepSeek 임베딩 생성 (동기 호출)
                import asyncio
                try:
                    loop = asyncio.get_event_loop()
                except RuntimeError:
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                
                embedding_result = loop.run_until_complete(
                    deepseek_service.create_embeddings([embedding_text])
                )
                
                if embedding_result["success"] and embedding_result["embeddings"]:
                    question.embedding = embedding_result["embeddings"][0]
            except Exception as e:
                logger.error(f"임베딩 생성 오류: {str(e)}")
        
        # 데이터베이스에 저장
        db.add(question)
        db.flush()
        
        return question, True
    
    except Exception as e:
        db.rollback()
        logger.error(f"문제 저장 오류: {str(e)}")
        return None, False


def save_parsed_questions(
    db: Session,
    parsed_data: Dict[str, Any],
    source_name: str,
    subject_name: Optional[str] = None,
    create_embeddings: bool = True,
    user_id: Optional[int] = None
) -> Tuple[int, int]:
    """
    레거시 함수 - 하위 호환성을 위해 유지
    새로운 코드에서는 save_converted_db_format_data 사용 권장
    """
    try:
        # 출처 찾기 또는 생성
        source = db.query(Source).filter(Source.name == source_name).first()
        if not source:
            source = Source(
                name=source_name,
                description=f"{source_name}에서 추출한 문제",
                type="시험"
            )
            db.add(source)
            db.flush()
        
        # 과목 찾기 또는 생성 (제공된 경우)
        subject = None
        if subject_name:
            subject = db.query(Subject).filter(Subject.name == subject_name).first()
            if not subject:
                subject = Subject(
                    name=subject_name,
                    description=f"{subject_name} 과목"
                )
                db.add(subject)
                db.flush()
        
        # 문제 리스트 확인
        questions_data = []
        
        if "questions" in parsed_data and isinstance(parsed_data["questions"], list):
            questions_data = parsed_data["questions"]
        elif isinstance(parsed_data, list):
            questions_data = parsed_data
        
        # 없으면 빈 리스트로 처리
        if not questions_data:
            logger.warning("파싱된 문제가 없습니다.")
            return 0, 0
        
        # 각 문제 저장
        success_count = 0
        total_count = len(questions_data)
        
        for question_data in questions_data:
            question, success = create_question_from_data(
                db=db,
                question_data=question_data,
                subject_id=subject.id if subject else None,
                source_id=source.id,
                create_embedding_vector=create_embeddings,
                user_id=user_id
            )
            
            if success:
                success_count += 1
        
        # 변경사항 커밋
        db.commit()
        return success_count, total_count
    
    except SQLAlchemyError as e:
        db.rollback()
        logger.error(f"문제 저장 중 데이터베이스 오류: {str(e)}")
        return 0, 0
    except Exception as e:
        db.rollback()
        logger.error(f"문제 저장 중 오류 발생: {str(e)}")
        return 0, 0


def update_question_embeddings(
    db: Session,
    question_ids: List[int] = None,
    model_type: str = "openai",
    model_name: Optional[str] = None,
    batch_size: int = 50
) -> Tuple[int, int]:
    """
    기존 문제의 임베딩 업데이트
    """
    try:
        # 처리할 문제 쿼리
        query = db.query(Question)
        if question_ids:
            query = query.filter(Question.id.in_(question_ids))
        else:
            # 임베딩이 없는 문제만 처리
            query = query.filter(Question.embedding.is_(None))
        
        total_count = query.count()
        success_count = 0
        
        # 배치 처리
        for offset in range(0, total_count, batch_size):
            batch = query.limit(batch_size).offset(offset).all()
            texts = []
            
            for question in batch:
                # 임베딩용 텍스트 생성 (문제 내용 + 선택지)
                embedding_text = question.content
                if question.options:
                    embedding_text += " " + " ".join(question.options.values())
                texts.append(embedding_text)
            
            # 임베딩 생성 (배치)
            if texts:
                try:
                    embeddings = create_embedding(
                        text=texts,
                        model_type=model_type,
                        model_name=model_name
                    )
                    
                    # 각 문제에 임베딩 할당
                    for i, question in enumerate(batch):
                        if i < len(embeddings):
                            question.embedding = embeddings[i]
                            success_count += 1
                    
                    # 변경사항 저장
                    db.commit()
                
                except Exception as e:
                    db.rollback()
                    logger.error(f"임베딩 배치 생성 오류: {str(e)}")
        
        return success_count, total_count
    
    except Exception as e:
        db.rollback()
        logger.error(f"임베딩 업데이트 오류: {str(e)}")
        return 0, 0


def process_parsed_json_file(
    file_path: str,
    db: Session = None,
    source_name: Optional[str] = None,
    subject_name: Optional[str] = None,
    create_embeddings: bool = True,
    user_id: Optional[int] = None
) -> Dict[str, Any]:
    """
    레거시 함수 - 하위 호환성을 위해 유지
    """
    try:
        # JSON 파일 로드
        with open(file_path, 'r', encoding='utf-8') as f:
            parsed_data = json.load(f)
        
        # 출처 이름이 없으면 파일명에서 추출
        if not source_name:
            import os
            file_name = os.path.basename(file_path)
            source_name = os.path.splitext(file_name)[0]
        
        # 데이터베이스 세션 관리
        should_close_db = False
        if db is None:
            db = next(get_db())
            should_close_db = True
        
        try:
            # 문제 저장
            success_count, total_count = save_parsed_questions(
                db=db,
                parsed_data=parsed_data,
                source_name=source_name,
                subject_name=subject_name,
                create_embeddings=create_embeddings,
                user_id=user_id
            )
            
            result = {
                "success": True,
                "total_questions": total_count,
                "saved_questions": success_count,
                "file_path": file_path,
                "source_name": source_name,
                "subject_name": subject_name
            }
            
        finally:
            if should_close_db:
                db.close()
        
        return result
    
    except Exception as e:
        logger.error(f"JSON 파일 처리 오류: {str(e)}")
        return {
            "success": False,
            "error": str(e),
            "file_path": file_path
        }


def save_parsed_questions_with_excel_data(
    db: Session,
    matched_data: List[Dict[str, Any]],
    source_name: str,
    create_embeddings: bool = True,
    user_id: Optional[int] = None
) -> Tuple[int, int]:
    """
    레거시 함수 - 하위 호환성을 위해 유지
    새로운 코드에서는 process_files_with_gemini_parser 사용 권장
    """
    try:
        # 출처 찾기 또는 생성
        source = db.query(Source).filter(Source.name == source_name).first()
        if not source:
            year = matched_data[0].get("year") if matched_data else None
            source = Source(
                name=source_name,
                description=f"{source_name} 기출문제",
                type="국가고시",
                year=year
            )
            db.add(source)
            db.flush()
        
        success_count = 0
        total_count = len(matched_data)
        
        # 각 문제 저장
        for item in matched_data:
            try:
                # 과목 찾기 또는 생성
                subject_name = item.get("subject") or item.get("subject_name")
                subject = None
                if subject_name:
                    subject = db.query(Subject).filter(Subject.name == subject_name).first()
                    if not subject:
                        subject = Subject(
                            name=subject_name,
                            description=f"{subject_name} 과목"
                        )
                        db.add(subject)
                        db.flush()
                
                # 문제 객체 생성 (새로운 스키마 사용)
                question = Question(
                    question_number=item.get("question_number", 1),
                    content=item.get("content", ""),
                    description=item.get("description"),
                    options=item.get("options", {}),
                    correct_answer=item.get("correct_answer", ""),
                    subject=subject_name or "",
                    area_name=item.get("area_name", ""),
                    difficulty=DifficultyLevel(item.get("difficulty", "중")),
                    year=item.get("year")
                )
                
                # 이미지 URL 추가
                if item.get("image_urls"):
                    question.image_urls = item["image_urls"]
                
                # DeepSeek 임베딩 생성
                if create_embeddings and question.content:
                    embedding_text = question.content
                    options = item.get("options", {})
                    if options:
                        embedding_text += " " + " ".join(options.values())
                    
                    try:
                        # DeepSeek 임베딩 생성 (동기 호출)
                        import asyncio
                        try:
                            loop = asyncio.get_event_loop()
                        except RuntimeError:
                            loop = asyncio.new_event_loop()
                            asyncio.set_event_loop(loop)
                        
                        embedding_result = loop.run_until_complete(
                            deepseek_service.create_embeddings([embedding_text])
                        )
                        
                        if embedding_result["success"] and embedding_result["embeddings"]:
                            question.embedding = embedding_result["embeddings"][0]
                    except Exception as e:
                        logger.warning(f"DeepSeek 임베딩 생성 실패: {e}")
                
                # 데이터베이스에 추가
                db.add(question)
                db.flush()
                success_count += 1
                
            except Exception as e:
                logger.error(f"문제 저장 오류 (문제 {item.get('question_number')}): {e}")
                continue
        
        # 커밋
        db.commit()
        return success_count, total_count
        
    except Exception as e:
        db.rollback()
        logger.error(f"전체 저장 프로세스 오류: {e}")
        return 0, total_count


def process_excel_and_questions(
    db: Session,
    excel_path: str,
    questions_data: Union[str, List[Dict[str, Any]]],
    source_name: Optional[str] = None,
    create_embeddings: bool = True,
    user_id: Optional[int] = None,
    gemini_api_key: Optional[str] = None
) -> Dict[str, Any]:
    """
    레거시 함수 - 하위 호환성을 위해 유지
    새로운 코드에서는 process_files_with_gemini_parser 사용 권장
    """
    try:
        from .question_parser import QuestionParser
        
        # 파서 초기화
        parser = QuestionParser(api_key=gemini_api_key or settings.GEMINI_API_KEY)
        
        # 1. 문제 파일 파싱
        if isinstance(questions_data, str):
            # 파일 경로인 경우
            questions_result = parser.parse_any_file(questions_data, content_type="questions")
            questions = questions_result.get("data", [])
        else:
            # 이미 파싱된 데이터인 경우
            questions = questions_data
        
        # 2. 정답 파일 파싱
        answers_result = parser.parse_any_file(excel_path, content_type="answers")
        answers = answers_result.get("data", [])
        
        if not answers:
            return {
                "success": False,
                "error": "정답 데이터를 찾을 수 없습니다."
            }
        
        # 3. 연도별로 그룹화 및 매칭
        from collections import defaultdict
        questions_by_year = defaultdict(list)
        answers_by_year = defaultdict(list)
        
        # 문제를 연도별로 그룹화
        for q in questions:
            year = str(q.get("year", "unknown"))
            questions_by_year[year].append(q)
        
        # 정답을 연도별로 그룹화
        for a in answers:
            year = str(a.get("year", "unknown"))
            answers_by_year[year].append(a)
        
        # 4. 연도별로 매칭 및 저장
        total_saved = 0
        total_questions = 0
        results_by_year = {}
        
        # 모든 연도에 대해 처리
        all_years = set(questions_by_year.keys()) | set(answers_by_year.keys())
        
        for year in all_years:
            year_questions = questions_by_year.get(year, [])
            year_answers = answers_by_year.get(year, [])
            
            if not year_questions:
                continue
            
            # 문제와 정답 매칭
            matched_data = parser.match_questions_with_answers(
                year_questions, 
                year_answers
            )
            
            # 출처 이름 생성
            year_source_name = source_name or f"{year}년도 물리치료사 국가시험"
            
            # 데이터베이스에 저장
            saved, total = save_parsed_questions_with_excel_data(
                db=db,
                matched_data=matched_data,
                source_name=year_source_name,
                create_embeddings=create_embeddings,
                user_id=user_id
            )
            
            total_saved += saved
            total_questions += total
            results_by_year[year] = {
                "saved": saved,
                "total": total,
                "match_rate": f"{(saved/total*100):.1f}%" if total > 0 else "0%"
            }
        
        return {
            "success": True,
            "total_questions": total_questions,
            "saved_questions": total_saved,
            "save_rate": f"{(total_saved/total_questions*100):.1f}%" if total_questions > 0 else "0%",
            "results_by_year": results_by_year,
            "excel_path": excel_path
        }
        
    except Exception as e:
        logger.error(f"파일 처리 오류: {e}")
        return {
            "success": False,
            "error": str(e)
        } 