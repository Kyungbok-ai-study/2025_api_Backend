"""
학과별 진단테스트 서비스
사용자의 학과에 따라 맞춤형 진단테스트를 제공하는 서비스
"""
from typing import List, Dict, Optional, Any, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, func
from datetime import datetime, timedelta

from app.models.unified_diagnosis import (
    DiagnosisTest,
    DiagnosisQuestion,
    DiagnosisSession,
    DiagnosisResponse,
    StudentDiagnosisHistory
)
from app.models.user import User
from app.models.enums import Department, DiagnosisSubject
from app.services.diagnosis_test_loader import diagnosis_test_loader

class DepartmentDiagnosisService:
    """학과별 진단 시스템 서비스"""
    
    def __init__(self, db: Session):
        self.db = db
        self.test_loader = diagnosis_test_loader
        
    def get_available_tests_for_user(self, user: User) -> List[Dict[str, Any]]:
        """사용자 학과에 맞는 사용 가능한 진단테스트 목록 조회"""
        try:
            # 사용자 학과 정보 추출
            user_department = self._get_user_department(user)
            
            # 학과별 진단테스트 조회
            query = self.db.query(DiagnosisTest).filter(
                and_(
                    DiagnosisTest.status == "active",
                    DiagnosisTest.is_published == True,
                    or_(
                        DiagnosisTest.department == user_department,
                        DiagnosisTest.department == "전체학과",  # 전체 학과 대상 테스트
                        DiagnosisTest.subject_area.in_(
                            self._get_applicable_subjects(user_department)
                        )
                    )
                )
            )
            
            # 만료되지 않은 테스트만 필터링
            current_time = datetime.now()
            query = query.filter(
                or_(
                    DiagnosisTest.expire_date.is_(None),
                    DiagnosisTest.expire_date > current_time
                )
            )
            
            tests = query.order_by(DiagnosisTest.created_at.desc()).all()
            
            # 사용자별 테스트 현황 정보 추가
            test_list = []
            for test in tests:
                test_info = self._build_test_info(test, user)
                test_list.append(test_info)
            
            return test_list
            
        except Exception as e:
            raise Exception(f"사용 가능한 테스트 조회 실패: {str(e)}")
    
    def get_department_specific_tests(self, department: str) -> List[Dict[str, Any]]:
        """특정 학과 전용 진단테스트 목록"""
        try:
            tests = self.db.query(DiagnosisTest).filter(
                and_(
                    DiagnosisTest.department == department,
                    DiagnosisTest.status == "active",
                    DiagnosisTest.is_published == True
                )
            ).order_by(DiagnosisTest.created_at.desc()).all()
            
            return [self._build_basic_test_info(test) for test in tests]
            
        except Exception as e:
            raise Exception(f"학과별 테스트 조회 실패: {str(e)}")
    
    def get_recommended_tests_for_user(self, user: User) -> List[Dict[str, Any]]:
        """사용자 맞춤 추천 진단테스트"""
        try:
            # 사용자 이력 기반 추천
            user_history = self._get_user_diagnosis_history(user)
            user_department = self._get_user_department(user)
            
            # 추천 로직
            recommendations = []
            
            # 1. 미완료 테스트 우선 추천
            incomplete_tests = self._get_incomplete_tests(user)
            for test in incomplete_tests:
                test_info = self._build_test_info(test, user)
                test_info["recommendation_reason"] = "미완료 테스트"
                test_info["priority"] = "high"
                recommendations.append(test_info)
            
            # 2. 학과별 필수 테스트
            essential_tests = self._get_essential_tests_for_department(user_department)
            for test in essential_tests:
                if not self._user_completed_test(user, test):
                    test_info = self._build_test_info(test, user)
                    test_info["recommendation_reason"] = "학과 필수 테스트"
                    test_info["priority"] = "high"
                    recommendations.append(test_info)
            
            # 3. 실력 향상 추천 테스트
            improvement_tests = self._get_improvement_tests(user, user_history)
            for test in improvement_tests:
                test_info = self._build_test_info(test, user)
                test_info["recommendation_reason"] = "실력 향상 추천"
                test_info["priority"] = "medium"
                recommendations.append(test_info)
            
            # 4. 도전 테스트 (고급)
            challenge_tests = self._get_challenge_tests(user, user_history)
            for test in challenge_tests:
                test_info = self._build_test_info(test, user)
                test_info["recommendation_reason"] = "도전 과제"
                test_info["priority"] = "low"
                recommendations.append(test_info)
            
            # 중복 제거 및 우선순위 정렬
            unique_recommendations = self._deduplicate_and_sort(recommendations)
            
            return unique_recommendations[:10]  # 최대 10개까지
            
        except Exception as e:
            raise Exception(f"맞춤 추천 테스트 조회 실패: {str(e)}")
    
    def start_diagnosis_session(self, user: User, test_id: int) -> Dict[str, Any]:
        """진단 세션 시작"""
        try:
            # 테스트 유효성 검사
            test = self._validate_test_access(user, test_id)
            
            # 기존 진행 중인 세션 확인
            existing_session = self.db.query(DiagnosisSession).filter(
                and_(
                    DiagnosisSession.user_id == user.id,
                    DiagnosisSession.test_id == test_id,
                    DiagnosisSession.status.in_(["not_started", "in_progress"])
                )
            ).first()
            
            if existing_session:
                # 기존 세션 반환
                return self._build_session_info(existing_session)
            
            # 새 세션 생성
            session_token = self._generate_session_token(user.id, test_id)
            expires_at = datetime.now() + timedelta(minutes=test.time_limit_minutes + 10)
            
            new_session = DiagnosisSession(
                test_id=test_id,
                user_id=user.id,
                session_token=session_token,
                attempt_number=self._get_next_attempt_number(user.id, test_id),
                status="not_started",
                expires_at=expires_at,
                session_metadata={
                    "user_department": self._get_user_department(user),
                    "test_department": test.department,
                    "started_via": "web_interface",
                    "user_level": self._estimate_user_level(user)
                }
            )
            
            self.db.add(new_session)
            self.db.commit()
            
            return self._build_session_info(new_session)
            
        except Exception as e:
            self.db.rollback()
            raise Exception(f"진단 세션 시작 실패: {str(e)}")
    
    def get_department_performance_analytics(self, department: str) -> Dict[str, Any]:
        """학과별 성과 분석"""
        try:
            # 학과별 테스트 통계
            tests_query = self.db.query(DiagnosisTest).filter(
                DiagnosisTest.department == department
            )
            
            total_tests = tests_query.count()
            active_tests = tests_query.filter(DiagnosisTest.status == "active").count()
            
            # 학과 학생들의 진단 세션 통계
            department_users = self.db.query(User).filter(
                User.profile_info['department'].astext == department
            ).all()
            
            user_ids = [user.id for user in department_users]
            
            sessions_query = self.db.query(DiagnosisSession).filter(
                DiagnosisSession.user_id.in_(user_ids)
            )
            
            total_sessions = sessions_query.count()
            completed_sessions = sessions_query.filter(
                DiagnosisSession.status == "completed"
            ).all()
            
            # 성과 분석
            if completed_sessions:
                scores = [s.percentage_score for s in completed_sessions if s.percentage_score]
                avg_score = sum(scores) / len(scores) if scores else 0
                
                # 점수 분포
                score_distribution = {
                    "excellent": len([s for s in scores if s >= 90]),
                    "good": len([s for s in scores if 80 <= s < 90]),
                    "average": len([s for s in scores if 70 <= s < 80]),
                    "poor": len([s for s in scores if 60 <= s < 70]),
                    "fail": len([s for s in scores if s < 60])
                }
            else:
                avg_score = 0
                score_distribution = {}
            
            # 과목별 성과
            subject_performance = self._analyze_subject_performance(user_ids)
            
            # 시간별 추이
            time_trends = self._analyze_time_trends(user_ids)
            
            return {
                "department": department,
                "basic_stats": {
                    "total_tests": total_tests,
                    "active_tests": active_tests,
                    "total_students": len(department_users),
                    "total_sessions": total_sessions,
                    "completed_sessions": len(completed_sessions),
                    "completion_rate": len(completed_sessions) / total_sessions if total_sessions > 0 else 0
                },
                "performance_stats": {
                    "average_score": round(avg_score, 2),
                    "score_distribution": score_distribution
                },
                "subject_performance": subject_performance,
                "time_trends": time_trends,
                "generated_at": datetime.now().isoformat()
            }
            
        except Exception as e:
            raise Exception(f"학과별 성과 분석 실패: {str(e)}")
    
    def get_cross_department_comparison(self) -> Dict[str, Any]:
        """학과간 비교 분석"""
        try:
            departments = [dept.value for dept in Department]
            comparison_data = {}
            
            for dept in departments:
                try:
                    dept_analytics = self.get_department_performance_analytics(dept)
                    comparison_data[dept] = {
                        "average_score": dept_analytics["performance_stats"]["average_score"],
                        "completion_rate": dept_analytics["basic_stats"]["completion_rate"],
                        "total_students": dept_analytics["basic_stats"]["total_students"],
                        "total_sessions": dept_analytics["basic_stats"]["total_sessions"]
                    }
                except:
                    # 데이터가 없는 학과는 기본값
                    comparison_data[dept] = {
                        "average_score": 0,
                        "completion_rate": 0,
                        "total_students": 0,
                        "total_sessions": 0
                    }
            
            # 순위 계산
            dept_rankings = {
                "by_average_score": sorted(
                    comparison_data.items(),
                    key=lambda x: x[1]["average_score"],
                    reverse=True
                ),
                "by_completion_rate": sorted(
                    comparison_data.items(),
                    key=lambda x: x[1]["completion_rate"],
                    reverse=True
                )
            }
            
            return {
                "comparison_data": comparison_data,
                "rankings": dept_rankings,
                "overall_stats": {
                    "total_departments": len([d for d in comparison_data.values() if d["total_students"] > 0]),
                    "total_students": sum([d["total_students"] for d in comparison_data.values()]),
                    "total_sessions": sum([d["total_sessions"] for d in comparison_data.values()]),
                    "overall_average": sum([d["average_score"] for d in comparison_data.values()]) / len(comparison_data)
                },
                "generated_at": datetime.now().isoformat()
            }
            
        except Exception as e:
            raise Exception(f"학과간 비교 분석 실패: {str(e)}")
    
    # 내부 유틸리티 메서드들
    def _get_user_department(self, user: User) -> str:
        """사용자 학과 정보 추출"""
        if user.profile_info and 'department' in user.profile_info:
            return user.profile_info['department']
        return "미분류"
    
    def _get_applicable_subjects(self, department: str) -> List[str]:
        """학과별 적용 가능한 과목 목록"""
        subject_mapping = {
            "컴퓨터공학과": [
                "computer_science", "software_engineering", "database", 
                "algorithm", "data_structure", "programming", "network"
            ],
            "소프트웨어융합과": [
                "software_engineering", "web_development", "mobile_development",
                "ai_machine_learning", "database", "programming"
            ],
            "물리치료학과": [
                "physical_therapy", "clinical_pathology"
            ],
            "간호학과": [
                "nursing", "medical_laboratory"
            ],
            "경영학과": [
                "business_administration", "economics", "statistics"
            ]
        }
        
        return subject_mapping.get(department, ["general"])
    
    def _build_test_info(self, test: DiagnosisTest, user: User) -> Dict[str, Any]:
        """테스트 정보 구성"""
        # 사용자의 테스트 이력 확인
        user_sessions = self.db.query(DiagnosisSession).filter(
            and_(
                DiagnosisSession.user_id == user.id,
                DiagnosisSession.test_id == test.id
            )
        ).all()
        
        completed_sessions = [s for s in user_sessions if s.status == "completed"]
        in_progress_session = next((s for s in user_sessions if s.status == "in_progress"), None)
        
        # 최고 점수
        best_score = max([s.percentage_score for s in completed_sessions if s.percentage_score]) if completed_sessions else None
        
        # 시도 횟수
        attempt_count = len(user_sessions)
        max_attempts = test.test_config.get("max_attempts", 3) if test.test_config else 3
        
        return {
            "id": test.id,
            "title": test.title,
            "description": test.description,
            "department": test.department,
            "subject_area": test.subject_area,
            "total_questions": test.total_questions,
            "time_limit_minutes": test.time_limit_minutes,
            "difficulty_distribution": test.test_metadata.get("difficulty_distribution") if test.test_metadata else None,
            "learning_objectives": test.test_metadata.get("learning_objectives") if test.test_metadata else [],
            "user_progress": {
                "completed": len(completed_sessions) > 0,
                "in_progress": in_progress_session is not None,
                "attempt_count": attempt_count,
                "max_attempts": max_attempts,
                "can_attempt": attempt_count < max_attempts,
                "best_score": best_score,
                "last_attempt": user_sessions[-1].created_at.isoformat() if user_sessions else None
            },
            "is_recommended": self._is_test_recommended_for_user(test, user),
            "estimated_difficulty": self._estimate_test_difficulty_for_user(test, user)
        }
    
    def _build_basic_test_info(self, test: DiagnosisTest) -> Dict[str, Any]:
        """기본 테스트 정보 구성"""
        return {
            "id": test.id,
            "title": test.title,
            "description": test.description,
            "department": test.department,
            "subject_area": test.subject_area,
            "total_questions": test.total_questions,
            "time_limit_minutes": test.time_limit_minutes,
            "created_at": test.created_at.isoformat(),
            "status": test.status
        }
    
    def _get_user_diagnosis_history(self, user: User) -> Optional[StudentDiagnosisHistory]:
        """사용자 진단 이력 조회"""
        return self.db.query(StudentDiagnosisHistory).filter(
            StudentDiagnosisHistory.user_id == user.id
        ).first()
    
    def _get_incomplete_tests(self, user: User) -> List[DiagnosisTest]:
        """미완료 테스트 목록"""
        incomplete_sessions = self.db.query(DiagnosisSession).filter(
            and_(
                DiagnosisSession.user_id == user.id,
                DiagnosisSession.status == "in_progress"
            )
        ).all()
        
        test_ids = [s.test_id for s in incomplete_sessions]
        return self.db.query(DiagnosisTest).filter(
            DiagnosisTest.id.in_(test_ids)
        ).all() if test_ids else []
    
    def _get_essential_tests_for_department(self, department: str) -> List[DiagnosisTest]:
        """학과별 필수 테스트"""
        return self.db.query(DiagnosisTest).filter(
            and_(
                DiagnosisTest.department == department,
                DiagnosisTest.test_metadata['essential'].astext == 'true',  # 필수 테스트 마킹
                DiagnosisTest.status == "active"
            )
        ).all()
    
    def _user_completed_test(self, user: User, test: DiagnosisTest) -> bool:
        """사용자가 테스트를 완료했는지 확인"""
        completed_sessions = self.db.query(DiagnosisSession).filter(
            and_(
                DiagnosisSession.user_id == user.id,
                DiagnosisSession.test_id == test.id,
                DiagnosisSession.status == "completed"
            )
        ).count()
        
        return completed_sessions > 0
    
    def _get_improvement_tests(self, user: User, history: Optional[StudentDiagnosisHistory]) -> List[DiagnosisTest]:
        """실력 향상 추천 테스트"""
        if not history or not history.recommendations:
            return []
        
        # 추천 사항에서 제안된 과목 영역
        recommended_subjects = history.recommendations.get("learning_path", [])
        
        return self.db.query(DiagnosisTest).filter(
            and_(
                DiagnosisTest.subject_area.in_(recommended_subjects),
                DiagnosisTest.status == "active",
                DiagnosisTest.test_metadata['difficulty_level'].astext.in_(["medium", "hard"])
            )
        ).limit(3).all()
    
    def _get_challenge_tests(self, user: User, history: Optional[StudentDiagnosisHistory]) -> List[DiagnosisTest]:
        """도전 과제 테스트"""
        user_department = self._get_user_department(user)
        
        return self.db.query(DiagnosisTest).filter(
            and_(
                DiagnosisTest.department == user_department,
                DiagnosisTest.test_metadata['difficulty_level'].astext == "hard",
                DiagnosisTest.status == "active"
            )
        ).limit(2).all()
    
    def _deduplicate_and_sort(self, recommendations: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """중복 제거 및 우선순위 정렬"""
        seen_ids = set()
        unique_recommendations = []
        
        # 우선순위별로 정렬
        priority_order = {"high": 1, "medium": 2, "low": 3}
        recommendations.sort(key=lambda x: priority_order.get(x.get("priority", "low"), 3))
        
        for rec in recommendations:
            if rec["id"] not in seen_ids:
                seen_ids.add(rec["id"])
                unique_recommendations.append(rec)
        
        return unique_recommendations
    
    def _validate_test_access(self, user: User, test_id: int) -> DiagnosisTest:
        """테스트 접근 권한 검증"""
        test = self.db.query(DiagnosisTest).filter(
            DiagnosisTest.id == test_id
        ).first()
        
        if not test:
            raise Exception("테스트를 찾을 수 없습니다.")
        
        if test.status != "active" or not test.is_published:
            raise Exception("비활성화된 테스트입니다.")
        
        # 학과별 접근 권한 확인
        user_department = self._get_user_department(user)
        applicable_subjects = self._get_applicable_subjects(user_department)
        
        if (test.department != user_department and 
            test.department != "전체학과" and 
            test.subject_area not in applicable_subjects):
            raise Exception("접근 권한이 없는 테스트입니다.")
        
        # 만료일 확인
        if test.expire_date and test.expire_date < datetime.now():
            raise Exception("만료된 테스트입니다.")
        
        return test
    
    def _generate_session_token(self, user_id: int, test_id: int) -> str:
        """세션 토큰 생성"""
        import uuid
        return f"DIAG_{user_id}_{test_id}_{datetime.now().strftime('%Y%m%d%H%M%S')}_{str(uuid.uuid4())[:8]}"
    
    def _get_next_attempt_number(self, user_id: int, test_id: int) -> int:
        """다음 시도 번호"""
        max_attempt = self.db.query(func.max(DiagnosisSession.attempt_number)).filter(
            and_(
                DiagnosisSession.user_id == user_id,
                DiagnosisSession.test_id == test_id
            )
        ).scalar()
        
        return (max_attempt or 0) + 1
    
    def _estimate_user_level(self, user: User) -> str:
        """사용자 수준 추정"""
        # 간단한 수준 추정 로직
        completed_sessions = self.db.query(DiagnosisSession).filter(
            and_(
                DiagnosisSession.user_id == user.id,
                DiagnosisSession.status == "completed"
            )
        ).all()
        
        if not completed_sessions:
            return "beginner"
        
        avg_score = sum([s.percentage_score for s in completed_sessions if s.percentage_score]) / len(completed_sessions)
        
        if avg_score >= 85:
            return "advanced"
        elif avg_score >= 70:
            return "intermediate"
        else:
            return "beginner"
    
    def _build_session_info(self, session: DiagnosisSession) -> Dict[str, Any]:
        """세션 정보 구성"""
        return {
            "session_id": session.id,
            "session_token": session.session_token,
            "test_id": session.test_id,
            "test_title": session.test.title if session.test else None,
            "status": session.status,
            "attempt_number": session.attempt_number,
            "expires_at": session.expires_at.isoformat() if session.expires_at else None,
            "time_limit_minutes": session.test.time_limit_minutes if session.test else 60,
            "total_questions": session.test.total_questions if session.test else 0,
            "created_at": session.created_at.isoformat()
        }
    
    def _is_test_recommended_for_user(self, test: DiagnosisTest, user: User) -> bool:
        """테스트가 사용자에게 추천되는지 확인"""
        # 간단한 추천 로직
        user_department = self._get_user_department(user)
        
        # 같은 학과 테스트는 추천
        if test.department == user_department:
            return True
        
        # 사용자가 아직 시도하지 않은 테스트는 추천
        attempted = self.db.query(DiagnosisSession).filter(
            and_(
                DiagnosisSession.user_id == user.id,
                DiagnosisSession.test_id == test.id
            )
        ).count()
        
        return attempted == 0
    
    def _estimate_test_difficulty_for_user(self, test: DiagnosisTest, user: User) -> str:
        """사용자 대비 테스트 난이도 추정"""
        user_level = self._estimate_user_level(user)
        test_difficulty = test.test_metadata.get("difficulty_level", "medium") if test.test_metadata else "medium"
        
        # 사용자 수준과 테스트 난이도 비교
        level_mapping = {"beginner": 1, "intermediate": 2, "advanced": 3}
        difficulty_mapping = {"easy": 1, "medium": 2, "hard": 3}
        
        user_score = level_mapping.get(user_level, 2)
        test_score = difficulty_mapping.get(test_difficulty, 2)
        
        if test_score < user_score:
            return "쉬움"
        elif test_score > user_score:
            return "어려움"
        else:
            return "적정"
    
    def _analyze_subject_performance(self, user_ids: List[int]) -> Dict[str, Any]:
        """과목별 성과 분석"""
        if not user_ids:
            return {}
        
        # 과목별 세션 통계
        sessions = self.db.query(DiagnosisSession).join(DiagnosisTest).filter(
            DiagnosisSession.user_id.in_(user_ids)
        ).all()
        
        subject_stats = {}
        for session in sessions:
            if not session.test:
                continue
                
            subject = session.test.subject_area
            if subject not in subject_stats:
                subject_stats[subject] = {
                    "total_sessions": 0,
                    "completed_sessions": 0,
                    "scores": []
                }
            
            subject_stats[subject]["total_sessions"] += 1
            if session.status == "completed":
                subject_stats[subject]["completed_sessions"] += 1
                if session.percentage_score:
                    subject_stats[subject]["scores"].append(session.percentage_score)
        
        # 평균 점수 계산
        for subject, stats in subject_stats.items():
            if stats["scores"]:
                stats["average_score"] = sum(stats["scores"]) / len(stats["scores"])
            else:
                stats["average_score"] = 0
            del stats["scores"]  # 개별 점수는 제거
        
        return subject_stats
    
    def _analyze_time_trends(self, user_ids: List[int]) -> Dict[str, Any]:
        """시간별 추이 분석"""
        if not user_ids:
            return {}
        
        # 최근 30일간의 데이터
        start_date = datetime.now() - timedelta(days=30)
        
        sessions = self.db.query(DiagnosisSession).filter(
            and_(
                DiagnosisSession.user_id.in_(user_ids),
                DiagnosisSession.created_at >= start_date
            )
        ).order_by(DiagnosisSession.created_at).all()
        
        # 일별 통계
        daily_stats = {}
        for session in sessions:
            date_key = session.created_at.date().isoformat()
            if date_key not in daily_stats:
                daily_stats[date_key] = {
                    "sessions": 0,
                    "completed": 0,
                    "scores": []
                }
            
            daily_stats[date_key]["sessions"] += 1
            if session.status == "completed":
                daily_stats[date_key]["completed"] += 1
                if session.percentage_score:
                    daily_stats[date_key]["scores"].append(session.percentage_score)
        
        # 평균 점수 계산
        for date, stats in daily_stats.items():
            if stats["scores"]:
                stats["average_score"] = sum(stats["scores"]) / len(stats["scores"])
            else:
                stats["average_score"] = 0
            del stats["scores"]
        
        return daily_stats

# 편의 함수들
def get_user_available_tests(db: Session, user: User) -> List[Dict[str, Any]]:
    """사용자 사용 가능한 테스트 조회"""
    service = DepartmentDiagnosisService(db)
    return service.get_available_tests_for_user(user)

def get_user_recommended_tests(db: Session, user: User) -> List[Dict[str, Any]]:
    """사용자 맞춤 추천 테스트"""
    service = DepartmentDiagnosisService(db)
    return service.get_recommended_tests_for_user(user)

def start_user_diagnosis_session(db: Session, user: User, test_id: int) -> Dict[str, Any]:
    """사용자 진단 세션 시작"""
    service = DepartmentDiagnosisService(db)
    return service.start_diagnosis_session(user, test_id)

async def get_available_tests_by_department(self, department: Department) -> List[Dict]:
    """학과별 사용 가능한 진단테스트 목록 조회"""
    try:
        # 학과에 해당하는 진단 과목들 찾기
        department_subjects = []
        for category, subjects in DEPARTMENT_CATEGORIES.items():
            for subject in subjects:
                if self._is_department_match(department, subject):
                    department_subjects.append(subject)
        
        # 각 과목별 테스트 정보 수집
        available_tests = []
        for subject in department_subjects:
            try:
                test_info = self.test_loader.get_test_info(subject)
                test_stats = self.test_loader.get_statistics(subject)
                
                available_tests.append({
                    "subject": subject.value,
                    "title": test_info.get("title", f"{subject.value} 진단테스트"),
                    "description": test_info.get("description", ""),
                    "total_questions": test_info.get("total_questions", 0),
                    "time_limit": test_info.get("time_limit", 60),
                    "difficulty_distribution": test_stats.get("difficulty_distribution", {}),
                    "available": True
                })
            except (FileNotFoundError, ValueError) as e:
                logger.warning(f"Test file not available for {subject.value}: {e}")
                available_tests.append({
                    "subject": subject.value,
                    "title": f"{subject.value} 진단테스트",
                    "description": "준비중입니다.",
                    "total_questions": 0,
                    "time_limit": 60,
                    "difficulty_distribution": {},
                    "available": False
                })
        
        return available_tests
        
    except Exception as e:
        logger.error(f"Error getting available tests for department {department}: {e}")
        raise

def _is_department_match(self, department: Department, subject: DiagnosisSubject) -> bool:
    """학과와 진단 과목이 매치되는지 확인"""
    # 컴퓨터 관련 학과 매핑
    if department in [Department.COMPUTER_SCIENCE, Department.SOFTWARE_ENGINEERING, 
                     Department.INFORMATION_TECHNOLOGY]:
        return subject in DEPARTMENT_CATEGORIES.get("computer_science", [])
    
    # 의료 관련 학과 매핑
    elif department in [Department.MEDICINE, Department.NURSING, Department.PHYSICAL_THERAPY]:
        return subject in DEPARTMENT_CATEGORIES.get("medical", [])
    
    # 공학 관련 학과 매핑
    elif department in [Department.MECHANICAL_ENGINEERING, Department.ELECTRICAL_ENGINEERING]:
        return subject in DEPARTMENT_CATEGORIES.get("engineering", [])
    
    # 기타 학과들
    elif department == Department.BUSINESS_ADMINISTRATION:
        return subject in DEPARTMENT_CATEGORIES.get("business", [])
    elif department == Department.LAW:
        return subject in DEPARTMENT_CATEGORIES.get("law", [])
    elif department == Department.EDUCATION:
        return subject in DEPARTMENT_CATEGORIES.get("education", [])
    
    return False

async def create_diagnosis_test_from_file(self, subject: DiagnosisSubject, user_department: Department) -> DiagnosisTest:
    """JSON 파일로부터 진단테스트 생성"""
    try:
        # JSON 데이터 로드
        test_data = self.test_loader.load_test_data(subject)
        test_info = test_data["test_info"]
        scoring_criteria = test_data["scoring_criteria"]
        questions_data = test_data["questions"]
        
        # 진단테스트 생성
        diagnosis_test = DiagnosisTest(
            title=test_info["title"],
            description=test_info["description"],
            subject=subject,
            target_department=user_department,
            configuration={
                "total_questions": test_info["total_questions"],
                "time_limit_minutes": test_info["time_limit"],
                "scoring_criteria": scoring_criteria,
                "difficulty_weights": scoring_criteria.get("difficulty_weights", {}),
                "pass_score": scoring_criteria.get("level_classification", {}).get("중급", {}).get("min_score", 60)
            },
            is_active=True
        )
        
        self.db.add(diagnosis_test)
        self.db.flush()
        
        # 문제들 생성
        for question_data in questions_data:
            diagnosis_question = DiagnosisQuestion(
                test_id=diagnosis_test.id,
                question_number=question_data["question_number"],
                content=question_data["content"],
                question_type=QuestionType.MULTIPLE_CHOICE,
                options=question_data["options"],
                correct_answer=question_data["correct_answer"],
                classification={
                    "subject": question_data.get("subject", subject.value),
                    "area": question_data.get("area_name", ""),
                    "difficulty": question_data.get("difficulty_level", "보통"),
                    "domain": question_data.get("domain", "")
                },
                question_metadata={
                    "difficulty_score": question_data.get("difficulty", 5),
                    "discrimination_power": question_data.get("discrimination_power", 7),
                    "diagnostic_suitability": question_data.get("diagnostic_suitability", 8),
                    "points": question_data.get("points", 3.3),
                    "year": question_data.get("year", 2024),
                    "original_question_number": question_data.get("original_question_number", 0)
                },
                source_info={
                    "source_file": question_data.get("source_info", {}).get("file", ""),
                    "unique_id": question_data.get("source_info", {}).get("unique_id", question_data["question_id"])
                },
                is_active=True
            )
            
            self.db.add(diagnosis_question)
        
        self.db.commit()
        return diagnosis_test
        
    except Exception as e:
        self.db.rollback()
        logger.error(f"Error creating diagnosis test from file for {subject}: {e}")
        raise

async def get_test_validation_report(self) -> Dict[str, Any]:
    """진단테스트 파일 유효성 검사 보고서"""
    try:
        validation_results = self.test_loader.validate_test_files()
        
        # 추가 통계 정보
        total_subjects = len(list(DiagnosisSubject))
        valid_count = len(validation_results["valid_files"])
        invalid_count = len(validation_results["invalid_files"])
        missing_count = len(validation_results["missing_files"])
        error_count = len(validation_results["errors"])
        
        validation_results.update({
            "summary": {
                "total_subjects": total_subjects,
                "valid_files": valid_count,
                "invalid_files": invalid_count,
                "missing_files": missing_count,
                "errors": error_count,
                "completion_rate": round((valid_count / total_subjects) * 100, 2)
            }
        })
        
        return validation_results
        
    except Exception as e:
        logger.error(f"Error getting test validation report: {e}")
        raise 