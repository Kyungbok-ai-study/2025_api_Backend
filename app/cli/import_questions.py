#!/usr/bin/env python
"""
파싱된 문제 데이터 임포트 스크립트

이 스크립트는 파싱된 JSON 파일에서 문제 데이터를 읽어 데이터베이스에 저장합니다.
텍스트 임베딩 생성 및 저장 기능도 포함되어 있습니다.
"""
import os
import sys
import argparse
import logging
import json
import glob
from typing import List, Optional

# 프로젝트 루트 경로를 파이썬 경로에 추가 (상대 경로 임포트를 위해)
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))

from app.services.question_service import process_parsed_json_file, update_question_embeddings
from app.db.database import get_db, engine, Base
from app.db.session import SessionLocal


# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('import_questions.log')
    ]
)
logger = logging.getLogger(__name__)


def setup_database():
    """데이터베이스 테이블 생성 (없는 경우)"""
    try:
        Base.metadata.create_all(bind=engine)
        logger.info("데이터베이스 테이블이 준비되었습니다.")
    except Exception as e:
        logger.error(f"데이터베이스 설정 오류: {str(e)}")
        sys.exit(1)


def import_question_file(
    file_path: str,
    subject_name: Optional[str] = None,
    source_name: Optional[str] = None,
    create_embeddings: bool = True
) -> bool:
    """
    단일 JSON 파일을 데이터베이스에 임포트
    
    Args:
        file_path (str): JSON 파일 경로
        subject_name (str, optional): 과목 이름
        source_name (str, optional): 출처 이름
        create_embeddings (bool): 임베딩 생성 여부
        
    Returns:
        bool: 성공 여부
    """
    try:
        # 세션 생성
        db = SessionLocal()
        
        # 출처 이름이 없는 경우 파일명 사용
        if not source_name:
            file_name = os.path.basename(file_path)
            source_name = os.path.splitext(file_name)[0]
        
        # 과목 이름 추출 (파일 경로에서, 없는 경우)
        if not subject_name:
            # 디렉토리 경로에서 과목명 추출 시도
            dir_path = os.path.dirname(file_path)
            if os.path.basename(dir_path) != "":
                subject_name = os.path.basename(dir_path)
        
        logger.info(f"파일 임포트 시작: {file_path}")
        logger.info(f"과목: {subject_name or '미지정'}, 출처: {source_name}")
        
        # 임포트 실행
        result = process_parsed_json_file(
            file_path=file_path,
            db=db,
            source_name=source_name,
            subject_name=subject_name,
            create_embeddings=create_embeddings
        )
        
        db.close()
        
        if result["success"]:
            logger.info(f"파일 임포트 완료: {result['saved_questions']}/{result['total_questions']} 문제 저장됨")
            return True
        else:
            logger.error(f"파일 임포트 실패: {result.get('error', '알 수 없는 오류')}")
            return False
            
    except Exception as e:
        logger.error(f"파일 임포트 중 오류 발생: {str(e)}")
        return False


def import_questions_batch(
    file_patterns: List[str],
    subject_name: Optional[str] = None,
    source_name: Optional[str] = None,
    create_embeddings: bool = True
) -> (int, int):
    """
    여러 JSON 파일을 데이터베이스에 일괄 임포트
    
    Args:
        file_patterns (List[str]): 파일 경로 패턴 목록 (glob 패턴 지원)
        subject_name (str, optional): 과목 이름
        source_name (str, optional): 출처 이름
        create_embeddings (bool): 임베딩 생성 여부
        
    Returns:
        (int, int): 성공한 파일 수와 총 파일 수
    """
    all_files = []
    for pattern in file_patterns:
        matched_files = glob.glob(pattern)
        all_files.extend(matched_files)
    
    if not all_files:
        logger.warning(f"일치하는 파일이 없습니다: {file_patterns}")
        return 0, 0
    
    logger.info(f"총 {len(all_files)}개 파일을 찾았습니다.")
    
    success_count = 0
    for file_path in all_files:
        if import_question_file(
            file_path,
            subject_name=subject_name,
            source_name=source_name,
            create_embeddings=create_embeddings
        ):
            success_count += 1
    
    return success_count, len(all_files)


def update_embeddings_cli(
    question_ids: Optional[List[int]] = None,
    model_type: str = "openai",
    model_name: Optional[str] = None,
    batch_size: int = 50
) -> (int, int):
    """
    CLI에서 임베딩 업데이트 실행
    
    Args:
        question_ids (List[int], optional): 문제 ID 목록
        model_type (str): 모델 유형
        model_name (str, optional): 모델 이름
        batch_size (int): 배치 크기
        
    Returns:
        (int, int): 성공한 업데이트 수와 총 문제 수
    """
    try:
        # 세션 생성
        db = SessionLocal()
        
        logger.info(f"임베딩 업데이트 시작 (모델: {model_type})")
        
        success_count, total_count = update_question_embeddings(
            db=db,
            question_ids=question_ids,
            model_type=model_type,
            model_name=model_name,
            batch_size=batch_size
        )
        
        db.close()
        
        logger.info(f"임베딩 업데이트 완료: {success_count}/{total_count} 문제 업데이트됨")
        return success_count, total_count
        
    except Exception as e:
        logger.error(f"임베딩 업데이트 중 오류 발생: {str(e)}")
        return 0, 0


def main():
    """메인 함수"""
    parser = argparse.ArgumentParser(description="파싱된 문제 데이터 임포트 스크립트")
    subparsers = parser.add_subparsers(dest="command", help="명령어")
    
    # 임포트 명령어
    import_parser = subparsers.add_parser("import", help="문제 데이터 임포트")
    import_parser.add_argument("files", nargs="+", help="임포트할 JSON 파일 경로 (glob 패턴 지원)")
    import_parser.add_argument("--subject", "-s", help="과목 이름")
    import_parser.add_argument("--source", "-o", help="출처 이름")
    import_parser.add_argument("--no-embeddings", action="store_true", help="임베딩 생성 비활성화")
    
    # 임베딩 업데이트 명령어
    embedding_parser = subparsers.add_parser("embeddings", help="임베딩 업데이트")
    embedding_parser.add_argument("--ids", nargs="+", type=int, help="문제 ID 목록")
    embedding_parser.add_argument("--model", "-m", default="openai", choices=["openai", "sentence_transformers"], help="임베딩 모델 유형")
    embedding_parser.add_argument("--model-name", help="구체적인 모델 이름")
    embedding_parser.add_argument("--batch-size", type=int, default=50, help="배치 크기")
    
    args = parser.parse_args()
    
    # 데이터베이스 설정
    setup_database()
    
    if args.command == "import":
        # 문제 임포트
        success_count, total_count = import_questions_batch(
            file_patterns=args.files,
            subject_name=args.subject,
            source_name=args.source,
            create_embeddings=not args.no_embeddings
        )
        
        if total_count > 0:
            logger.info(f"임포트 작업 완료: {success_count}/{total_count} 파일 성공")
            sys.exit(0 if success_count == total_count else 1)
        else:
            logger.error("임포트할 파일이 없습니다.")
            sys.exit(1)
            
    elif args.command == "embeddings":
        # 임베딩 업데이트
        success_count, total_count = update_embeddings_cli(
            question_ids=args.ids,
            model_type=args.model,
            model_name=args.model_name,
            batch_size=args.batch_size
        )
        
        if total_count > 0:
            logger.info(f"임베딩 업데이트 완료: {success_count}/{total_count} 문제 업데이트됨")
            sys.exit(0 if success_count > 0 else 1)
        else:
            logger.warning("업데이트할 문제가 없습니다.")
            sys.exit(0)
    
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main() 