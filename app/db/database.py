"""
PostgreSQL 데이터베이스 연결 설정
"""
import os
from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declarative_base
from dotenv import load_dotenv
import psycopg
import psycopg_pool

# .env 파일 로드
load_dotenv()

# 기본 연결 문자열 (psycopg v3 형식)
DB_DSN = os.getenv("DATABASE_URL", "postgresql://admin:1234@localhost:5432/kb_learning_db")
# SQLAlchemy용 연결 문자열로 변환 (postgresql+asyncpg 형식 - SQLAlchemy 1.4와 호환)
DATABASE_URL = DB_DSN.replace("postgresql://", "postgresql+asyncpg://")

# 엔진 생성
engine = create_async_engine(DATABASE_URL, echo=True, future=False)

# 비동기 세션 설정
async_session = sessionmaker(
    engine, class_=AsyncSession, expire_on_commit=False
)

# Base 클래스 생성 (SQLAlchemy 1.4 방식)
Base = declarative_base()

# 직접 psycopg 연결 풀 생성 (필요시 사용)
async def get_connection_pool():
    """
    psycopg 연결 풀을 가져옵니다.
    """
    pool = psycopg_pool.AsyncConnectionPool(conninfo=DB_DSN)
    await pool.wait()
    return pool

async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    데이터베이스 세션을 가져오는 의존성 함수
    
    Returns:
        AsyncGenerator[AsyncSession, None]: 비동기 데이터베이스 세션
    """
    async with async_session() as session:
        try:
            yield session
        finally:
            await session.close() 