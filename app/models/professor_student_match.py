"""
교수-학생 매칭 및 모니터링 시스템
"""
from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, Text, JSON
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from sqlalchemy.dialects.postgresql import JSONB
from datetime import datetime

from app.db.database import Base

class ProfessorStudentMatch(Base):
    """교수-학생 매칭 테이블"""
    __tablename__ = "professor_student_matches"
    
    id = Column(Integer, primary_key=True, index=True)
    professor_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    student_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    
    # 매칭 상태
    match_status = Column(String(20), default="pending", nullable=False)  # pending, approved, rejected, auto_matched
    match_method = Column(String(30), default="school_department", nullable=False)  # school_department, manual
    
    # 학교-학과 정보
    match_info = Column(JSONB, nullable=True)  # {
    #     "school": "경복대학교",
    #     "department": "간호학과",
    #     "auto_matched": true,
    #     "confidence_score": 0.95
    # }
    
    # 교수의 결정
    professor_decision = Column(JSONB, nullable=True)  # {
    #     "approved": true,
    #     "decision_at": "2024-01-01T00:00:00",
    #     "reason": "같은 학과 학생 확인"
    # }
    
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now(), nullable=False)
    
    # 관계 설정
    professor = relationship("User", foreign_keys=[professor_id], back_populates="supervised_students")
    student = relationship("User", foreign_keys=[student_id], back_populates="supervisors")

class StudentDiagnosisAlert(Base):
    """학생 진단테스트 알림 테이블"""
    __tablename__ = "student_diagnosis_alerts"
    
    id = Column(Integer, primary_key=True, index=True)
    student_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    professor_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    
    # 진단테스트 정보
    diagnosis_info = Column(JSONB, nullable=False)  # {
    #     "test_id": "diag_2024_001",
    #     "test_type": "종합진단",
    #     "started_at": "2024-01-01T10:00:00",
    #     "completed_at": "2024-01-01T10:30:00",
    #     "score": 85.5,
    #     "total_questions": 50,
    #     "correct_answers": 42
    # }
    
    # 알림 상태
    alert_status = Column(String(20), default="new", nullable=False)  # new, read, archived
    professor_viewed_at = Column(DateTime, nullable=True)
    
    # 교수 메모
    professor_notes = Column(JSONB, nullable=True)  # {
    #     "notes": "학생이 어려움을 겪고 있음",
    #     "action_needed": true,
    #     "follow_up_date": "2024-01-02"
    # }
    
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now(), nullable=False)
    
    # 관계 설정
    student = relationship("User", foreign_keys=[student_id])
    professor = relationship("User", foreign_keys=[professor_id])

class StudentMonitoringLog(Base):
    """학생 모니터링 로그 테이블"""
    __tablename__ = "student_monitoring_logs"
    
    id = Column(Integer, primary_key=True, index=True)
    student_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    professor_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    
    # 모니터링 활동 유형
    activity_type = Column(String(50), nullable=False)  # diagnosis_test, assignment_submit, login, problem_solve
    
    # 활동 상세 정보
    activity_data = Column(JSONB, nullable=False)  # {
    #     "activity_name": "종합진단테스트",
    #     "performance": {
    #         "score": 85.5,
    #         "time_taken": 1800,  # 초
    #         "difficulty_areas": ["해부학", "생리학"]
    #     },
    #     "behavioral_notes": "시간 내 완료, 중간 난이도 문제에서 어려움"
    # }
    
    # 교수 분석
    professor_analysis = Column(JSONB, nullable=True)  # {
    #     "concern_level": "medium",  # low, medium, high
    #     "recommendations": ["추가 학습 자료 제공", "1:1 상담 필요"],
    #     "analysis_notes": "전반적으로 양호하나 특정 분야 보완 필요"
    # }
    
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    
    # 관계 설정
    student = relationship("User", foreign_keys=[student_id])
    professor = relationship("User", foreign_keys=[professor_id]) 