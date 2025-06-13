#!/usr/bin/env python3
"""
학습 패턴 분석기 (LSTM + RNN 기반)
학습자의 행동 패턴, 학습 스타일, 인지 능력을 분석
"""

import torch
import torch.nn as nn
import numpy as np
from typing import Dict, List, Tuple, Optional
from datetime import datetime
import logging
from sklearn.preprocessing import StandardScaler
import pickle
import os

logger = logging.getLogger(__name__)

class LearningPatternAnalyzer(nn.Module):
    """LSTM 기반 학습 패턴 분석 모델"""
    
    def __init__(
        self,
        input_size: int = 10,  # 입력 특성 수
        hidden_size: int = 64,
        num_layers: int = 2,
        dropout: float = 0.3
    ):
        super(LearningPatternAnalyzer, self).__init__()
        
        self.hidden_size = hidden_size
        self.num_layers = num_layers
        
        # BiLSTM for pattern recognition
        self.bilstm = nn.LSTM(
            input_size=input_size,
            hidden_size=hidden_size,
            num_layers=num_layers,
            dropout=dropout,
            bidirectional=True,
            batch_first=True
        )
        
        # Attention mechanism
        self.attention = nn.MultiheadAttention(
            embed_dim=hidden_size * 2,  # bidirectional
            num_heads=8,
            dropout=dropout
        )
        
        # Pattern classification layers
        self.pattern_classifier = nn.Sequential(
            nn.Linear(hidden_size * 2, hidden_size),
            nn.ReLU(),
            nn.Dropout(dropout),
            nn.Linear(hidden_size, 32),
            nn.ReLU(),
            nn.Linear(32, 4)  # 4가지 학습 패턴
        )
        
        # Learning style predictor
        self.style_predictor = nn.Sequential(
            nn.Linear(hidden_size * 2, hidden_size),
            nn.ReLU(),
            nn.Dropout(dropout),
            nn.Linear(hidden_size, 16),
            nn.ReLU(),
            nn.Linear(16, 3)  # 즉흥형, 신중형, 균형형
        )
        
        # Cognitive load estimator
        self.cognitive_estimator = nn.Sequential(
            nn.Linear(hidden_size * 2, hidden_size),
            nn.ReLU(),
            nn.Dropout(dropout),
            nn.Linear(hidden_size, 1)  # 인지 부하 정도
        )
        
        # Time consistency analyzer
        self.time_analyzer = nn.Sequential(
            nn.Linear(hidden_size * 2, hidden_size),
            nn.ReLU(),
            nn.Dropout(dropout),
            nn.Linear(hidden_size, 1)  # 시간 일관성
        )
        
        self.sigmoid = nn.Sigmoid()
        self.softmax = nn.Softmax(dim=-1)
        
    def forward(self, x: torch.Tensor) -> Dict[str, torch.Tensor]:
        """
        Args:
            x: (batch_size, sequence_length, input_size)
        Returns:
            dict: 각종 분석 결과
        """
        # BiLSTM 처리
        lstm_out, _ = self.bilstm(x)  # (batch_size, seq_len, hidden_size*2)
        
        # Attention 적용
        attn_out, _ = self.attention(
            lstm_out.transpose(0, 1),  # (seq_len, batch_size, hidden_size*2)
            lstm_out.transpose(0, 1),
            lstm_out.transpose(0, 1)
        )
        attn_out = attn_out.transpose(0, 1)  # (batch_size, seq_len, hidden_size*2)
        
        # Global average pooling
        pooled = torch.mean(attn_out, dim=1)  # (batch_size, hidden_size*2)
        
        # 각종 예측
        pattern_scores = self.softmax(self.pattern_classifier(pooled))
        style_scores = self.softmax(self.style_predictor(pooled))
        cognitive_load = self.sigmoid(self.cognitive_estimator(pooled))
        time_consistency = self.sigmoid(self.time_analyzer(pooled))
        
        return {
            'learning_patterns': pattern_scores,
            'learning_style': style_scores,
            'cognitive_load': cognitive_load,
            'time_consistency': time_consistency
        }

class CognitiveStateTracker(nn.Module):
    """RNN 기반 인지 상태 추적기"""
    
    def __init__(
        self,
        input_size: int = 15,
        hidden_size: int = 48,
        num_layers: int = 2
    ):
        super(CognitiveStateTracker, self).__init__()
        
        # GRU for cognitive state tracking
        self.gru = nn.GRU(
            input_size=input_size,
            hidden_size=hidden_size,
            num_layers=num_layers,
            batch_first=True
        )
        
        # Cognitive indicators
        self.attention_tracker = nn.Linear(hidden_size, 1)  # 주의력
        self.memory_tracker = nn.Linear(hidden_size, 1)    # 기억력  
        self.processing_tracker = nn.Linear(hidden_size, 1) # 처리 속도
        self.fatigue_tracker = nn.Linear(hidden_size, 1)   # 피로도
        
        self.sigmoid = nn.Sigmoid()
        
    def forward(self, x: torch.Tensor) -> Dict[str, torch.Tensor]:
        """
        Args:
            x: (batch_size, sequence_length, input_size)
        Returns:
            dict: 인지 상태 지표들
        """
        gru_out, _ = self.gru(x)
        
        # 마지막 시점의 상태 사용
        last_state = gru_out[:, -1, :]  # (batch_size, hidden_size)
        
        # 인지 지표 예측
        attention = self.sigmoid(self.attention_tracker(last_state))
        memory = self.sigmoid(self.memory_tracker(last_state))
        processing = self.sigmoid(self.processing_tracker(last_state))
        fatigue = self.sigmoid(self.fatigue_tracker(last_state))
        
        return {
            'attention_level': attention,
            'memory_retention': memory,
            'processing_speed': processing,
            'fatigue_level': fatigue
        }

class LearningAnalyzer:
    """종합 학습 분석기"""
    
    def __init__(self, model_dir: str = "models/"):
        self.model_dir = model_dir
        os.makedirs(model_dir, exist_ok=True)
        
        # 모델 초기화
        self.pattern_model = LearningPatternAnalyzer()
        self.cognitive_model = CognitiveStateTracker()
        
        # 전처리기
        self.scaler = StandardScaler()
        self.is_fitted = False
        
        # 패턴 매핑
        self.pattern_names = ['순차적', '탐색적', '반복적', '직관적']
        self.style_names = ['즉흥형', '신중형', '균형형']
        
        self._load_models()
    
    def analyze_learning_session(self, test_responses: List[Dict]) -> Dict[str, any]:
        """학습 세션 종합 분석"""
        
        if len(test_responses) < 3:
            return self._get_default_analysis()
        
        try:
            # 특성 추출
            features = self._extract_features(test_responses)
            
            if features is None or len(features) == 0:
                return self._get_default_analysis()
            
            # 텐서 변환
            feature_tensor = torch.FloatTensor(features).unsqueeze(0)  # (1, seq_len, features)
            
            # 패턴 분석
            with torch.no_grad():
                pattern_results = self.pattern_model(feature_tensor)
                cognitive_results = self.cognitive_model(feature_tensor)
            
            # 결과 해석
            analysis = self._interpret_results(
                pattern_results, 
                cognitive_results, 
                test_responses
            )
            
            return analysis
            
        except Exception as e:
            logger.error(f"학습 분석 오류: {str(e)}")
            return self._get_default_analysis()
    
    def _extract_features(self, responses: List[Dict]) -> Optional[np.ndarray]:
        """응답에서 학습 특성 추출"""
        
        if not responses:
            return None
        
        features = []
        prev_time = 0
        
        for i, response in enumerate(responses):
            feature_vec = []
            
            # 시간 관련 특성
            time_spent = response.get('time_spent', 60)
            feature_vec.append(min(time_spent / 300.0, 1.0))  # 정규화된 시간
            
            # 시간 변화율
            if i > 0:
                time_change = (time_spent - prev_time) / max(prev_time, 1)
                feature_vec.append(np.tanh(time_change))  # 변화율
            else:
                feature_vec.append(0.0)
            
            prev_time = time_spent
            
            # 정답 여부
            feature_vec.append(float(response.get('is_correct', False)))
            
            # 확신도
            confidence = response.get('confidence_level', 3)
            feature_vec.append(confidence / 5.0)
            
            # 문제 순서 (위치 정보)
            feature_vec.append(i / len(responses))
            
            # 도메인 원핫 인코딩 (5개 도메인)
            domain = response.get('domain', '해부학')
            domain_mapping = {
                '해부학': [1,0,0,0,0], '생리학': [0,1,0,0,0], '운동학': [0,0,1,0,0],
                '치료학': [0,0,0,1,0], '평가학': [0,0,0,0,1]
            }
            domain_vec = domain_mapping.get(domain, [0,0,0,0,1])
            feature_vec.extend(domain_vec)
            
            features.append(feature_vec)
        
        feature_array = np.array(features)
        
        # 표준화 (처음 사용시에만 fit)
        if not self.is_fitted:
            try:
                self.scaler.fit(feature_array)
                self.is_fitted = True
                # 스케일러 저장
                with open(f"{self.model_dir}/scaler.pkl", 'wb') as f:
                    pickle.dump(self.scaler, f)
            except:
                pass  # 실패시 원본 사용
        
        try:
            feature_array = self.scaler.transform(feature_array)
        except:
            pass  # 실패시 원본 사용
        
        return feature_array
    
    def _interpret_results(
        self, 
        pattern_results: Dict, 
        cognitive_results: Dict,
        responses: List[Dict]
    ) -> Dict[str, any]:
        """분석 결과 해석"""
        
        # 패턴 분석
        pattern_probs = pattern_results['learning_patterns'].squeeze().numpy()
        dominant_pattern_idx = np.argmax(pattern_probs)
        dominant_pattern = self.pattern_names[dominant_pattern_idx]
        pattern_confidence = float(pattern_probs[dominant_pattern_idx])
        
        # 스타일 분석
        style_probs = pattern_results['learning_style'].squeeze().numpy()
        dominant_style_idx = np.argmax(style_probs)
        dominant_style = self.style_names[dominant_style_idx]
        style_confidence = float(style_probs[dominant_style_idx])
        
        # 인지 상태
        cognitive_load = float(pattern_results['cognitive_load'].squeeze())
        time_consistency = float(pattern_results['time_consistency'].squeeze())
        attention = float(cognitive_results['attention_level'].squeeze())
        fatigue = float(cognitive_results['fatigue_level'].squeeze())
        
        # 시간 패턴 분석
        times = [r.get('time_spent', 60) for r in responses]
        time_trend = self._analyze_time_trend(times)
        
        # 피로도 감지
        fatigue_detected = fatigue > 0.7 or self._detect_fatigue_pattern(responses)
        
        return {
            'learning_patterns': {
                'dominant_pattern': dominant_pattern,
                'pattern_confidence': pattern_confidence,
                'all_patterns': {
                    name: float(prob) for name, prob in zip(self.pattern_names, pattern_probs)
                }
            },
            'learning_style': {
                'response_style': dominant_style,
                'style_confidence': style_confidence,
                'all_styles': {
                    name: float(prob) for name, prob in zip(self.style_names, style_probs)
                }
            },
            'cognitive_metrics': {
                'cognitive_load': cognitive_load,
                'attention_level': attention,
                'fatigue_level': fatigue,
                'processing_efficiency': 1.0 - cognitive_load
            },
            'time_analysis': {
                'average_response_time': float(np.mean(times)),
                'time_consistency': time_consistency,
                'time_trend': time_trend,
                'fatigue_detected': fatigue_detected
            },
            'behavioral_insights': self._generate_behavioral_insights(
                dominant_pattern, dominant_style, cognitive_load, time_trend
            )
        }
    
    def _analyze_time_trend(self, times: List[float]) -> str:
        """시간 트렌드 분석"""
        if len(times) < 3:
            return "일관됨"
        
        # 시간 변화 계산
        first_half = np.mean(times[:len(times)//2])
        second_half = np.mean(times[len(times)//2:])
        
        change_ratio = (second_half - first_half) / first_half
        
        if change_ratio > 0.2:
            return "느려짐"
        elif change_ratio < -0.2:
            return "빨라짐"
        else:
            return "일관됨"
    
    def _detect_fatigue_pattern(self, responses: List[Dict]) -> bool:
        """피로도 패턴 감지"""
        if len(responses) < 10:
            return False
        
        # 후반부 정답률 vs 전반부 정답률
        mid_point = len(responses) // 2
        first_half_acc = np.mean([r.get('is_correct', False) for r in responses[:mid_point]])
        second_half_acc = np.mean([r.get('is_correct', False) for r in responses[mid_point:]])
        
        # 후반부 시간 증가
        first_half_time = np.mean([r.get('time_spent', 60) for r in responses[:mid_point]])
        second_half_time = np.mean([r.get('time_spent', 60) for r in responses[mid_point:]])
        
        # 피로도 판정: 정답률 감소 + 시간 증가
        accuracy_drop = first_half_acc - second_half_acc > 0.2
        time_increase = (second_half_time - first_half_time) / first_half_time > 0.3
        
        return accuracy_drop and time_increase
    
    def _generate_behavioral_insights(
        self, 
        pattern: str, 
        style: str, 
        cognitive_load: float,
        time_trend: str
    ) -> List[str]:
        """행동 패턴 기반 인사이트 생성"""
        
        insights = []
        
        # 패턴별 인사이트
        if pattern == "순차적":
            insights.append("체계적으로 문제를 해결하는 성향을 보입니다.")
        elif pattern == "탐색적":
            insights.append("다양한 접근 방식을 시도하는 탐구적 성향입니다.")
        elif pattern == "반복적":
            insights.append("신중하게 검토하는 꼼꼼한 성향입니다.")
        else:
            insights.append("직관적 판단력이 뛰어난 성향입니다.")
        
        # 스타일별 인사이트
        if style == "즉흥형":
            insights.append("빠른 판단력을 가지고 있으나 신중함이 필요합니다.")
        elif style == "신중형":
            insights.append("신중한 접근을 하나 때로는 과감함이 필요합니다.")
        else:
            insights.append("균형잡힌 문제 해결 방식을 보입니다.")
        
        # 인지 부하 인사이트
        if cognitive_load > 0.7:
            insights.append("높은 인지 부하가 감지되어 휴식이 필요해 보입니다.")
        elif cognitive_load < 0.3:
            insights.append("여유로운 상태로 더 도전적인 문제도 가능합니다.")
        
        # 시간 트렌드 인사이트
        if time_trend == "느려짐":
            insights.append("집중력이 점차 저하되는 패턴이 관찰됩니다.")
        elif time_trend == "빨라짐":
            insights.append("문제 해결 속도가 향상되는 긍정적 패턴입니다.")
        
        return insights
    
    def _get_default_analysis(self) -> Dict[str, any]:
        """기본 분석 결과 (데이터 부족시)"""
        
        return {
            'learning_patterns': {
                'dominant_pattern': "순차적",
                'pattern_confidence': 0.6,
                'all_patterns': {name: 0.25 for name in self.pattern_names}
            },
            'learning_style': {
                'response_style': "균형형",
                'style_confidence': 0.5,
                'all_styles': {name: 0.33 for name in self.style_names}
            },
            'cognitive_metrics': {
                'cognitive_load': 0.5,
                'attention_level': 0.7,
                'fatigue_level': 0.3,
                'processing_efficiency': 0.5
            },
            'time_analysis': {
                'average_response_time': 56.0,
                'time_consistency': 0.7,
                'time_trend': "일관됨",
                'fatigue_detected': False
            },
            'behavioral_insights': [
                "분석에 필요한 데이터가 부족합니다.",
                "더 많은 문제를 풀어보시기 바랍니다."
            ]
        }
    
    def _load_models(self):
        """저장된 모델 로드"""
        try:
            pattern_path = f"{self.model_dir}/pattern_analyzer.pth"
            cognitive_path = f"{self.model_dir}/cognitive_tracker.pth"
            scaler_path = f"{self.model_dir}/scaler.pkl"
            
            if os.path.exists(pattern_path):
                self.pattern_model.load_state_dict(torch.load(pattern_path))
                logger.info("패턴 분석 모델 로드 완료")
            
            if os.path.exists(cognitive_path):
                self.cognitive_model.load_state_dict(torch.load(cognitive_path))
                logger.info("인지 상태 모델 로드 완료")
            
            if os.path.exists(scaler_path):
                with open(scaler_path, 'rb') as f:
                    self.scaler = pickle.load(f)
                    self.is_fitted = True
                logger.info("스케일러 로드 완료")
                
        except Exception as e:
            logger.warning(f"모델 로드 실패, 기본 모델 사용: {e}")
    
    def save_models(self):
        """모델 저장"""
        try:
            torch.save(self.pattern_model.state_dict(), f"{self.model_dir}/pattern_analyzer.pth")
            torch.save(self.cognitive_model.state_dict(), f"{self.model_dir}/cognitive_tracker.pth")
            
            if self.is_fitted:
                with open(f"{self.model_dir}/scaler.pkl", 'wb') as f:
                    pickle.dump(self.scaler, f)
            
            logger.info("모델 저장 완료")
        except Exception as e:
            logger.error(f"모델 저장 실패: {e}")
    
    def update_models(self, training_data: List[List[Dict]]):
        """새로운 데이터로 모델 업데이트"""
        # 실제 환경에서는 여기서 모델 재훈련
        logger.info("모델 업데이트 요청됨 (실제 구현 필요)")
        pass
