"""
학습 수준 계산 관련 서비스
개발 보고서에 명시된 산술식을 구현
"""
import math
from typing import List, Dict, Any, Tuple, Optional
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)

class LearningCalculator:
    """
    학습 수준 계산기
    
    산술식: 학습수준지표 = (정답1 × 난이도점수1 + 정답2 × 난이도점수2 + ... + 정답n × 난이도점수n) 
    / (난이도점수1 + 난이도점수2 + ... + 난이도점수n)
    
    여기서:
    - 정답i: i번째 문제의 정답 여부 (정답=1, 오답=0)
    - 난이도점수i: i번째 문제의 난이도 점수 (쉬움=1, 보통=2, 어려움=3, 매우어려움=4, 전문가=5)
    - n: 전체 문제 수
    """
    
    # 난이도별 점수 매핑
    DIFFICULTY_SCORES = {
        1: 1.0,  # beginner
        2: 2.0,  # easy  
        3: 3.0,  # medium
        4: 4.0,  # hard
        5: 5.0   # expert
    }
    
    def calculate_learning_level(
        self, 
        answers: List[Tuple[bool, int]], 
        time_weights: Optional[List[float]] = None
    ) -> float:
        """
        기본 학습 수준 지표 계산
        
        Args:
            answers: List of (is_correct, difficulty) tuples
            time_weights: Optional time-based weights for each answer
            
        Returns:
            Learning level score (0.0 - 1.0)
        """
        if not answers:
            return 0.0
        
        total_score = 0.0
        max_possible_score = 0.0
        
        for i, (is_correct, difficulty) in enumerate(answers):
            difficulty_score = self.DIFFICULTY_SCORES.get(difficulty, 1.0)
            time_weight = time_weights[i] if time_weights and i < len(time_weights) else 1.0
            
            # 가중치 적용
            weighted_difficulty_score = difficulty_score * time_weight
            
            if is_correct:
                total_score += weighted_difficulty_score
            
            max_possible_score += weighted_difficulty_score
        
        learning_level = total_score / max_possible_score if max_possible_score > 0 else 0.0
        
        logger.debug(
            f"학습 수준 계산: total_score={total_score:.2f}, "
            f"max_possible_score={max_possible_score:.2f}, "
            f"learning_level={learning_level:.3f}"
        )
        
        return learning_level
    
    def calculate_weighted_learning_level(
        self,
        answers: List[Tuple[bool, int, Optional[int]]], 
        time_penalty: bool = True,
        confidence_boost: bool = True
    ) -> Dict[str, Any]:
        """
        가중치가 적용된 고급 학습 수준 계산
        
        Args:
            answers: List of (is_correct, difficulty, time_spent_seconds) tuples
            time_penalty: Whether to apply time penalty for slow answers
            confidence_boost: Whether to boost score for quick correct answers
            
        Returns:
            Dictionary with detailed calculation results
        """
        if not answers:
            return {
                "learning_level": 0.0,
                "base_score": 0.0,
                "time_adjusted_score": 0.0,
                "analysis": {}
            }
        
        base_score = 0.0
        time_adjusted_score = 0.0
        max_possible_score = 0.0
        difficulty_breakdown = {}
        time_analysis = {}
        
        for is_correct, difficulty, time_spent in answers:
            difficulty_score = self.DIFFICULTY_SCORES.get(difficulty, 1.0)
            max_possible_score += difficulty_score
            
            # 기본 점수 계산
            if is_correct:
                base_score += difficulty_score
                
                # 시간 기반 가중치 계산
                time_weight = self._calculate_time_weight(
                    difficulty, time_spent, confidence_boost
                ) if time_spent else 1.0
                
                time_adjusted_score += difficulty_score * time_weight
            
            # 난이도별 분석
            diff_key = str(difficulty)
            if diff_key not in difficulty_breakdown:
                difficulty_breakdown[diff_key] = {
                    "total": 0, "correct": 0, "accuracy": 0.0, "avg_time": 0.0
                }
            
            difficulty_breakdown[diff_key]["total"] += 1
            if is_correct:
                difficulty_breakdown[diff_key]["correct"] += 1
            
            if time_spent:
                if "times" not in difficulty_breakdown[diff_key]:
                    difficulty_breakdown[diff_key]["times"] = []
                difficulty_breakdown[diff_key]["times"].append(time_spent)
        
        # 난이도별 통계 완성
        for diff_key, data in difficulty_breakdown.items():
            data["accuracy"] = data["correct"] / data["total"] if data["total"] > 0 else 0.0
            if "times" in data and data["times"]:
                data["avg_time"] = sum(data["times"]) / len(data["times"])
        
        # 최종 학습 수준 계산
        base_learning_level = base_score / max_possible_score if max_possible_score > 0 else 0.0
        adjusted_learning_level = time_adjusted_score / max_possible_score if max_possible_score > 0 else 0.0
        
        return {
            "learning_level": adjusted_learning_level if time_penalty else base_learning_level,
            "base_score": base_score,
            "time_adjusted_score": time_adjusted_score,
            "max_possible_score": max_possible_score,
            "base_learning_level": base_learning_level,
            "adjusted_learning_level": adjusted_learning_level,
            "difficulty_breakdown": difficulty_breakdown,
            "total_questions": len(answers),
            "correct_answers": sum(1 for is_correct, _, _ in answers if is_correct)
        }
    
    def calculate_learning_trend(
        self, 
        historical_levels: List[Tuple[datetime, float]],
        window_days: int = 30
    ) -> Dict[str, Any]:
        """
        학습 추세 계산
        
        Args:
            historical_levels: List of (timestamp, learning_level) tuples
            window_days: Moving average window in days
            
        Returns:
            Trend analysis results
        """
        if len(historical_levels) < 2:
            return {
                "trend": "insufficient_data",
                "slope": 0.0,
                "improvement_rate": 0.0,
                "volatility": 0.0
            }
        
        # 시간순 정렬
        sorted_levels = sorted(historical_levels, key=lambda x: x[0])
        
        # 최근 데이터만 사용
        cutoff_date = datetime.utcnow() - timedelta(days=window_days)
        recent_levels = [(ts, level) for ts, level in sorted_levels if ts >= cutoff_date]
        
        if len(recent_levels) < 2:
            recent_levels = sorted_levels[-min(10, len(sorted_levels)):]  # 최소 10개 또는 전체
        
        # 선형 회귀로 추세 계산
        x_values = [(ts - recent_levels[0][0]).total_seconds() / 86400 for ts, _ in recent_levels]  # days
        y_values = [level for _, level in recent_levels]
        
        slope, intercept = self._linear_regression(x_values, y_values)
        
        # 변동성 계산 (표준편차)
        mean_level = sum(y_values) / len(y_values)
        volatility = math.sqrt(sum((y - mean_level) ** 2 for y in y_values) / len(y_values))
        
        # 개선율 계산
        if len(recent_levels) >= 2:
            initial_level = recent_levels[0][1]
            final_level = recent_levels[-1][1]
            improvement_rate = (final_level - initial_level) / initial_level if initial_level > 0 else 0.0
        else:
            improvement_rate = 0.0
        
        # 추세 분류
        if abs(slope) < 0.001:
            trend = "stable"
        elif slope > 0.005:
            trend = "improving"
        elif slope < -0.005:
            trend = "declining"
        else:
            trend = "slight_change"
        
        return {
            "trend": trend,
            "slope": slope,
            "improvement_rate": improvement_rate,
            "volatility": volatility,
            "recent_average": mean_level,
            "data_points": len(recent_levels),
            "time_span_days": (recent_levels[-1][0] - recent_levels[0][0]).days if len(recent_levels) > 1 else 0
        }
    
    def predict_future_performance(
        self,
        current_level: float,
        trend_data: Dict[str, Any],
        target_level: float,
        days_ahead: int = 30
    ) -> Dict[str, Any]:
        """
        미래 성과 예측
        
        Args:
            current_level: Current learning level
            trend_data: Trend analysis from calculate_learning_trend
            target_level: Target learning level to achieve
            days_ahead: Number of days to predict ahead
            
        Returns:
            Prediction results
        """
        slope = trend_data.get("slope", 0.0)
        volatility = trend_data.get("volatility", 0.1)
        
        # 선형 예측
        predicted_level = current_level + (slope * days_ahead)
        predicted_level = max(0.0, min(1.0, predicted_level))  # 0-1 범위로 제한
        
        # 목표 달성 시간 예측
        days_to_target = None
        achievement_probability = 0.0
        
        if slope > 0 and target_level > current_level:
            days_to_target = (target_level - current_level) / slope
            # 확률 계산 (변동성 고려)
            z_score = (target_level - predicted_level) / max(volatility, 0.01)
            achievement_probability = max(0.0, min(1.0, 0.5 + 0.5 * math.erf(z_score / math.sqrt(2))))
        elif target_level <= current_level:
            days_to_target = 0
            achievement_probability = 1.0
        
        # 신뢰구간 계산
        confidence_margin = 1.96 * volatility  # 95% 신뢰구간
        lower_bound = max(0.0, predicted_level - confidence_margin)
        upper_bound = min(1.0, predicted_level + confidence_margin)
        
        return {
            "predicted_level": predicted_level,
            "days_to_target": days_to_target,
            "achievement_probability": achievement_probability,
            "confidence_interval": {
                "lower": lower_bound,
                "upper": upper_bound,
                "margin": confidence_margin
            },
            "recommendation": self._generate_performance_recommendation(
                current_level, predicted_level, target_level, slope
            )
        }
    
    def _calculate_time_weight(
        self, 
        difficulty: int, 
        time_spent: Optional[int],
        confidence_boost: bool = True
    ) -> float:
        """시간 기반 가중치 계산"""
        if not time_spent:
            return 1.0
        
        # 난이도별 예상 시간 (초)
        expected_times = {
            1: 30,   # beginner: 30초
            2: 60,   # easy: 1분
            3: 120,  # medium: 2분
            4: 180,  # hard: 3분
            5: 300   # expert: 5분
        }
        
        expected_time = expected_times.get(difficulty, 60)
        time_ratio = time_spent / expected_time
        
        if not confidence_boost:
            return 1.0
        
        # 빠른 정답에 보너스, 느린 답안에 페널티
        if time_ratio <= 0.5:  # 매우 빠름
            return 1.2
        elif time_ratio <= 0.8:  # 빠름
            return 1.1
        elif time_ratio <= 1.2:  # 적정
            return 1.0
        elif time_ratio <= 2.0:  # 느림
            return 0.9
        else:  # 매우 느림
            return 0.8
    
    def _linear_regression(self, x_values: List[float], y_values: List[float]) -> Tuple[float, float]:
        """단순 선형 회귀"""
        if len(x_values) != len(y_values) or len(x_values) < 2:
            return 0.0, 0.0
        
        n = len(x_values)
        sum_x = sum(x_values)
        sum_y = sum(y_values)
        sum_xy = sum(x * y for x, y in zip(x_values, y_values))
        sum_x_squared = sum(x * x for x in x_values)
        
        denominator = n * sum_x_squared - sum_x * sum_x
        if abs(denominator) < 1e-10:
            return 0.0, sum_y / n
        
        slope = (n * sum_xy - sum_x * sum_y) / denominator
        intercept = (sum_y - slope * sum_x) / n
        
        return slope, intercept
    
    def _generate_performance_recommendation(
        self,
        current_level: float,
        predicted_level: float,
        target_level: float,
        slope: float
    ) -> str:
        """성과 기반 추천사항 생성"""
        if current_level >= target_level:
            return "목표를 이미 달성했습니다. 더 높은 목표를 설정해보세요."
        
        if slope <= 0:
            return "현재 진행 상황이 좋지 않습니다. 학습 방법을 개선하고 더 집중적으로 학습하세요."
        
        if predicted_level >= target_level:
            return "현재 추세를 유지하시면 목표를 달성할 수 있습니다."
        
        improvement_needed = target_level - predicted_level
        if improvement_needed > 0.2:
            return "목표 달성을 위해 학습 강도를 크게 높여야 합니다."
        elif improvement_needed > 0.1:
            return "목표 달성을 위해 학습 시간을 늘리고 어려운 문제에 도전하세요."
        else:
            return "조금만 더 노력하시면 목표를 달성할 수 있습니다." 