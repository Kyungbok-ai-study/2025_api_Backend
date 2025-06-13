"""
학습 분석 및 모니터링 관련 데이터베이스 모델
"""
from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean, ForeignKey, JSON, Float, Date
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import enum
from sqlalchemy.dialects.postgresql import ENUM

from app.db.database import Base

class StudentActivity(Base):
    """학생 활동 로그"""
    __tablename__ = "student_activities"
    
    id = Column(Integer, primary_key=True, index=True)
    student_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    
    # 활동 정보
    activity_type = Column(String(50), nullable=False)  # 'login', 'assignment_submit', 'test_take', etc.
    activity_description = Column(Text, nullable=True)
    
    # 관련 객체 ID
    related_assignment_id = Column(Integer, ForeignKey("assignments.id"), nullable=True)
    related_test_id = Column(Integer, nullable=True)
    
    # 성과 정보
    score = Column(Float, nullable=True)
    time_spent_minutes = Column(Integer, nullable=True)
    
    # 시간 정보
    activity_date = Column(Date, nullable=False, index=True)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    
    # 관계 설정
    student = relationship("User", foreign_keys=[student_id])
    related_assignment = relationship("Assignment", foreign_keys=[related_assignment_id])
    
    def __repr__(self):
        return f"<StudentActivity(id={self.id}, student_id={self.student_id}, type={self.activity_type})>"

class StudentWarning(Base):
    """학생 경고 시스템"""
    __tablename__ = "student_warnings"
    
    id = Column(Integer, primary_key=True, index=True)
    student_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    professor_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    
    # 경고 정보
    warning_type = Column(String(50), nullable=False)  # 'low_score', 'missing_assignment', 'no_activity'
    severity = Column(String(20), nullable=False)  # 'low', 'medium', 'high', 'critical'
    
    title = Column(String(200), nullable=False)
    description = Column(Text, nullable=False)
    
    # 관련 데이터
    related_data = Column(JSON, nullable=True)  # 경고 관련 추가 데이터
    
    # 상태
    is_resolved = Column(Boolean, default=False, nullable=False)
    resolved_at = Column(DateTime, nullable=True)
    
    # 시간 정보
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    
    # 관계 설정
    student = relationship("User", foreign_keys=[student_id])
    professor = relationship("User", foreign_keys=[professor_id])
    
    def __repr__(self):
        return f"<StudentWarning(id={self.id}, student_id={self.student_id}, type={self.warning_type})>"

class LearningAnalytics(Base):
    """학습 분석 데이터"""
    __tablename__ = "learning_analytics"
    
    id = Column(Integer, primary_key=True, index=True)
    student_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    
    # 기간 정보
    analysis_date = Column(Date, nullable=False, index=True)
    week_of_year = Column(Integer, nullable=False)
    month = Column(Integer, nullable=False)
    year = Column(Integer, nullable=False)
    
    # 활동 통계
    total_activities = Column(Integer, default=0, nullable=False)
    login_count = Column(Integer, default=0, nullable=False)
    assignments_submitted = Column(Integer, default=0, nullable=False)
    tests_taken = Column(Integer, default=0, nullable=False)
    
    # 성과 통계
    average_score = Column(Float, nullable=True)
    total_study_time_minutes = Column(Integer, default=0, nullable=False)
    
    # 비교 데이터
    class_rank = Column(Integer, nullable=True)
    class_percentile = Column(Float, nullable=True)
    
    # 시간 정보
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now(), nullable=False)
    
    # 관계 설정
    student = relationship("User", foreign_keys=[student_id])
    
    def __repr__(self):
        return f"<LearningAnalytics(id={self.id}, student_id={self.student_id}, date={self.analysis_date})>"

class ClassStatistics(Base):
    """반/학과 통계"""
    __tablename__ = "class_statistics"
    
    id = Column(Integer, primary_key=True, index=True)
    
    # 분류 정보
    school = Column(String(100), nullable=False)
    department = Column(String(100), nullable=False)
    subject = Column(String(100), nullable=True)
    
    # 기간 정보
    analysis_date = Column(Date, nullable=False, index=True)
    
    # 통계 데이터
    total_students = Column(Integer, nullable=False)
    active_students = Column(Integer, nullable=False)
    average_score = Column(Float, nullable=True)
    average_attendance = Column(Float, nullable=True)
    
    # 경고 레벨 학생 수
    critical_students = Column(Integer, default=0, nullable=False)
    warning_students = Column(Integer, default=0, nullable=False)
    
    # 시간 정보
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now(), nullable=False)
    
    def __repr__(self):
        return f"<ClassStatistics(id={self.id}, school={self.school}, department={self.department})>"

class ProfessorDashboardData(Base):
    """교수 대시보드 집계 데이터"""
    __tablename__ = "professor_dashboard_data"
    
    id = Column(Integer, primary_key=True, index=True)
    professor_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    
    # 기간 정보
    data_date = Column(Date, nullable=False, index=True)
    
    # 학생 통계
    total_students = Column(Integer, nullable=False)
    active_students = Column(Integer, nullable=False)
    critical_students = Column(Integer, default=0, nullable=False)
    warning_students = Column(Integer, default=0, nullable=False)
    
    # 과제 통계
    total_assignments = Column(Integer, nullable=False)
    pending_assignments = Column(Integer, nullable=False)
    graded_assignments = Column(Integer, nullable=False)
    
    # 성과 통계
    class_average_score = Column(Float, nullable=True)
    department_average_score = Column(Float, nullable=True)
    school_average_score = Column(Float, nullable=True)
    
    # 활동 통계
    daily_logins = Column(Integer, default=0, nullable=False)
    current_online_students = Column(Integer, default=0, nullable=False)
    
    # 시간 정보
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now(), nullable=False)
    
    # 관계 설정
    professor = relationship("User", foreign_keys=[professor_id])
    
    def __repr__(self):
        return f"<ProfessorDashboardData(id={self.id}, professor_id={self.professor_id}, date={self.data_date})>" 