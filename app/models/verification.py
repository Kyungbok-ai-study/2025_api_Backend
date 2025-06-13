"""
인증 요청 모델 정의
"""
from sqlalchemy import Column, Integer, String, DateTime, Text, Boolean, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from enum import Enum

from app.db.database import Base

class VerificationType(str, Enum):
    STUDENT = "student"
    PROFESSOR = "professor"

class VerificationStatus(str, Enum):
    PENDING = "pending"      # 대기중
    APPROVED = "approved"    # 승인됨
    REJECTED = "rejected"    # 거절됨

class VerificationRequest(Base):
    """
    인증 요청 모델 클래스
    
    Attributes:
        id (int): 인증 요청 고유 ID
        request_number (int): 인증 순서 번호 (관리자용)
        user_id (int): 신청자 사용자 ID
        verification_type (str): 인증 유형 ('student' 또는 'professor')
        reason (str): 신청 사유
        status (str): 처리 상태 ('pending', 'approved', 'rejected')
        submitted_at (datetime): 신청일시
        reviewed_at (datetime): 검토완료일시 (승인/거절)
        reviewed_by (str): 검토자 사용자 ID
        reviewer_comment (str): 검토자 코멘트
        rejection_reason (str): 거부 사유 (거부 시)
        documents (str): 업로드된 문서 파일 경로들 (JSON 형태)
        created_at (datetime): 생성일시
        updated_at (datetime): 수정일시
    """
    __tablename__ = "verification_requests"
    
    id = Column(Integer, primary_key=True, index=True)
    request_number = Column(Integer, unique=True, index=True, nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    verification_type = Column(String(20), nullable=False)  # 'student' or 'professor'
    reason = Column(Text, nullable=False)
    status = Column(String(20), nullable=False, default="pending")  # 'pending', 'approved', 'rejected'
    submitted_at = Column(DateTime, server_default=func.now(), nullable=False)
    reviewed_at = Column(DateTime, nullable=True)
    reviewed_by = Column(String(50), nullable=True)  # 검토자 사용자 ID
    reviewer_comment = Column(Text, nullable=True)
    rejection_reason = Column(Text, nullable=True)  # 거부 사유
    documents = Column(Text, nullable=True)  # JSON 형태로 파일 경로들 저장
    
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now(), nullable=False)
    
    # 관계 설정
    user = relationship("User", back_populates="verification_requests")
    
    def __repr__(self):
        """인증 요청 객체의 문자열 표현"""
        return f"<VerificationRequest(id={self.id}, number={self.request_number}, user_id={self.user_id}, type={self.verification_type}, status={self.status})>"
    
    @property
    def is_pending(self) -> bool:
        """대기중 여부 확인"""
        return self.status == "pending"
    
    @property
    def is_approved(self) -> bool:
        """승인 여부 확인"""
        return self.status == "approved"
    
    @property
    def is_rejected(self) -> bool:
        """거절 여부 확인"""
        return self.status == "rejected"
    
    def get_status_text(self) -> str:
        """상태 텍스트 반환"""
        status_map = {
            "pending": "검토중",
            "approved": "승인됨",
            "rejected": "거절됨"
        }
        return status_map.get(self.status, "알 수 없음")
    
    def get_type_text(self) -> str:
        """인증 유형 텍스트 반환"""
        type_map = {
            "student": "재학생 인증",
            "professor": "교수 인증"
        }
        return type_map.get(self.verification_type, "알 수 없음") 