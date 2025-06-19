"""
진단테스트 진행 상황 및 단계별 분석 서비스
1차: 초기 진단 분석
2차~: 비교분석 및 학습추세 분석
"""
import logging
from typing import List, Dict, Any, Optional, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, func, desc, asc
from datetime import datetime, timedelta
import statistics
import json

from app.models.unified_diagnosis import DiagnosisSession, DiagnosisResponse, DiagnosisTest
from app.models.user import User

logger = logging.getLogger(__name__)

class DiagnosisProgressService:
    """진단테스트 진행 상황 및 단계별 분석 서비스"""
    
    def __init__(self, db: Session):
        self.db = db

    async def get_comprehensive_analysis(self, user_id: int, department: str) -> Dict[str, Any]:
        """사용자의 종합 진단 분석 (차수별 맞춤 분석)"""
        try:
            # 완료된 세션들 조회 (차수 순으로 정렬)
            completed_sessions = self.db.query(DiagnosisSession).join(
                DiagnosisTest, DiagnosisSession.test_id == DiagnosisTest.id
            ).filter(
                and_(
                    DiagnosisSession.user_id == user_id,
                    DiagnosisTest.department == department,
                    DiagnosisSession.status == "completed"
                )
            ).order_by(DiagnosisSession.completed_at).all()

            if not completed_sessions:
                return {
                    "analysis_type": "no_data",
                    "message": "완료된 진단테스트가 없습니다.",
                    "recommendations": ["첫 번째 진단테스트를 완료해주세요."]
                }

            # 완료된 차수 수에 따른 분석 타입 결정
            completed_count = len(completed_sessions)
            latest_session = completed_sessions[-1]

            if completed_count == 1:
                # 1차 완료: 초기 진단 분석
                return await self._generate_initial_diagnosis_analysis(
                    user_id, latest_session, department
                )
            else:
                # 2차 이상: 비교분석 및 학습추세 분석
                return await self._generate_comparative_trend_analysis(
                    user_id, completed_sessions, department
                )

        except Exception as e:
            logger.error(f"종합 진단 분석 실패: {str(e)}")
            raise Exception(f"진단 분석 생성 실패: {str(e)}")

    async def _generate_initial_diagnosis_analysis(
        self, 
        user_id: int, 
        session: DiagnosisSession, 
        department: str
    ) -> Dict[str, Any]:
        """1차 진단테스트 완료 후 초기 진단 분석"""
        
        # 응답 데이터 조회
        responses = self.db.query(DiagnosisResponse).filter(
            DiagnosisResponse.session_id == session.id
        ).all()

        # 기본 성과 지표
        total_questions = len(responses)
        correct_answers = sum(1 for r in responses if r.is_correct)
        accuracy_rate = correct_answers / total_questions if total_questions > 0 else 0
        
        # 영역별 분석
        domain_analysis = self._analyze_performance_by_domain(responses)
        
        # 난이도별 분석
        difficulty_analysis = self._analyze_performance_by_difficulty(responses)
        
        # 시간 분석
        time_analysis = self._analyze_response_times(responses)
        
        # 학습 상태 진단
        learning_state = self._diagnose_initial_learning_state(
            accuracy_rate, domain_analysis, difficulty_analysis, time_analysis
        )
        
        # 개인화된 학습 추천
        learning_recommendations = self._generate_initial_learning_recommendations(
            learning_state, domain_analysis, difficulty_analysis
        )
        
        # 다음 단계 가이드
        next_steps = self._generate_next_steps_guide(learning_state, department)

        return {
            "analysis_type": "initial_diagnosis",
            "round_number": 1,
            "completed_at": session.completed_at.isoformat(),
            "department": department,
            
            # 기본 성과
            "performance_summary": {
                "total_questions": total_questions,
                "correct_answers": correct_answers,
                "accuracy_rate": round(accuracy_rate * 100, 1),
                "score": round(session.percentage_score, 1),
                "time_spent_minutes": round(session.total_time_spent / 60, 1) if session.total_time_spent else 0,
                "performance_level": self._classify_performance_level(accuracy_rate)
            },
            
            # 영역별 분석
            "domain_analysis": domain_analysis,
            
            # 난이도별 분석  
            "difficulty_analysis": difficulty_analysis,
            
            # 시간 분석
            "time_analysis": time_analysis,
            
            # 학습 상태 진단
            "learning_diagnosis": learning_state,
            
            # 개인화된 추천
            "personalized_recommendations": learning_recommendations,
            
            # 다음 단계 가이드
            "next_steps": next_steps,
            
            # 시각화 데이터
            "visualizations": {
                "domain_radar": self._generate_domain_radar_data(domain_analysis),
                "difficulty_chart": self._generate_difficulty_chart_data(difficulty_analysis),
                "time_distribution": self._generate_time_distribution_data(responses)
            },
            
            "analysis_metadata": {
                "analysis_date": datetime.now().isoformat(),
                "analysis_version": "initial_v1.0",
                "confidence_score": self._calculate_analysis_confidence(responses)
            }
        }

    async def _generate_comparative_trend_analysis(
        self, 
        user_id: int, 
        sessions: List[DiagnosisSession], 
        department: str
    ) -> Dict[str, Any]:
        """2차 이상 진단테스트 완료 후 비교분석 및 학습추세 분석"""
        
        current_session = sessions[-1]
        previous_session = sessions[-2]
        
        # 모든 세션의 응답 데이터 조회
        all_responses = {}
        for session in sessions:
            responses = self.db.query(DiagnosisResponse).filter(
                DiagnosisResponse.session_id == session.id
            ).all()
            all_responses[session.id] = responses

        # 성과 비교 분석
        performance_comparison = self._compare_performance_across_sessions(sessions, all_responses)
        
        # 학습 추세 분석
        learning_trends = self._analyze_learning_trends(sessions, all_responses)
        
        # 영역별 발전 분석
        domain_progress = self._analyze_domain_progress(sessions, all_responses)
        
        # 약점 개선 분석
        weakness_improvement = self._analyze_weakness_improvement(sessions, all_responses)
        
        # 학습 패턴 분석
        learning_patterns = self._analyze_learning_patterns(sessions, all_responses)
        
        # 예측 및 목표 설정
        predictions = self._generate_performance_predictions(sessions, all_responses)
        
        # 동료 비교 (현재 차수 기준)
        peer_comparison = await self._get_peer_comparison_data(user_id, current_session, department)

        return {
            "analysis_type": "comparative_trend",
            "round_number": len(sessions),
            "completed_at": current_session.completed_at.isoformat(),
            "department": department,
            "total_rounds_completed": len(sessions),
            
            # 현재 성과 요약
            "current_performance": {
                "score": round(current_session.percentage_score, 1),
                "accuracy_rate": round(len([r for r in all_responses[current_session.id] if r.is_correct]) / len(all_responses[current_session.id]) * 100, 1),
                "time_spent_minutes": round(current_session.total_time_spent / 60, 1) if current_session.total_time_spent else 0,
                "performance_level": self._classify_performance_level(current_session.percentage_score / 100)
            },
            
            # 성과 비교 분석
            "performance_comparison": performance_comparison,
            
            # 학습 추세 분석
            "learning_trends": learning_trends,
            
            # 영역별 발전 분석
            "domain_progress": domain_progress,
            
            # 약점 개선 분석
            "weakness_improvement": weakness_improvement,
            
            # 학습 패턴 분석
            "learning_patterns": learning_patterns,
            
            # 성과 예측
            "predictions": predictions,
            
            # 동료 비교
            "peer_comparison": peer_comparison,
            
            # 시각화 데이터
            "visualizations": {
                "trend_chart": self._generate_trend_chart_data(sessions),
                "progress_radar": self._generate_progress_radar_data(domain_progress),
                "improvement_timeline": self._generate_improvement_timeline_data(sessions),
                "comparative_analysis": self._generate_comparative_chart_data(sessions)
            },
            
            # 개인화된 추천
            "personalized_recommendations": self._generate_advanced_learning_recommendations(
                learning_trends, domain_progress, weakness_improvement, predictions
            ),
            
            "analysis_metadata": {
                "analysis_date": datetime.now().isoformat(),
                "analysis_version": "comparative_v1.0",
                "confidence_score": self._calculate_trend_analysis_confidence(sessions),
                "data_completeness": len(sessions) / 10  # 전체 10차 중 완료된 비율
            }
        }

    def _analyze_performance_by_domain(self, responses: List[DiagnosisResponse]) -> Dict[str, Any]:
        """영역별 성과 분석"""
        domain_stats = {}
        
        # 응답을 도메인별로 그룹화 (메타데이터에서 도메인 정보 추출)
        for response in responses:
            # 임시로 문제 번호 기반 도메인 분류 (실제로는 문제 메타데이터 사용)
            domain = self._classify_domain_by_question_id(response.question_id)
            
            if domain not in domain_stats:
                domain_stats[domain] = {"total": 0, "correct": 0, "times": []}
            
            domain_stats[domain]["total"] += 1
            if response.is_correct:
                domain_stats[domain]["correct"] += 1
            if response.response_time:
                domain_stats[domain]["times"].append(response.response_time)
        
        # 도메인별 분석 결과 생성
        domain_analysis = {}
        for domain, stats in domain_stats.items():
            accuracy = stats["correct"] / stats["total"] if stats["total"] > 0 else 0
            avg_time = statistics.mean(stats["times"]) if stats["times"] else 0
            
            domain_analysis[domain] = {
                "accuracy_rate": round(accuracy * 100, 1),
                "questions_count": stats["total"],
                "correct_count": stats["correct"],
                "average_time": round(avg_time, 1),
                "performance_level": self._classify_performance_level(accuracy),
                "is_strength": accuracy >= 0.8,
                "is_weakness": accuracy < 0.6
            }
        
        return domain_analysis

    def _analyze_performance_by_difficulty(self, responses: List[DiagnosisResponse]) -> Dict[str, Any]:
        """난이도별 성과 분석"""
        difficulty_stats = {"easy": {"total": 0, "correct": 0}, 
                           "medium": {"total": 0, "correct": 0}, 
                           "hard": {"total": 0, "correct": 0}}
        
        for response in responses:
            # 임시로 문제 번호 기반 난이도 분류
            difficulty = self._classify_difficulty_by_question_id(response.question_id)
            
            difficulty_stats[difficulty]["total"] += 1
            if response.is_correct:
                difficulty_stats[difficulty]["correct"] += 1
        
        difficulty_analysis = {}
        for level, stats in difficulty_stats.items():
            accuracy = stats["correct"] / stats["total"] if stats["total"] > 0 else 0
            difficulty_analysis[level] = {
                "accuracy_rate": round(accuracy * 100, 1),
                "questions_count": stats["total"],
                "correct_count": stats["correct"],
                "performance_level": self._classify_performance_level(accuracy)
            }
        
        return difficulty_analysis

    def _analyze_response_times(self, responses: List[DiagnosisResponse]) -> Dict[str, Any]:
        """응답 시간 분석"""
        times = [r.response_time for r in responses if r.response_time]
        
        if not times:
            return {"message": "응답 시간 데이터가 없습니다."}
        
        return {
            "average_time": round(statistics.mean(times), 1),
            "median_time": round(statistics.median(times), 1),
            "min_time": round(min(times), 1),
            "max_time": round(max(times), 1),
            "time_consistency": round(1 - (statistics.stdev(times) / statistics.mean(times)), 2) if len(times) > 1 else 1.0,
            "time_efficiency": self._classify_time_efficiency(statistics.mean(times)),
            "time_distribution": {
                "fast_responses": len([t for t in times if t < 30]),
                "normal_responses": len([t for t in times if 30 <= t <= 90]),
                "slow_responses": len([t for t in times if t > 90])
            }
        }

    def _diagnose_initial_learning_state(
        self, 
        accuracy_rate: float, 
        domain_analysis: Dict, 
        difficulty_analysis: Dict, 
        time_analysis: Dict
    ) -> Dict[str, Any]:
        """초기 학습 상태 진단"""
        
        # 전반적 수준 평가
        overall_level = self._classify_performance_level(accuracy_rate)
        
        # 강점 영역 식별
        strengths = [domain for domain, analysis in domain_analysis.items() 
                    if analysis.get("is_strength", False)]
        
        # 약점 영역 식별
        weaknesses = [domain for domain, analysis in domain_analysis.items() 
                     if analysis.get("is_weakness", False)]
        
        # 학습 스타일 분석
        learning_style = self._analyze_initial_learning_style(difficulty_analysis, time_analysis)
        
        # 잠재력 평가
        potential_assessment = self._assess_learning_potential(
            accuracy_rate, domain_analysis, difficulty_analysis
        )

        return {
            "overall_level": overall_level,
            "accuracy_rate": round(accuracy_rate * 100, 1),
            "strengths": strengths,
            "weaknesses": weaknesses,
            "learning_style": learning_style,
            "potential_assessment": potential_assessment,
            "readiness_for_next_level": accuracy_rate >= 0.7,
            "key_insights": self._generate_key_insights(
                overall_level, strengths, weaknesses, learning_style
            )
        }

    def _compare_performance_across_sessions(
        self, 
        sessions: List[DiagnosisSession], 
        all_responses: Dict
    ) -> Dict[str, Any]:
        """세션 간 성과 비교 분석"""
        
        current_session = sessions[-1]
        previous_session = sessions[-2]
        
        current_responses = all_responses[current_session.id]
        previous_responses = all_responses[previous_session.id]
        
        # 기본 지표 비교
        current_accuracy = len([r for r in current_responses if r.is_correct]) / len(current_responses)
        previous_accuracy = len([r for r in previous_responses if r.is_correct]) / len(previous_responses)
        
        score_change = current_session.percentage_score - previous_session.percentage_score
        accuracy_change = (current_accuracy - previous_accuracy) * 100
        
        # 시간 비교
        current_avg_time = statistics.mean([r.response_time for r in current_responses if r.response_time])
        previous_avg_time = statistics.mean([r.response_time for r in previous_responses if r.response_time])
        time_change = current_avg_time - previous_avg_time
        
        return {
            "score_comparison": {
                "current_score": round(current_session.percentage_score, 1),
                "previous_score": round(previous_session.percentage_score, 1),
                "score_change": round(score_change, 1),
                "improvement_status": "개선" if score_change > 0 else "유지" if score_change == 0 else "감소"
            },
            "accuracy_comparison": {
                "current_accuracy": round(current_accuracy * 100, 1),
                "previous_accuracy": round(previous_accuracy * 100, 1),
                "accuracy_change": round(accuracy_change, 1),
                "improvement_status": "개선" if accuracy_change > 0 else "유지" if accuracy_change == 0 else "감소"
            },
            "time_comparison": {
                "current_avg_time": round(current_avg_time, 1),
                "previous_avg_time": round(previous_avg_time, 1),
                "time_change": round(time_change, 1),
                "efficiency_status": "향상" if time_change < 0 else "유지" if time_change == 0 else "감소"
            },
            "overall_trend": self._determine_overall_trend(score_change, accuracy_change, time_change)
        }

    def _analyze_learning_trends(
        self, 
        sessions: List[DiagnosisSession], 
        all_responses: Dict
    ) -> Dict[str, Any]:
        """학습 추세 분석"""
        
        # 점수 추세
        scores = [session.percentage_score for session in sessions]
        score_trend = self._calculate_trend_direction(scores)
        
        # 정확도 추세
        accuracies = []
        for session in sessions:
            responses = all_responses[session.id]
            accuracy = len([r for r in responses if r.is_correct]) / len(responses)
            accuracies.append(accuracy * 100)
        
        accuracy_trend = self._calculate_trend_direction(accuracies)
        
        # 시간 효율성 추세
        avg_times = []
        for session in sessions:
            responses = all_responses[session.id]
            times = [r.response_time for r in responses if r.response_time]
            if times:
                avg_times.append(statistics.mean(times))
        
        time_trend = self._calculate_trend_direction(avg_times, reverse=True)  # 시간은 적을수록 좋음
        
        # 일관성 분석
        consistency_score = self._calculate_performance_consistency(scores)
        
        # 학습 속도 분석
        learning_velocity = self._calculate_learning_velocity(sessions)

        return {
            "score_trend": {
                "direction": score_trend,
                "current_score": round(scores[-1], 1),
                "best_score": round(max(scores), 1),
                "average_score": round(statistics.mean(scores), 1),
                "improvement_rate": round((scores[-1] - scores[0]) / len(sessions), 2)
            },
            "accuracy_trend": {
                "direction": accuracy_trend,
                "current_accuracy": round(accuracies[-1], 1),
                "best_accuracy": round(max(accuracies), 1),
                "average_accuracy": round(statistics.mean(accuracies), 1)
            },
            "time_efficiency_trend": {
                "direction": time_trend,
                "current_avg_time": round(avg_times[-1], 1) if avg_times else 0,
                "best_avg_time": round(min(avg_times), 1) if avg_times else 0
            },
            "consistency_analysis": {
                "consistency_score": consistency_score,
                "consistency_level": self._classify_consistency_level(consistency_score),
                "stability_assessment": "안정적" if consistency_score > 0.8 else "변동적"
            },
            "learning_velocity": learning_velocity,
            "overall_progress": self._assess_overall_progress(score_trend, accuracy_trend, consistency_score)
        }

    def _analyze_domain_progress(
        self, 
        sessions: List[DiagnosisSession], 
        all_responses: Dict
    ) -> Dict[str, Any]:
        """영역별 발전 분석"""
        
        domain_progress = {}
        
        # 각 세션별로 도메인 성과 계산
        for i, session in enumerate(sessions):
            responses = all_responses[session.id]
            domain_stats = {}
            
            for response in responses:
                domain = self._classify_domain_by_question_id(response.question_id)
                
                if domain not in domain_stats:
                    domain_stats[domain] = {"total": 0, "correct": 0}
                
                domain_stats[domain]["total"] += 1
                if response.is_correct:
                    domain_stats[domain]["correct"] += 1
            
            # 도메인별 정확도 계산
            for domain, stats in domain_stats.items():
                accuracy = stats["correct"] / stats["total"] if stats["total"] > 0 else 0
                
                if domain not in domain_progress:
                    domain_progress[domain] = []
                
                domain_progress[domain].append({
                    "round": i + 1,
                    "accuracy": round(accuracy * 100, 1),
                    "questions_count": stats["total"],
                    "correct_count": stats["correct"]
                })
        
        # 각 도메인별 발전 분석
        domain_analysis = {}
        for domain, progress_data in domain_progress.items():
            accuracies = [data["accuracy"] for data in progress_data]
            trend = self._calculate_trend_direction(accuracies)
            
            domain_analysis[domain] = {
                "progress_data": progress_data,
                "trend": trend,
                "current_accuracy": accuracies[-1],
                "best_accuracy": max(accuracies),
                "improvement": round(accuracies[-1] - accuracies[0], 1),
                "consistency": self._calculate_performance_consistency(accuracies),
                "is_improving": trend in ["상승", "급상승"],
                "needs_attention": accuracies[-1] < 60 or trend in ["하락", "급하락"]
            }
        
        return domain_analysis

    def _analyze_weakness_improvement(
        self, 
        sessions: List[DiagnosisSession], 
        all_responses: Dict
    ) -> Dict[str, Any]:
        """약점 개선 분석"""
        
        # 첫 번째 세션에서 약점 영역 식별
        first_responses = all_responses[sessions[0].id]
        first_domain_analysis = self._analyze_performance_by_domain(first_responses)
        
        initial_weaknesses = [domain for domain, analysis in first_domain_analysis.items() 
                             if analysis.get("is_weakness", False)]
        
        if not initial_weaknesses:
            return {
                "message": "초기에 식별된 약점 영역이 없습니다.",
                "overall_strength": True
            }
        
        # 최신 세션에서 해당 영역들의 개선 정도 분석
        latest_responses = all_responses[sessions[-1].id]
        latest_domain_analysis = self._analyze_performance_by_domain(latest_responses)
        
        weakness_improvement = {}
        for weakness in initial_weaknesses:
            if weakness in latest_domain_analysis:
                initial_accuracy = first_domain_analysis[weakness]["accuracy_rate"]
                current_accuracy = latest_domain_analysis[weakness]["accuracy_rate"]
                improvement = current_accuracy - initial_accuracy
                
                weakness_improvement[weakness] = {
                    "initial_accuracy": initial_accuracy,
                    "current_accuracy": current_accuracy,
                    "improvement": round(improvement, 1),
                    "improvement_status": "크게 개선" if improvement > 20 else "개선" if improvement > 10 else "약간 개선" if improvement > 0 else "변화 없음" if improvement == 0 else "악화",
                    "is_overcome": current_accuracy >= 70,  # 70% 이상이면 약점 극복으로 간주
                    "improvement_rate": round(improvement / len(sessions), 1)  # 차수당 개선율
                }
        
        # 전체 약점 개선 요약
        total_improvement = sum([data["improvement"] for data in weakness_improvement.values()])
        overcome_count = sum([1 for data in weakness_improvement.values() if data["is_overcome"]])
        
        return {
            "initial_weaknesses": initial_weaknesses,
            "weakness_improvement": weakness_improvement,
            "summary": {
                "total_weaknesses": len(initial_weaknesses),
                "overcome_weaknesses": overcome_count,
                "overcome_rate": round(overcome_count / len(initial_weaknesses) * 100, 1),
                "average_improvement": round(total_improvement / len(initial_weaknesses), 1),
                "improvement_trend": "긍정적" if total_improvement > 0 else "정체" if total_improvement == 0 else "부정적"
            }
        }

    # 헬퍼 메서드들
    def _classify_domain_by_question_id(self, question_id: int) -> str:
        """문제 ID로 도메인 분류"""
        if question_id <= 10:
            return "기초의학"
        elif question_id <= 20:
            return "임상의학"
        else:
            return "전문치료"

    def _classify_difficulty_by_question_id(self, question_id: int) -> str:
        """문제 ID로 난이도 분류 (임시 구현)"""
        if question_id <= 10:
            return "easy"
        elif question_id <= 20:
            return "medium"
        else:
            return "hard"

    def _classify_performance_level(self, accuracy_rate: float) -> str:
        """성과 수준 분류"""
        if accuracy_rate >= 0.9:
            return "우수"
        elif accuracy_rate >= 0.8:
            return "양호"
        elif accuracy_rate >= 0.7:
            return "보통"
        elif accuracy_rate >= 0.6:
            return "미흡"
        else:
            return "부족"

    def _classify_time_efficiency(self, avg_time: float) -> str:
        """시간 효율성 분류"""
        if avg_time < 30:
            return "매우 빠름"
        elif avg_time < 60:
            return "빠름"
        elif avg_time < 90:
            return "보통"
        else:
            return "느림"

    def _calculate_trend_direction(self, values: List[float], reverse: bool = False) -> str:
        """추세 방향 계산"""
        if len(values) < 2:
            return "분석 불가"
        
        # 선형 회귀를 통한 추세 계산
        n = len(values)
        x_values = list(range(n))
        
        # 기울기 계산
        slope = (n * sum(x * y for x, y in zip(x_values, values)) - sum(x_values) * sum(values)) / (n * sum(x * x for x in x_values) - sum(x_values) ** 2)
        
        if reverse:
            slope = -slope
        
        if slope > 5:
            return "급상승"
        elif slope > 1:
            return "상승"
        elif slope > -1:
            return "안정"
        elif slope > -5:
            return "하락"
        else:
            return "급하락"

    def _calculate_performance_consistency(self, values: List[float]) -> float:
        """성과 일관성 계산"""
        if len(values) < 2:
            return 1.0
        
        # 변동계수의 역수로 일관성 측정
        mean_val = statistics.mean(values)
        if mean_val == 0:
            return 1.0
        
        cv = statistics.stdev(values) / mean_val
        consistency = max(0, 1 - cv / 2)  # 0~1 범위로 정규화
        
        return round(consistency, 3)

    def _generate_domain_radar_data(self, domain_analysis: Dict) -> Dict[str, Any]:
        """도메인 레이더 차트 데이터 생성"""
        return {
            "labels": list(domain_analysis.keys()),
            "datasets": [{
                "label": "현재 성과",
                "data": [analysis["accuracy_rate"] for analysis in domain_analysis.values()],
                "backgroundColor": "rgba(54, 162, 235, 0.2)",
                "borderColor": "rgba(54, 162, 235, 1)",
                "pointBackgroundColor": "rgba(54, 162, 235, 1)"
            }]
        }

    def _generate_trend_chart_data(self, sessions: List[DiagnosisSession]) -> Dict[str, Any]:
        """추세 차트 데이터 생성"""
        return {
            "labels": [f"{i+1}차" for i in range(len(sessions))],
            "datasets": [{
                "label": "점수 추이",
                "data": [round(session.percentage_score, 1) for session in sessions],
                "borderColor": "rgba(75, 192, 192, 1)",
                "backgroundColor": "rgba(75, 192, 192, 0.2)",
                "tension": 0.4
            }]
        }

    async def _get_peer_comparison_data(
        self, 
        user_id: int, 
        current_session: DiagnosisSession, 
        department: str
    ) -> Dict[str, Any]:
        """동료 비교 데이터 조회"""
        try:
            # 같은 학과의 다른 학생들 세션 조회
            peer_sessions = self.db.query(DiagnosisSession).join(
                DiagnosisTest, DiagnosisSession.test_id == DiagnosisTest.id
            ).join(
                User, DiagnosisSession.user_id == User.id
            ).filter(
                and_(
                    DiagnosisTest.department == department,
                    DiagnosisSession.status == "completed",
                    DiagnosisSession.user_id != user_id,
                    User.profile_info['department'].astext == department
                )
            ).all()

            if not peer_sessions:
                return {"message": "비교할 동료 데이터가 없습니다."}

            peer_scores = [session.percentage_score for session in peer_sessions if session.percentage_score]
            
            if not peer_scores:
                return {"message": "비교할 점수 데이터가 없습니다."}

            user_score = current_session.percentage_score
            peer_average = statistics.mean(peer_scores)
            
            # 백분위 계산
            better_than_count = sum(1 for score in peer_scores if user_score > score)
            percentile = (better_than_count / len(peer_scores)) * 100

            return {
                "user_score": round(user_score, 1),
                "peer_average": round(peer_average, 1),
                "peer_count": len(peer_scores),
                "percentile": round(percentile, 1),
                "ranking": len(peer_scores) - better_than_count + 1,
                "performance_vs_average": round(user_score - peer_average, 1),
                "comparison_status": "평균 이상" if user_score > peer_average else "평균 이하"
            }

        except Exception as e:
            logger.error(f"동료 비교 데이터 조회 실패: {str(e)}")
            return {"message": "동료 비교 데이터 조회에 실패했습니다."} 