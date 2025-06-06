"""
애플리케이션 설정
"""
import os
from typing import Optional, List
from functools import lru_cache

try:
    from pydantic_settings import BaseSettings
    from pydantic import Field
except ImportError:
    # Pydantic v1 호환성
    from pydantic import BaseSettings, Field

class Settings(BaseSettings):
    """애플리케이션 설정"""
    
    # 기본 설정
    PROJECT_NAME: str = Field(default="CampusON API", description="프로젝트 이름")
    VERSION: str = Field(default="0.1.0", description="API 버전")
    DESCRIPTION: str = Field(
        default="경복대학교 학습 지원 플랫폼 API", 
        description="API 설명"
    )
    
    # 서버 설정
    HOST: str = Field(default="0.0.0.0", description="서버 호스트")
    PORT: int = Field(default=8000, description="서버 포트")
    DEBUG: bool = Field(default=True, description="디버그 모드")
    
    # JWT 토큰 설정
    JWT_SECRET_KEY: str = Field(default="dev-secret-key-change-in-production", description="JWT 암호화 키")
    JWT_ALGORITHM: str = Field(default="HS256", description="JWT 알고리즘")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = Field(default=30, description="액세스 토큰 만료 시간 (분)")
    REFRESH_TOKEN_EXPIRE_DAYS: int = Field(default=7, description="리프레시 토큰 만료 시간 (일)")
    
    # 보안 설정 (기존 호환성 유지)
    SECRET_KEY: str = Field(default="dev-secret-key-change-in-production", description="일반 암호화 키")
    ALGORITHM: str = Field(default="HS256", description="암호화 알고리즘")
    
    # 데이터베이스 설정
    DATABASE_URL: str = Field(default="postgresql://admin:1234@localhost:5432/kb_learning_db", description="데이터베이스 URL")
    DATABASE_ECHO: bool = Field(default=False, description="SQL 쿼리 로깅")
    
    # PostgreSQL 벡터 확장 설정
    PGVECTOR_ENABLED: bool = Field(default=True, description="pgvector 확장 사용 여부")
    VECTOR_DIMENSION: int = Field(default=1536, description="벡터 차원 수")
    
    # Redis 설정 (캐싱)
    REDIS_URL: Optional[str] = Field(default=None, description="Redis URL")
    CACHE_TTL_SECONDS: int = Field(default=3600, description="캐시 TTL (초)")
    
    # CORS 설정
    ALLOWED_ORIGINS: List[str] = Field(
        default=["http://localhost:3000", "http://localhost:5173", "http://localhost:8080"],
        description="허용된 CORS 오리진"
    )
    ALLOWED_METHODS: List[str] = Field(
        default=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        description="허용된 HTTP 메서드"
    )
    ALLOWED_HEADERS: List[str] = Field(
        default=["*"],
        description="허용된 HTTP 헤더"
    )
    
    # AI 모델 설정 (EXAONE)
    AI_MODEL_PATH: Optional[str] = Field(default=None, description="AI 모델 경로")
    AI_MODEL_NAME: str = Field(default="exaone-deep-32b", description="AI 모델 이름")
    AI_MODEL_URL: str = Field(default="https://api.exaone.ai/v1", description="AI 모델 API URL")
    AI_API_KEY: Optional[str] = Field(default=None, description="AI 모델 API 키")
    AI_MAX_TOKENS: int = Field(default=2048, description="AI 생성 최대 토큰 수")
    AI_TEMPERATURE: float = Field(default=0.7, description="AI 생성 온도")
    
    # Gemini AI 설정
    GEMINI_API_KEY: str = Field(
        default="AIzaSyCEGkV7L6p5fCJ0V8Bf_WVeO4A-1kBO-X4", 
        description="Gemini API 키"
    )
    GEMINI_MODEL_NAME: str = Field(
        default="gemini-1.5-flash-latest", 
        description="Gemini 모델 이름"
    )
    
    # 임베딩 모델 설정
    EMBEDDING_MODEL_NAME: str = Field(
        default="sentence-transformers/all-MiniLM-L6-v2",
        description="임베딩 모델 이름"
    )
    EMBEDDING_BATCH_SIZE: int = Field(default=32, description="임베딩 배치 크기")
    
    # 파일 업로드 설정
    MAX_FILE_SIZE_MB: int = Field(default=50, description="최대 파일 크기 (MB)")
    UPLOAD_DIRECTORY: str = Field(default="uploads", description="업로드 디렉토리")
    ALLOWED_FILE_EXTENSIONS: List[str] = Field(
        default=[".pdf", ".docx", ".txt", ".md"],
        description="허용된 파일 확장자"
    )
    
    # 로깅 설정
    LOG_LEVEL: str = Field(default="INFO", description="로그 레벨")
    LOG_FILE: Optional[str] = Field(default=None, description="로그 파일 경로")
    
    # 이메일 설정 (SMS 인증 등)
    SMTP_SERVER: Optional[str] = Field(default=None, description="SMTP 서버")
    SMTP_PORT: int = Field(default=587, description="SMTP 포트")
    SMTP_USERNAME: Optional[str] = Field(default=None, description="SMTP 사용자명")
    SMTP_PASSWORD: Optional[str] = Field(default=None, description="SMTP 비밀번호")
    
    # SMS 인증 설정
    SMS_API_KEY: Optional[str] = Field(default=None, description="SMS API 키")
    SMS_API_SECRET: Optional[str] = Field(default=None, description="SMS API 시크릿")
    
    # 소셜 로그인 설정
    KAKAO_CLIENT_ID: Optional[str] = Field(default=None, description="카카오 클라이언트 ID")
    KAKAO_CLIENT_SECRET: Optional[str] = Field(default=None, description="카카오 클라이언트 시크릿")
    
    NAVER_CLIENT_ID: Optional[str] = Field(default=None, description="네이버 클라이언트 ID")
    NAVER_CLIENT_SECRET: Optional[str] = Field(default=None, description="네이버 클라이언트 시크릿")
    
    GOOGLE_CLIENT_ID: Optional[str] = Field(default=None, description="구글 클라이언트 ID")
    GOOGLE_CLIENT_SECRET: Optional[str] = Field(default=None, description="구글 클라이언트 시크릿")
    
    # 모니터링 설정
    PROMETHEUS_ENABLED: bool = Field(default=False, description="Prometheus 메트릭 활성화")
    GRAFANA_ENABLED: bool = Field(default=False, description="Grafana 대시보드 활성화")
    
    # 보안 헤더 설정
    SECURITY_HEADERS_ENABLED: bool = Field(default=True, description="보안 헤더 활성화")
    
    # 공개 API 설정
    PUBLIC_API_ENABLED: bool = Field(default=True, description="공개 API 활성화")
    PUBLIC_API_RATE_LIMIT: int = Field(default=100, description="공개 API 요청 제한 (시간당)")
    
    # 진단 테스트 설정
    DIAGNOSIS_TEST_TIME_LIMIT_MINUTES: int = Field(default=60, description="진단 테스트 제한 시간 (분)")
    DIAGNOSIS_QUESTIONS_PER_DIFFICULTY: int = Field(default=6, description="난이도별 진단 문제 수")
    
    # 학습 추천 설정
    RECOMMENDATION_ALGORITHM: str = Field(
        default="hybrid", 
        description="추천 알고리즘 (collaborative, content, hybrid)"
    )
    MAX_RECOMMENDATIONS: int = Field(default=50, description="최대 추천 문제 수")
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True
        # .env 파일이 없어도 에러를 발생시키지 않음
        env_ignore_empty = True

@lru_cache()
def get_settings() -> Settings:
    """설정 객체 반환 (캐시됨)"""
    try:
        return Settings()
    except Exception:
        # .env 파일에 문제가 있어도 기본값으로 설정 생성
        return Settings(_env_file=None)

# 전역 설정 인스턴스
settings = get_settings()

# 개발/프로덕션 환경별 설정
class DevelopmentSettings(Settings):
    """개발 환경 설정"""
    DEBUG: bool = True
    DATABASE_ECHO: bool = True
    LOG_LEVEL: str = "DEBUG"

class ProductionSettings(Settings):
    """프로덕션 환경 설정"""
    DEBUG: bool = False
    DATABASE_ECHO: bool = False
    LOG_LEVEL: str = "WARNING"
    SECURITY_HEADERS_ENABLED: bool = True

class TestSettings(Settings):
    """테스트 환경 설정"""
    DEBUG: bool = True
    DATABASE_URL: str = "sqlite:///./test.db"
    SECRET_KEY: str = "test-secret-key"

def get_environment_settings() -> Settings:
    """환경별 설정 반환"""
    env = os.getenv("ENVIRONMENT", "development").lower()
    
    if env == "production":
        return ProductionSettings()
    elif env == "test":
        return TestSettings()
    else:
        return DevelopmentSettings() 