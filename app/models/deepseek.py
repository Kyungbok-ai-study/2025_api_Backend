from sqlalchemy import Column, Integer, String, Text, DateTime, Float, ForeignKey, JSON
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.db.database import Base

class DeepSeekLearningSession(Base):
    """딥시크 학습 세션 모델"""
    __tablename__ = "deepseek_learning_sessions"

    id = Column(Integer, primary_key=True, index=True)
    professor_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    question_id = Column(Integer, ForeignKey("questions.id"), nullable=True)
    
    # 학습 데이터
    learning_data = Column(JSON, nullable=True)  # 학습에 사용된 데이터
    context_data = Column(Text, nullable=True)   # 컨텍스트 정보
    
    # 상태 및 결과
    status = Column(String(50), default='pending')  # pending, processing, completed, failed
    result = Column(Text, nullable=True)           # 학습 결과
    error_message = Column(Text, nullable=True)    # 오류 메시지
    
    # 성능 메트릭
    processing_time = Column(Float, nullable=True)  # 처리 시간 (초)
    tokens_processed = Column(Integer, nullable=True)  # 처리된 토큰 수
    model_response = Column(Text, nullable=True)    # 모델 응답
    
    # 메타데이터
    model_version = Column(String(100), nullable=True)  # 사용된 모델 버전
    learning_type = Column(String(50), default='auto')  # auto, manual, batch
    batch_id = Column(String(100), nullable=True)       # 일괄 처리 ID
    
    # 타임스탬프
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    completed_at = Column(DateTime(timezone=True), nullable=True)

    # 관계
    professor = relationship("User", back_populates="deepseek_sessions")
    question = relationship("Question", back_populates="deepseek_sessions")

    def __repr__(self):
        return f"<DeepSeekLearningSession(id={self.id}, professor_id={self.professor_id}, status='{self.status}')>" 