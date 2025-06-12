#!/usr/bin/env python3
"""
DKT (Deep Knowledge Tracing) 모델
학생의 지식 상태를 추적하고 예측하는 딥러닝 모델
"""

import torch
import torch.nn as nn
import torch.optim as optim
import numpy as np
from typing import Dict, List, Tuple, Optional
import pickle
import os
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

class DKTModel(nn.Module):
    """Deep Knowledge Tracing 모델"""
    
    def __init__(
        self,
        num_concepts: int = 5,  # 물리치료학 5개 도메인
        num_questions: int = 100,  # 최대 문항 수
        hidden_size: int = 128,
        num_layers: int = 2,
        dropout: float = 0.2
    ):
        super(DKTModel, self).__init__()
        
        self.num_concepts = num_concepts
        self.num_questions = num_questions
        self.hidden_size = hidden_size
        self.num_layers = num_layers
        
        # 입력 차원: (question_id, concept_id, is_correct, time_spent, confidence)
        input_size = num_questions + num_concepts + 3  # one-hot + features
        
        # LSTM 레이어
        self.lstm = nn.LSTM(
            input_size=input_size,
            hidden_size=hidden_size,
            num_layers=num_layers,
            dropout=dropout,
            batch_first=True
        )
        
        # 출력 레이어들
        self.concept_mastery = nn.Linear(hidden_size, num_concepts)  # 개념별 숙련도
        self.knowledge_state = nn.Linear(hidden_size, hidden_size // 2)  # 지식 상태
        self.difficulty_predictor = nn.Linear(hidden_size, 1)  # 난이도 예측
        self.time_predictor = nn.Linear(hidden_size, 1)  # 소요시간 예측
        
        # 활성화 함수
        self.sigmoid = nn.Sigmoid()
        self.relu = nn.ReLU()
        self.dropout = nn.Dropout(dropout)
        
    def forward(self, x: torch.Tensor, hidden: Optional[Tuple] = None) -> Dict[str, torch.Tensor]:
        """
        순전파
        Args:
            x: (batch_size, sequence_length, input_size) 입력 시퀀스
            hidden: LSTM 은닉 상태
        Returns:
            dict: 각종 예측 결과
        """
        # LSTM 처리
        lstm_out, hidden = self.lstm(x, hidden)
        
        # 마지막 시퀀스의 출력 사용
        last_output = lstm_out[:, -1, :]  # (batch_size, hidden_size)
        
        # 드롭아웃 적용
        last_output = self.dropout(last_output)
        
        # 각종 예측
        concept_scores = self.sigmoid(self.concept_mastery(last_output))  # (batch_size, num_concepts)
        knowledge_vec = self.relu(self.knowledge_state(last_output))      # (batch_size, hidden_size//2)
        difficulty_pred = self.sigmoid(self.difficulty_predictor(last_output))  # (batch_size, 1)
        time_pred = self.relu(self.time_predictor(last_output))          # (batch_size, 1)
        
        return {
            'concept_mastery': concept_scores,
            'knowledge_state': knowledge_vec,
            'difficulty_prediction': difficulty_pred,
            'time_prediction': time_pred,
            'hidden_state': hidden
        }
    
    def predict_next_performance(self, sequence: torch.Tensor) -> Dict[str, float]:
        """다음 문제 성능 예측"""
        self.eval()
        with torch.no_grad():
            output = self.forward(sequence.unsqueeze(0))  # 배치 차원 추가
            
            concept_scores = output['concept_mastery'].squeeze().numpy()
            difficulty_pred = output['difficulty_prediction'].squeeze().item()
            time_pred = output['time_prediction'].squeeze().item()
            
            return {
                'concept_mastery': {
                    'anatomy': float(concept_scores[0]),      # 해부학
                    'physiology': float(concept_scores[1]),   # 생리학  
                    'kinesiology': float(concept_scores[2]),  # 운동학
                    'therapy': float(concept_scores[3]),      # 치료학
                    'assessment': float(concept_scores[4])    # 평가학
                },
                'overall_difficulty': float(difficulty_pred),
                'estimated_time': float(time_pred),
                'confidence_score': float(np.mean(concept_scores))
            }

class DKTTrainer:
    """DKT 모델 훈련 클래스"""
    
    def __init__(self, model: DKTModel, learning_rate: float = 0.001):
        self.model = model
        self.optimizer = optim.Adam(model.parameters(), lr=learning_rate)
        self.criterion_mastery = nn.BCELoss()
        self.criterion_time = nn.MSELoss()
        self.criterion_difficulty = nn.BCELoss()
        
    def train_step(self, batch: Dict[str, torch.Tensor]) -> Dict[str, float]:
        """단일 훈련 스텝"""
        self.model.train()
        self.optimizer.zero_grad()
        
        # 순전파
        outputs = self.model(batch['sequences'])
        
        # 손실 계산
        mastery_loss = self.criterion_mastery(
            outputs['concept_mastery'], 
            batch['target_mastery']
        )
        
        time_loss = self.criterion_time(
            outputs['time_prediction'], 
            batch['target_time']
        )
        
        difficulty_loss = self.criterion_difficulty(
            outputs['difficulty_prediction'], 
            batch['target_difficulty']
        )
        
        # 총 손실
        total_loss = mastery_loss + 0.5 * time_loss + 0.3 * difficulty_loss
        
        # 역전파
        total_loss.backward()
        self.optimizer.step()
        
        return {
            'total_loss': total_loss.item(),
            'mastery_loss': mastery_loss.item(),
            'time_loss': time_loss.item(),
            'difficulty_loss': difficulty_loss.item()
        }
    
    def save_model(self, filepath: str) -> None:
        """모델 저장"""
        torch.save({
            'model_state_dict': self.model.state_dict(),
            'optimizer_state_dict': self.optimizer.state_dict(),
            'model_config': {
                'num_concepts': self.model.num_concepts,
                'num_questions': self.model.num_questions,
                'hidden_size': self.model.hidden_size,
                'num_layers': self.model.num_layers
            }
        }, filepath)
        logger.info(f"DKT 모델 저장 완료: {filepath}")
    
    def load_model(self, filepath: str) -> None:
        """모델 로드"""
        if os.path.exists(filepath):
            checkpoint = torch.load(filepath)
            self.model.load_state_dict(checkpoint['model_state_dict'])
            self.optimizer.load_state_dict(checkpoint['optimizer_state_dict'])
            logger.info(f"DKT 모델 로드 완료: {filepath}")
        else:
            logger.warning(f"모델 파일이 존재하지 않음: {filepath}")

class DataPreprocessor:
    """DKT 모델용 데이터 전처리기"""
    
    def __init__(self, num_concepts: int = 5, num_questions: int = 100):
        self.num_concepts = num_concepts
        self.num_questions = num_questions
        
        # 도메인 매핑
        self.domain_mapping = {
            '해부학': 0, 'anatomy': 0,
            '생리학': 1, 'physiology': 1,
            '운동학': 2, 'kinesiology': 2,
            '치료학': 3, 'therapy': 3,
            '평가학': 4, 'assessment': 4
        }
    
    def prepare_sequence(self, test_responses: List[Dict]) -> torch.Tensor:
        """테스트 응답을 DKT 입력 시퀀스로 변환"""
        sequence_data = []
        
        for response in test_responses:
            # 문항 원핫 인코딩
            question_vec = np.zeros(self.num_questions)
            if response.get('question_id', 0) < self.num_questions:
                question_vec[response.get('question_id', 0)] = 1
            
            # 개념 원핫 인코딩
            concept_vec = np.zeros(self.num_concepts)
            domain = response.get('domain', '해부학')
            concept_idx = self.domain_mapping.get(domain, 0)
            concept_vec[concept_idx] = 1
            
            # 추가 특성
            is_correct = float(response.get('is_correct', False))
            time_spent = min(response.get('time_spent', 60), 300) / 300.0  # 정규화
            confidence = response.get('confidence_level', 3) / 5.0  # 정규화
            
            # 특성 벡터 결합
            features = np.concatenate([
                question_vec,
                concept_vec,
                [is_correct, time_spent, confidence]
            ])
            
            sequence_data.append(features)
        
        return torch.FloatTensor(np.array(sequence_data))
    
    def prepare_training_batch(
        self, 
        student_sessions: List[List[Dict]]
    ) -> Dict[str, torch.Tensor]:
        """여러 학생 세션을 훈련 배치로 변환"""
        
        sequences = []
        target_masteries = []
        target_times = []
        target_difficulties = []
        
        for session in student_sessions:
            if len(session) < 2:  # 최소 2개 이상의 응답 필요
                continue
                
            # 입력 시퀀스 (마지막 제외)
            input_sequence = self.prepare_sequence(session[:-1])
            sequences.append(input_sequence)
            
            # 타겟 계산
            last_response = session[-1]
            
            # 개념별 숙련도 타겟 (실제 정답률 기반)
            concept_mastery = np.zeros(self.num_concepts)
            domain_stats = self._calculate_domain_performance(session)
            for i, (domain, perf) in enumerate(domain_stats.items()):
                if i < self.num_concepts:
                    concept_mastery[i] = perf['accuracy']
            
            target_masteries.append(concept_mastery)
            
            # 시간 타겟
            target_time = min(last_response.get('time_spent', 60), 300) / 300.0
            target_times.append([target_time])
            
            # 난이도 타겟 (정답 여부의 역)
            target_difficulty = 1.0 - float(last_response.get('is_correct', False))
            target_difficulties.append([target_difficulty])
        
        # 패딩 처리 (시퀀스 길이 맞추기)
        max_len = max(len(seq) for seq in sequences) if sequences else 1
        padded_sequences = []
        
        for seq in sequences:
            if len(seq) < max_len:
                padding = torch.zeros(max_len - len(seq), seq.shape[1])
                seq = torch.cat([seq, padding], dim=0)
            padded_sequences.append(seq)
        
        return {
            'sequences': torch.stack(padded_sequences),
            'target_mastery': torch.FloatTensor(target_masteries),
            'target_time': torch.FloatTensor(target_times),
            'target_difficulty': torch.FloatTensor(target_difficulties)
        }
    
    def _calculate_domain_performance(self, session: List[Dict]) -> Dict[str, Dict]:
        """세션 내 도메인별 성과 계산"""
        domain_stats = {}
        
        for domain_name in ['해부학', '생리학', '운동학', '치료학', '평가학']:
            domain_responses = [r for r in session if r.get('domain') == domain_name]
            
            if domain_responses:
                total = len(domain_responses)
                correct = sum(1 for r in domain_responses if r.get('is_correct', False))
                avg_time = np.mean([r.get('time_spent', 60) for r in domain_responses])
                
                domain_stats[domain_name] = {
                    'accuracy': correct / total,
                    'average_time': avg_time,
                    'total_questions': total
                }
            else:
                domain_stats[domain_name] = {
                    'accuracy': 0.5,  # 기본값
                    'average_time': 60,
                    'total_questions': 0
                }
        
        return domain_stats
