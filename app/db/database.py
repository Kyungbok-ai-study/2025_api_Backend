"""
PostgreSQL 데이터베이스 연결 설정
"""
import os
from typing import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session, declarative_base

from app.core.config import settings

# Base 클래스 생성
Base = declarative_base()

# 동기 엔진 생성
engine = create_engine(
    settings.DATABASE_URL,
    echo=settings.DATABASE_ECHO,
    pool_pre_ping=True,
    pool_recycle=300,
    pool_size=5,
    max_overflow=10
)

# 동기 세션 팩토리
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# 동기 데이터베이스 세션 의존성
def get_db() -> Generator[Session, None, None]:
    """
    동기 데이터베이스 세션을 가져오는 의존성 함수
    
    Returns:
        Generator[Session, None, None]: 동기 데이터베이스 세션
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# 테스트용 동기 세션 생성
def get_test_db_session() -> Session:
    """
    테스트용 동기 세션 생성
    """
    return SessionLocal()

# 데이터베이스 초기화 함수
def init_database():
    """
    데이터베이스 테이블 생성
    """
    Base.metadata.create_all(bind=engine) 