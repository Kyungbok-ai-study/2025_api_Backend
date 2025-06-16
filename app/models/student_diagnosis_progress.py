"""
학생별 진단테스트 차수 진행 상황 관리 모델
"""
from sqlalchemy import Column, Integer, String, DateTime, Boolean, ForeignKey, JSON, Float, UniqueConstraint
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from sqlalchemy.dialects.postgresql import JSONB
from datetime import datetime
from typing import Optional, Dict, List

from app.db.database import Base

class StudentDiagnosisProgress(Base):
    """학생별 진단테스트 차수 진행 상황"""
    __tablename__ = "student_diagnosis_progress"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    department = Column(String(100), nullable=False, index=True)  # 물리치료학과, 작업치료학과
    
    # 현재 진행 상황
    current_round = Column(Integer, default=0, nullable=False, index=True)  # 현재 차수 (0차부터 시작)
    max_available_round = Column(Integer, default=1, nullable=False)  # 다음 가능한 차수 (1차부터)
    
    # 차수별 완료 상태 (JSON으로 관리)
    completed_rounds = Column(JSONB, default=list, nullable=False)  # [1, 2, 3, ...] 완료된 차수들
    
    # 차수별 상세 기록
    round_details = Column(JSONB, default=dict, nullable=False)  # {
    #     "1": {
    #         "completed_at": "2024-06-16T10:30:00",
    #         "score": 85.5,
    #         "attempts": 1,
    #         "time_spent": 1800,  # 초
    #         "questions_correct": 26,
    #         "questions_total": 30,
    #         "level": "상급",
    #         "session_id": "DIAG_PT_R1_001"
    #     }
    # }
    
    # 전체 진행 통계
    total_tests_completed = Column(Integer, default=0, nullable=False)
    average_score = Column(Float, default=0.0, nullable=False)  # 평균 점수
    total_study_time = Column(Integer, default=0, nullable=False)  # 총 학습 시간 (초)
    
    # 학습 패턴 분석
    learning_pattern = Column(JSONB, nullable=True)  # {
    #     "preferred_time": "morning",
    #     "average_session_duration": 1800,
    #     "difficulty_trend": "improving",
    #     "consistency_score": 0.85,
    #     "weak_areas": ["신경계", "심폐"],
    #     "strong_areas": ["근골격계", "운동치료"]
    # }
    
    # 추천 및 피드백
    next_recommendation = Column(JSONB, nullable=True)  # {
    #     "recommended_round": 3,
    #     "focus_areas": ["신경계 물리치료"],
    #     "study_tips": ["기초 개념 복습 필요"],
    #     "estimated_difficulty": "보통",
    #     "preparation_time": "1-2시간"
    # }
    
    # 상태 관리
    is_active = Column(Boolean, default=True, nullable=False)
    last_test_date = Column(DateTime, nullable=True)
    
    # 타임스탬프
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    
    # 관계 설정
    user = relationship("User", back_populates="diagnosis_progress")
    
    # 유니크 제약 조건 (학생-학과별로 하나씩만)
    __table_args__ = (
        UniqueConstraint('user_id', 'department', name='uq_student_department_progress'),
    )
    
    def __repr__(self):
        return f"<StudentDiagnosisProgress(user_id={self.user_id}, department={self.department}, current_round={self.current_round})>"
    
    def can_take_round(self, round_number: int) -> bool:
        """특정 차수 테스트를 볼 수 있는지 확인"""
        return round_number <= self.max_available_round
    
    def complete_round(self, round_number: int, score: float, session_data: Dict) -> None:
        """차수 완료 처리"""
        if round_number not in self.completed_rounds:
            self.completed_rounds = self.completed_rounds + [round_number]
        
        # 차수별 상세 기록 업데이트
        if not self.round_details:
            self.round_details = {}
        
        self.round_details[str(round_number)] = {
            "completed_at": datetime.now().isoformat(),
            "score": score,
            "attempts": self.round_details.get(str(round_number), {}).get("attempts", 0) + 1,
            "time_spent": session_data.get("time_spent", 0),
            "questions_correct": session_data.get("questions_correct", 0),
            "questions_total": session_data.get("questions_total", 30),
            "level": session_data.get("level", "미분류"),
            "session_id": session_data.get("session_id", "")
        }
        
        # 현재 차수 및 다음 가능한 차수 업데이트
        self.current_round = max(self.current_round, round_number)
        self.max_available_round = min(self.current_round + 1, 10)  # 최대 10차까지
        
        # 통계 업데이트
        self.total_tests_completed = len(self.completed_rounds)
        completed_scores = [details.get("score", 0) for details in self.round_details.values()]
        self.average_score = sum(completed_scores) / len(completed_scores) if completed_scores else 0.0
        self.total_study_time += session_data.get("time_spent", 0)
        self.last_test_date = datetime.now()
    
    def get_next_available_round(self) -> int:
        """다음 가능한 차수 반환"""
        return self.max_available_round
    
    def get_completion_rate(self) -> float:
        """완료율 계산 (0.0 ~ 1.0)"""
        return len(self.completed_rounds) / 10.0  # 총 10차까지 있다고 가정
    
    def is_round_completed(self, round_number: int) -> bool:
        """특정 차수가 완료되었는지 확인"""
        return round_number in self.completed_rounds
    
    def get_round_score(self, round_number: int) -> Optional[float]:
        """특정 차수의 점수 반환"""
        return self.round_details.get(str(round_number), {}).get("score")


class DiagnosisRoundConfig(Base):
    """진단테스트 차수별 설정"""
    __tablename__ = "diagnosis_round_config"
    
    id = Column(Integer, primary_key=True, index=True)
    department = Column(String(100), nullable=False, index=True)  # 물리치료학과, 작업치료학과
    round_number = Column(Integer, nullable=False, index=True)
    
    # 기본 정보
    title = Column(String(200), nullable=False)
    focus_area = Column(String(100), nullable=False)  # 전문 영역
    description = Column(String(500), nullable=True)
    
    # 테스트 설정
    total_questions = Column(Integer, default=30, nullable=False)
    time_limit_minutes = Column(Integer, default=60, nullable=False)
    passing_score = Column(Float, default=60.0, nullable=False)
    
    # 파일 경로
    test_file_path = Column(String(300), nullable=False)
    
    # 차수 조건
    prerequisite_rounds = Column(JSONB, default=list, nullable=False)  # 선수 차수들 [1, 2, ...]
    unlock_condition = Column(JSONB, nullable=True)  # {
    #     "min_score": 70,  # 이전 차수 최소 점수
    #     "required_attempts": 1,  # 필요한 시도 횟수
    #     "time_gap_hours": 24  # 이전 테스트와의 최소 간격
    # }
    
    # 상태
    is_active = Column(Boolean, default=True, nullable=False)
    
    # 타임스탬프
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    
    # 유니크 제약 조건 (학과-차수별로 하나씩만)
    __table_args__ = (
        UniqueConstraint('department', 'round_number', name='uq_department_round'),
    )
    
    def __repr__(self):
        return f"<DiagnosisRoundConfig(department={self.department}, round={self.round_number}, title={self.title})>" 