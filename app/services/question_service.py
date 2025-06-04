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
from datetime import datetime

from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError

from ..db.database import get_db
from ..models.question import (
    Question, AnswerOption, CorrectAnswer, Explanation,
    Tag, Subject, Source, QuestionType, DifficultyLevel
)
from ..utils.embedding_utils import create_embedding


def create_question_from_data(
    db: Session,
    question_data: Dict[str, Any],
    subject_id: Optional[int] = None,
    source_id: Optional[int] = None,
    create_embedding_vector: bool = True,
    user_id: Optional[int] = None
) -> Tuple[Question, bool]:
    """
    파싱된 문제 데이터를 데이터베이스에 저장
    
    Args:
        db (Session): 데이터베이스 세션
        question_data (Dict[str, Any]): 문제 데이터 딕셔너리
        subject_id (int, optional): 과목 ID
        source_id (int, optional): 출처 ID
        create_embedding_vector (bool): 임베딩 벡터 생성 여부
        user_id (int, optional): 생성자 ID
        
    Returns:
        Tuple[Question, bool]: 저장된 문제 객체와 성공 여부
    """
    try:
        # 필수 필드 확인
        content = question_data.get("content")
        if not content:
            logging.error("문제 내용이 없습니다.")
            return None, False
        
        # 문제 유형 결정
        question_type_str = question_data.get("type", "multiple_choice")
        try:
            question_type = QuestionType(question_type_str)
        except ValueError:
            # 기본값으로 설정
            question_type = QuestionType.MULTIPLE_CHOICE
        
        # 난이도 결정
        difficulty_str = question_data.get("difficulty", "medium")
        try:
            difficulty = DifficultyLevel(difficulty_str)
        except ValueError:
            # 기본값으로 설정
            difficulty = DifficultyLevel.MEDIUM
        
        # 문제 객체 생성
        question = Question(
            content=content,
            question_type=question_type,
            difficulty=difficulty,
            subject_id=subject_id,
            source_id=source_id,
            created_by_id=user_id,
            updated_by_id=user_id,
            metadata=question_data.get("metadata", {})
        )
        
        # 이미지 URL 추가 (있는 경우)
        if "image_urls" in question_data and isinstance(question_data["image_urls"], list):
            question.image_urls = question_data["image_urls"]
        
        # 선택지 추가 (객관식인 경우)
        options = question_data.get("options", [])
        if options and isinstance(options, list):
            for i, option_text in enumerate(options):
                # 선택지 레이블 결정 (A, B, C, D, ... 또는 ①, ②, ③, ④, ...)
                if isinstance(option_text, str) and len(option_text) > 1:
                    # 선택지 텍스트에서 레이블 추출 시도 (예: "A. 내용" 또는 "① 내용")
                    if option_text[0] in "①②③④⑤⑥⑦⑧⑨⑩" or option_text[0] in "ABCDEFGHIJ":
                        option_label = option_text[0]
                        # 첫 문자가 레이블인 경우 나머지 부분만 텍스트로 사용
                        if len(option_text) > 2 and option_text[1] in [".", ")", " "]:
                            option_text = option_text[2:].strip()
                    else:
                        option_label = chr(65 + i)  # A, B, C, D, ...
                else:
                    option_label = chr(65 + i)  # A, B, C, D, ...
                
                # 선택지 객체 생성
                option = AnswerOption(
                    option_text=option_text,
                    option_label=option_label,
                    display_order=i+1
                )
                question.options.append(option)
        
        # 정답 추가
        answer = question_data.get("answer")
        if answer:
            # 정답 형식에 따라 처리
            if isinstance(answer, str):
                # 문자열 형태의 정답 (예: "A" 또는 "정답 내용")
                correct_answer = CorrectAnswer(
                    answer_text=answer
                )
                question.correct_answers.append(correct_answer)
            elif isinstance(answer, list):
                # 여러 정답이 있는 경우
                for ans in answer:
                    correct_answer = CorrectAnswer(
                        answer_text=ans
                    )
                    question.correct_answers.append(correct_answer)
            elif isinstance(answer, dict) and "text" in answer:
                # 딕셔너리 형태의 정답
                correct_answer = CorrectAnswer(
                    answer_text=answer["text"]
                )
                question.correct_answers.append(correct_answer)
        
        # 해설 추가
        explanation_text = question_data.get("explanation")
        if explanation_text:
            explanation = Explanation(
                content=explanation_text
            )
            question.explanations.append(explanation)
        
        # 태그 추가
        tags = question_data.get("tags", [])
        if tags and isinstance(tags, list):
            for tag_name in tags:
                # 기존 태그 찾기 또는 새로 생성
                tag = db.query(Tag).filter(Tag.name == tag_name).first()
                if not tag:
                    tag = Tag(name=tag_name)
                    db.add(tag)
                    db.flush()
                question.tags.append(tag)
        
        # 임베딩 생성 (필요한 경우)
        if create_embedding_vector:
            # 임베딩용 텍스트 생성 (문제 내용 + 선택지)
            embedding_text = content
            for option in question.options:
                embedding_text += " " + option.option_text
            
            try:
                # OpenAI 임베딩 생성
                embeddings = create_embedding(embedding_text, model_type="openai")
                if embeddings and len(embeddings) > 0:
                    question.embedding = embeddings[0]
            except Exception as e:
                logging.error(f"임베딩 생성 오류: {str(e)}")
        
        # 데이터베이스에 저장
        db.add(question)
        db.flush()
        
        # 선택지 정답 연결 (필요한 경우)
        answer_labels = question_data.get("answer_labels", [])
        if answer_labels and isinstance(answer_labels, list) and question.options:
            # 레이블로 정답 선택지 찾기 (예: ["A", "C"])
            for label in answer_labels:
                for option in question.options:
                    if option.option_label == label:
                        correct_answer = CorrectAnswer(
                            question_id=question.id,
                            answer_option_id=option.id
                        )
                        db.add(correct_answer)
        
        return question, True
    
    except Exception as e:
        db.rollback()
        logging.error(f"문제 저장 오류: {str(e)}")
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
    파싱된 여러 문제를 데이터베이스에 저장
    
    Args:
        db (Session): 데이터베이스 세션
        parsed_data (Dict[str, Any]): 파싱된 데이터
        source_name (str): 출처 이름
        subject_name (str, optional): 과목 이름
        create_embeddings (bool): 임베딩 벡터 생성 여부
        user_id (int, optional): 생성자 ID
        
    Returns:
        Tuple[int, int]: 성공한 문제 수와 총 문제 수
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
            logging.warning("파싱된 문제가 없습니다.")
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
        logging.error(f"문제 저장 중 데이터베이스 오류: {str(e)}")
        return 0, 0
    except Exception as e:
        db.rollback()
        logging.error(f"문제 저장 중 오류 발생: {str(e)}")
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
    
    Args:
        db (Session): 데이터베이스 세션
        question_ids (List[int], optional): 업데이트할 문제 ID 목록, None이면 모든 문제
        model_type (str): 사용할 모델 유형
        model_name (str, optional): 모델 이름
        batch_size (int): 한 번에 처리할 문제 수
        
    Returns:
        Tuple[int, int]: 성공한 업데이트 수와 총 문제 수
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
                for option in question.options:
                    embedding_text += " " + option.option_text
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
                    logging.error(f"임베딩 배치 생성 오류: {str(e)}")
        
        return success_count, total_count
    
    except Exception as e:
        db.rollback()
        logging.error(f"임베딩 업데이트 오류: {str(e)}")
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
    파싱된 JSON 파일을 읽어 데이터베이스에 저장
    
    Args:
        file_path (str): JSON 파일 경로
        db (Session, optional): 데이터베이스 세션, None이면 새로 생성
        source_name (str, optional): 출처 이름, None이면 파일명 사용
        subject_name (str, optional): 과목 이름
        create_embeddings (bool): 임베딩 벡터 생성 여부
        user_id (int, optional): 생성자 ID
        
    Returns:
        Dict[str, Any]: 처리 결과
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
        logging.error(f"JSON 파일 처리 오류: {str(e)}")
        return {
            "success": False,
            "error": str(e),
            "file_path": file_path
        } 