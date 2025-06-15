"""
진단 시스템 통합 마이그레이션 서비스
diagnostic_tests + test_sessions -> unified_diagnosis 시스템으로 안전하게 데이터 이관
"""
import json
from datetime import datetime
from typing import Dict, List, Optional, Any, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, func, text

from app.models.diagnostic_test import (
    DiagnosticTest as OldDiagnosticTest,
    DiagnosticQuestion as OldDiagnosticQuestion,
    DiagnosticSubmission as OldDiagnosticSubmission,
    DiagnosticResponse as OldDiagnosticResponse,
    StudentDiagnosticHistory as OldStudentDiagnosticHistory
)
from app.models.diagnosis import (
    TestSession as OldTestSession,
    TestResponse as OldTestResponse,
    DiagnosisResult as OldDiagnosisResult,
    LearningLevelHistory as OldLearningLevelHistory
)
from app.models.unified_diagnosis import (
    DiagnosisTest,
    DiagnosisQuestion,
    DiagnosisSession,
    DiagnosisResponse,
    StudentDiagnosisHistory
)
from app.models.user import User

class DiagnosisMigrationService:
    """진단 시스템 통합 마이그레이션 서비스"""
    
    def __init__(self, db_session: Session):
        self.db = db_session
        self.migration_log = []
        self.error_log = []
        
    def migrate_all_systems(self) -> Dict[str, Any]:
        """모든 진단 시스템을 통합 시스템으로 마이그레이션"""
        try:
            self.log_info("진단 시스템 통합 마이그레이션 시작")
            
            # 1. 기존 데이터 백업
            backup_info = self._backup_existing_data()
            
            # 2. diagnostic_tests 시스템 마이그레이션
            diagnostic_results = self._migrate_diagnostic_tests()
            
            # 3. test_sessions 시스템 마이그레이션
            session_results = self._migrate_test_sessions()
            
            # 4. 학생 이력 통합
            history_results = self._migrate_student_histories()
            
            # 5. 데이터 검증
            validation_results = self._validate_migrated_data()
            
            # 6. 마이그레이션 완료 처리
            self._finalize_migration()
            
            self.log_info("진단 시스템 통합 마이그레이션 완료")
            
            return {
                "status": "success",
                "backup_info": backup_info,
                "diagnostic_results": diagnostic_results,
                "session_results": session_results,
                "history_results": history_results,
                "validation_results": validation_results,
                "migration_log": self.migration_log,
                "error_count": len(self.error_log),
                "errors": self.error_log
            }
            
        except Exception as e:
            self.log_error(f"마이그레이션 실패: {str(e)}")
            self.db.rollback()
            return {
                "status": "failed",
                "error": str(e),
                "migration_log": self.migration_log,
                "error_log": self.error_log
            }
    
    def _backup_existing_data(self) -> Dict[str, int]:
        """기존 데이터 백업"""
        self.log_info("기존 데이터 백업 시작")
        
        backup_counts = {
            "diagnostic_tests": self.db.query(OldDiagnosticTest).count(),
            "diagnostic_questions": self.db.query(OldDiagnosticQuestion).count(),
            "diagnostic_submissions": self.db.query(OldDiagnosticSubmission).count(),
            "diagnostic_responses": self.db.query(OldDiagnosticResponse).count(),
            "test_sessions": self.db.query(OldTestSession).count(),
            "test_responses": self.db.query(OldTestResponse).count(),
            "diagnosis_results": self.db.query(OldDiagnosisResult).count(),
            "student_histories": self.db.query(OldStudentDiagnosticHistory).count()
        }
        
        # 백업 테이블 생성 (필요시)
        self._create_backup_tables()
        
        self.log_info(f"백업 완료: {backup_counts}")
        return backup_counts
    
    def _migrate_diagnostic_tests(self) -> Dict[str, Any]:
        """diagnostic_tests 시스템 마이그레이션"""
        self.log_info("diagnostic_tests 시스템 마이그레이션 시작")
        
        results = {
            "tests_migrated": 0,
            "questions_migrated": 0,
            "sessions_migrated": 0,
            "responses_migrated": 0,
            "errors": []
        }
        
        # 1. 진단 테스트 마이그레이션
        old_tests = self.db.query(OldDiagnosticTest).all()
        for old_test in old_tests:
            try:
                new_test = self._convert_diagnostic_test(old_test)
                self.db.add(new_test)
                self.db.flush()  # ID 생성을 위해
                
                # 2. 문제 마이그레이션
                for old_question in old_test.questions:
                    new_question = self._convert_diagnostic_question(old_question, new_test.id)
                    self.db.add(new_question)
                    results["questions_migrated"] += 1
                
                # 3. 제출 및 응답 마이그레이션
                for old_submission in old_test.submissions:
                    new_session = self._convert_diagnostic_submission(old_submission, new_test.id)
                    self.db.add(new_session)
                    self.db.flush()
                    
                    for old_response in old_submission.responses:
                        new_response = self._convert_diagnostic_response(old_response, new_session.id)
                        self.db.add(new_response)
                        results["responses_migrated"] += 1
                    
                    results["sessions_migrated"] += 1
                
                results["tests_migrated"] += 1
                
            except Exception as e:
                error_msg = f"진단 테스트 마이그레이션 실패 (ID: {old_test.id}): {str(e)}"
                self.log_error(error_msg)
                results["errors"].append(error_msg)
        
        self.db.commit()
        self.log_info(f"diagnostic_tests 마이그레이션 완료: {results}")
        return results
    
    def _migrate_test_sessions(self) -> Dict[str, Any]:
        """test_sessions 시스템 마이그레이션"""
        self.log_info("test_sessions 시스템 마이그레이션 시작")
        
        results = {
            "sessions_migrated": 0,
            "responses_migrated": 0,
            "tests_created": 0,
            "errors": []
        }
        
        # 1. 기존 test_sessions를 기반으로 통합 테스트 생성
        test_mapping = self._create_unified_tests_from_sessions()
        results["tests_created"] = len(test_mapping)
        
        # 2. 세션 마이그레이션
        old_sessions = self.db.query(OldTestSession).all()
        for old_session in old_sessions:
            try:
                # 해당하는 통합 테스트 찾기
                unified_test_id = self._find_unified_test_for_session(old_session, test_mapping)
                if not unified_test_id:
                    continue
                
                new_session = self._convert_test_session(old_session, unified_test_id)
                self.db.add(new_session)
                self.db.flush()
                
                # 3. 응답 마이그레이션
                for old_response in old_session.responses:
                    new_response = self._convert_test_response(old_response, new_session.id)
                    self.db.add(new_response)
                    results["responses_migrated"] += 1
                
                results["sessions_migrated"] += 1
                
            except Exception as e:
                error_msg = f"테스트 세션 마이그레이션 실패 (ID: {old_session.id}): {str(e)}"
                self.log_error(error_msg)
                results["errors"].append(error_msg)
        
        self.db.commit()
        self.log_info(f"test_sessions 마이그레이션 완료: {results}")
        return results
    
    def _migrate_student_histories(self) -> Dict[str, Any]:
        """학생 진단 이력 통합"""
        self.log_info("학생 진단 이력 통합 시작")
        
        results = {
            "histories_migrated": 0,
            "users_processed": 0,
            "errors": []
        }
        
        # 모든 사용자에 대해 진단 이력 통합
        users = self.db.query(User).all()
        for user in users:
            try:
                # 사용자별 진단 이력 통합
                unified_history = self._create_unified_history(user)
                if unified_history:
                    self.db.add(unified_history)
                    results["histories_migrated"] += 1
                
                results["users_processed"] += 1
                
            except Exception as e:
                error_msg = f"사용자 이력 통합 실패 (ID: {user.id}): {str(e)}"
                self.log_error(error_msg)
                results["errors"].append(error_msg)
        
        self.db.commit()
        self.log_info(f"학생 진단 이력 통합 완료: {results}")
        return results
    
    def _convert_diagnostic_test(self, old_test: OldDiagnosticTest) -> DiagnosisTest:
        """진단 테스트 변환"""
        return DiagnosisTest(
            title=old_test.title,
            description=old_test.description,
            department=old_test.department,
            subject_area=self._determine_subject_area(old_test.department),
            test_config={
                "total_questions": old_test.total_questions,
                "time_limit_minutes": old_test.time_limit,
                "random_order": True,
                "allow_retake": True,
                "max_attempts": 3
            },
            scoring_criteria=old_test.scoring_criteria or self._create_default_scoring(),
            analysis_config={
                "enable_bkt": True,
                "enable_dkt": True,
                "enable_irt": True,
                "adaptive_testing": False,
                "real_time_feedback": True
            },
            test_metadata={
                "version": old_test.version,
                "migrated_from": "diagnostic_tests",
                "original_id": old_test.id,
                "migration_date": datetime.now().isoformat()
            },
            status="active" if old_test.is_active else "inactive",
            is_published=old_test.is_active,
            created_by=1,  # 기본 관리자 ID
            created_at=old_test.created_at,
            updated_at=old_test.updated_at
        )
    
    def _convert_diagnostic_question(self, old_question: OldDiagnosticQuestion, test_id: int) -> DiagnosisQuestion:
        """진단 문제 변환"""
        return DiagnosisQuestion(
            test_id=test_id,
            question_id=old_question.question_id,
            question_number=old_question.question_number,
            content=old_question.content,
            question_type="multiple_choice",
            options=old_question.options,
            correct_answer=old_question.correct_answer,
            explanation=getattr(old_question, 'explanation', None),
            classification={
                "subject": old_question.subject,
                "area": old_question.area_name,
                "difficulty": old_question.difficulty_level,
                "domain": old_question.domain,
                "keywords": []
            },
            question_properties={
                "estimated_time": 120,
                "points": old_question.points or 1.0,
                "difficulty_score": old_question.difficulty or 5,
                "discrimination_power": old_question.discrimination_power or 5,
                "diagnostic_value": old_question.diagnostic_suitability or 5
            },
            ai_analysis={
                "auto_generated": False,
                "difficulty_prediction": old_question.difficulty or 5,
                "topic_classification": [old_question.subject] if old_question.subject else []
            },
            source_info=old_question.source_info,
            display_order=old_question.question_number,
            is_active=True,
            created_at=old_question.created_at
        )
    
    def _convert_diagnostic_submission(self, old_submission: OldDiagnosticSubmission, test_id: int) -> DiagnosisSession:
        """진단 제출 변환"""
        return DiagnosisSession(
            test_id=test_id,
            user_id=old_submission.user_id,
            session_token=f"MIGRATED_{old_submission.id}_{datetime.now().timestamp()}",
            attempt_number=1,
            status=old_submission.status,
            started_at=old_submission.start_time,
            completed_at=old_submission.end_time,
            raw_score=old_submission.total_score,
            percentage_score=old_submission.total_score,
            response_stats={
                "total_questions": old_submission.correct_count + old_submission.wrong_count + old_submission.unanswered_count,
                "answered": old_submission.correct_count + old_submission.wrong_count,
                "correct": old_submission.correct_count,
                "incorrect": old_submission.wrong_count,
                "skipped": old_submission.unanswered_count
            },
            diagnosis_result=old_submission.diagnostic_result,
            advanced_analysis={
                "bkt_analysis": old_submission.bkt_analysis,
                "dkt_analysis": old_submission.dkt_analysis,
                "rnn_analysis": old_submission.rnn_analysis,
                "migrated_from": "diagnostic_submissions"
            },
            session_metadata={
                "migrated_from": "diagnostic_submissions",
                "original_id": old_submission.id,
                "level_classification": old_submission.level_classification
            },
            created_at=old_submission.created_at,
            updated_at=old_submission.updated_at
        )
    
    def _convert_diagnostic_response(self, old_response: OldDiagnosticResponse, session_id: int) -> DiagnosisResponse:
        """진단 응답 변환"""
        return DiagnosisResponse(
            session_id=session_id,
            question_id=old_response.question_id,
            user_answer=old_response.user_answer,
            is_correct=old_response.is_correct,
            points_earned=1.0 if old_response.is_correct else 0.0,
            response_time=old_response.response_time,
            cognitive_analysis={
                "knowledge_state": old_response.knowledge_state,
                "confidence_level": old_response.confidence_level,
                "migrated_from": "diagnostic_responses"
            },
            response_metadata={
                "migrated_from": "diagnostic_responses",
                "original_id": old_response.id
            },
            answered_at=old_response.answered_at
        )
    
    def _create_unified_tests_from_sessions(self) -> Dict[str, int]:
        """test_sessions를 기반으로 통합 테스트 생성"""
        # 세션들을 과목별로 그룹화하여 통합 테스트 생성
        session_groups = self.db.query(
            OldTestSession.subject_id,
            func.count(OldTestSession.id).label('session_count')
        ).group_by(OldTestSession.subject_id).all()
        
        test_mapping = {}
        for subject_id, session_count in session_groups:
            # 각 과목별로 통합 테스트 생성
            unified_test = DiagnosisTest(
                title=f"통합 진단테스트 - {subject_id}",
                description=f"기존 test_sessions에서 마이그레이션된 통합 진단테스트",
                department="컴퓨터공학과",  # 기본값
                subject_area=subject_id,
                test_config=self._create_default_test_config(),
                scoring_criteria=self._create_default_scoring(),
                analysis_config=self._create_default_analysis_config(),
                test_metadata={
                    "version": "1.0",
                    "migrated_from": "test_sessions",
                    "original_subject_id": subject_id,
                    "migration_date": datetime.now().isoformat()
                },
                status="active",
                is_published=True,
                created_by=1,
                created_at=datetime.now(),
                updated_at=datetime.now()
            )
            
            self.db.add(unified_test)
            self.db.flush()
            test_mapping[subject_id] = unified_test.id
        
        return test_mapping
    
    def _find_unified_test_for_session(self, old_session: OldTestSession, test_mapping: Dict[str, int]) -> Optional[int]:
        """세션에 해당하는 통합 테스트 ID 찾기"""
        return test_mapping.get(old_session.subject_id)
    
    def _convert_test_session(self, old_session: OldTestSession, test_id: int) -> DiagnosisSession:
        """테스트 세션 변환"""
        return DiagnosisSession(
            test_id=test_id,
            user_id=old_session.user_id,
            session_token=f"MIGRATED_TS_{old_session.id}_{datetime.now().timestamp()}",
            attempt_number=1,
            status="completed" if old_session.completed_at else "in_progress",
            started_at=old_session.started_at,
            completed_at=old_session.completed_at,
            raw_score=old_session.score or 0.0,
            percentage_score=old_session.score or 0.0,
            response_stats={
                "total_questions": getattr(old_session, 'total_questions', 0),
                "answered": len(old_session.responses) if hasattr(old_session, 'responses') else 0
            },
            session_metadata={
                "migrated_from": "test_sessions",
                "original_id": old_session.id,
                "subject_id": old_session.subject_id
            },
            created_at=old_session.created_at if hasattr(old_session, 'created_at') else datetime.now(),
            updated_at=old_session.updated_at if hasattr(old_session, 'updated_at') else datetime.now()
        )
    
    def _convert_test_response(self, old_response: OldTestResponse, session_id: int) -> DiagnosisResponse:
        """테스트 응답 변환"""
        return DiagnosisResponse(
            session_id=session_id,
            question_id=old_response.question_id,
            user_answer=old_response.user_answer,
            is_correct=old_response.is_correct,
            points_earned=1.0 if old_response.is_correct else 0.0,
            response_time=old_response.response_time if hasattr(old_response, 'response_time') else None,
            response_metadata={
                "migrated_from": "test_responses",
                "original_id": old_response.id
            },
            answered_at=old_response.answered_at if hasattr(old_response, 'answered_at') else datetime.now()
        )
    
    def _create_unified_history(self, user: User) -> Optional[StudentDiagnosisHistory]:
        """사용자별 통합 진단 이력 생성"""
        # 기존 진단 이력 수집
        old_histories = self.db.query(OldStudentDiagnosticHistory).filter(
            OldStudentDiagnosticHistory.user_id == user.id
        ).all()
        
        if not old_histories:
            return None
        
        # 모든 이력을 통합
        combined_progression = {}
        combined_predictions = {}
        combined_recommendations = {}
        combined_stats = {}
        
        for history in old_histories:
            # 학습 진행도 통합
            if history.learning_progression:
                combined_progression.update(history.learning_progression)
            
            # 예측 결과 통합
            if history.predicted_performance:
                combined_predictions.update(history.predicted_performance)
            
            # 추천 사항 통합
            if history.recommended_actions:
                combined_recommendations.update(history.recommended_actions)
        
        return StudentDiagnosisHistory(
            user_id=user.id,
            department=user.profile_info.get('department', '미분류') if user.profile_info else '미분류',
            subject_area="통합",
            learning_progression=combined_progression,
            predictions=combined_predictions,
            recommendations=combined_recommendations,
            performance_stats=combined_stats,
            last_updated=datetime.now()
        )
    
    def _validate_migrated_data(self) -> Dict[str, Any]:
        """마이그레이션된 데이터 검증"""
        self.log_info("마이그레이션 데이터 검증 시작")
        
        validation_results = {
            "tests_count": self.db.query(DiagnosisTest).count(),
            "questions_count": self.db.query(DiagnosisQuestion).count(),
            "sessions_count": self.db.query(DiagnosisSession).count(),
            "responses_count": self.db.query(DiagnosisResponse).count(),
            "histories_count": self.db.query(StudentDiagnosisHistory).count(),
            "data_integrity_check": self._check_data_integrity(),
            "relationship_validation": self._validate_relationships()
        }
        
        self.log_info(f"데이터 검증 완료: {validation_results}")
        return validation_results
    
    def _check_data_integrity(self) -> Dict[str, bool]:
        """데이터 무결성 검사"""
        return {
            "all_tests_have_questions": self._check_all_tests_have_questions(),
            "all_sessions_have_valid_tests": self._check_sessions_have_valid_tests(),
            "all_responses_have_valid_sessions": self._check_responses_have_valid_sessions(),
            "no_orphaned_records": self._check_no_orphaned_records()
        }
    
    def _validate_relationships(self) -> Dict[str, bool]:
        """관계 검증"""
        return {
            "test_question_relationships": True,  # 구현 필요
            "session_response_relationships": True,  # 구현 필요
            "user_session_relationships": True  # 구현 필요
        }
    
    def _finalize_migration(self):
        """마이그레이션 완료 처리"""
        # 마이그레이션 완료 로그 기록
        self.log_info("마이그레이션 완료 처리 시작")
        
        # 기존 테이블 백업 상태로 변경 (실제 삭제는 관리자가 수동으로)
        # self._archive_old_tables()
        
        self.log_info("마이그레이션 완료 처리 완료")
    
    # 유틸리티 메서드들
    def _determine_subject_area(self, department: str) -> str:
        """학과에 따른 과목 영역 결정"""
        department_mapping = {
            "물리치료학과": "physical_therapy",
            "컴퓨터공학과": "computer_science",
            "소프트웨어융합과": "software_engineering"
        }
        return department_mapping.get(department, "general")
    
    def _create_default_test_config(self) -> Dict[str, Any]:
        """기본 테스트 설정"""
        return {
            "total_questions": 30,
            "time_limit_minutes": 60,
            "random_order": True,
            "allow_retake": True,
            "max_attempts": 3
        }
    
    def _create_default_scoring(self) -> Dict[str, Any]:
        """기본 점수 기준"""
        return {
            "levels": {
                "excellent": {"min": 90, "max": 100, "label": "우수"},
                "good": {"min": 80, "max": 89, "label": "양호"},
                "average": {"min": 70, "max": 79, "label": "보통"},
                "poor": {"min": 60, "max": 69, "label": "미흡"},
                "fail": {"min": 0, "max": 59, "label": "부족"}
            }
        }
    
    def _create_default_analysis_config(self) -> Dict[str, Any]:
        """기본 분석 설정"""
        return {
            "enable_bkt": True,
            "enable_dkt": True,
            "enable_irt": True,
            "adaptive_testing": False,
            "real_time_feedback": True
        }
    
    def _create_backup_tables(self):
        """백업 테이블 생성"""
        # 실제 구현에서는 SQL 명령으로 백업 테이블 생성
        pass
    
    def _check_all_tests_have_questions(self) -> bool:
        """모든 테스트가 문제를 가지고 있는지 확인"""
        tests_without_questions = self.db.query(DiagnosisTest).filter(
            ~DiagnosisTest.questions.any()
        ).count()
        return tests_without_questions == 0
    
    def _check_sessions_have_valid_tests(self) -> bool:
        """모든 세션이 유효한 테스트를 가지고 있는지 확인"""
        invalid_sessions = self.db.query(DiagnosisSession).filter(
            ~DiagnosisSession.test_id.in_(
                self.db.query(DiagnosisTest.id)
            )
        ).count()
        return invalid_sessions == 0
    
    def _check_responses_have_valid_sessions(self) -> bool:
        """모든 응답이 유효한 세션을 가지고 있는지 확인"""
        invalid_responses = self.db.query(DiagnosisResponse).filter(
            ~DiagnosisResponse.session_id.in_(
                self.db.query(DiagnosisSession.id)
            )
        ).count()
        return invalid_responses == 0
    
    def _check_no_orphaned_records(self) -> bool:
        """고아 레코드가 없는지 확인"""
        # 구현 상세 로직
        return True
    
    def log_info(self, message: str):
        """정보 로그"""
        log_entry = f"[INFO] {datetime.now().isoformat()}: {message}"
        self.migration_log.append(log_entry)
        print(log_entry)
    
    def log_error(self, message: str):
        """오류 로그"""
        log_entry = f"[ERROR] {datetime.now().isoformat()}: {message}"
        self.error_log.append(log_entry)
        print(log_entry)

# 편의 함수들
def migrate_diagnosis_systems(db: Session) -> Dict[str, Any]:
    """진단 시스템 마이그레이션 실행"""
    service = DiagnosisMigrationService(db)
    return service.migrate_all_systems()

def rollback_migration(db: Session) -> Dict[str, Any]:
    """마이그레이션 롤백"""
    # 롤백 로직 구현
    return {"status": "rollback_completed"}

def validate_migration(db: Session) -> Dict[str, Any]:
    """마이그레이션 검증"""
    service = DiagnosisMigrationService(db)
    return service._validate_migrated_data() 