#!/usr/bin/env python3
"""
지식 추적 및 종합 AI 분석 시스템
DKT + LSTM + DeepSeek 통합 분석
"""

import asyncio
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime
import json
import numpy as np

logger = logging.getLogger(__name__)

class KnowledgeTracer:
    """지식 추적 및 종합 AI 분석 시스템"""
    
    def __init__(self, model_dir: str = "models/"):
        self.model_dir = model_dir
        
        # 도메인 매핑
        self.domain_mapping = {
            '해부학': 'anatomy',
            '생리학': 'physiology', 
            '운동학': 'kinesiology',
            '치료학': 'therapy',
            '평가학': 'assessment'
        }
        
        # 나중에 import (순환 참조 방지)
        self.dkt_model = None
        self.learning_analyzer = None
        self.deepseek_service = None
        
        self._initialize_models()
    
    def _initialize_models(self):
        """모델 초기화 (지연 로딩)"""
        try:
            from .dkt_model import DKTModel, DKTTrainer, DataPreprocessor
            from .learning_analyzer import LearningAnalyzer
            from ..services.deepseek_service import DeepSeekService
            
            self.dkt_model = DKTModel()
            self.dkt_trainer = DKTTrainer(self.dkt_model)
            self.data_preprocessor = DataPreprocessor()
            self.learning_analyzer = LearningAnalyzer(self.model_dir)
            self.deepseek_service = DeepSeekService()
            
            self._load_models()
            logger.info("AI 모델 초기화 완료")
            
        except Exception as e:
            logger.warning(f"AI 모델 초기화 실패: {e}")
    
    async def analyze_student_performance(
        self, 
        user_id: int,
        test_responses: List[Dict],
        test_session: Dict
    ) -> Dict[str, Any]:
        """학생 성과 종합 분석"""
        
        logger.info(f"🧠 AI 분석 시작: user_id={user_id}, responses={len(test_responses)}")
        
        try:
            # 모델이 초기화되지 않은 경우 대안 분석
            if not self.dkt_model or not self.learning_analyzer:
                logger.warning("AI 모델 미초기화, 통계적 분석 사용")
                return self._get_statistical_analysis(test_responses)
            
            # 1. DKT 분석 (지식 추적)
            dkt_analysis = await self._perform_dkt_analysis(test_responses)
            
            # 2. LSTM 학습 패턴 분석
            pattern_analysis = self.learning_analyzer.analyze_learning_session(test_responses)
            
            # 3. DeepSeek 종합 분석
            deepseek_analysis = await self._perform_deepseek_analysis(
                test_responses, dkt_analysis, pattern_analysis, test_session
            )
            
            # 4. 통합 분석 결과 생성
            integrated_analysis = self._integrate_ai_analyses(
                dkt_analysis, pattern_analysis, deepseek_analysis
            )
            
            logger.info(f"✅ AI 분석 완료: user_id={user_id}")
            return integrated_analysis
            
        except Exception as e:
            logger.error(f"❌ AI 분석 실패: user_id={user_id}, error={str(e)}")
            return self._get_fallback_analysis(test_responses)
    
    async def _perform_dkt_analysis(self, test_responses: List[Dict]) -> Dict[str, Any]:
        """DKT 모델 분석"""
        
        try:
            if len(test_responses) < 2:
                return self._get_default_dkt_analysis()
            
            # 시퀀스 데이터 준비
            sequence = self.data_preprocessor.prepare_sequence(test_responses)
            
            # DKT 예측
            predictions = self.dkt_model.predict_next_performance(sequence)
            
            # 개념별 숙련도 분석
            concept_mastery = predictions['concept_mastery']
            
            # 학습 진행도 계산
            learning_progress = self._calculate_learning_progress(test_responses, concept_mastery)
            
            return {
                'concept_mastery': concept_mastery,
                'learning_progress': learning_progress,
                'knowledge_state': {
                    'overall_mastery': float(np.mean(list(concept_mastery.values()))),
                    'confidence_score': predictions['confidence_score'],
                    'difficulty_prediction': predictions['overall_difficulty'],
                    'time_estimation': predictions['estimated_time']
                },
                'domain_predictions': self._generate_domain_predictions(concept_mastery),
                'learning_trajectory': self._analyze_learning_trajectory(test_responses)
            }
            
        except Exception as e:
            logger.error(f"DKT 분석 오류: {str(e)}")
            return self._get_default_dkt_analysis()
    
    def _calculate_learning_progress(
        self, 
        responses: List[Dict], 
        concept_mastery: Dict[str, float]
    ) -> Dict[str, Any]:
        """학습 진행도 계산"""
        
        # 시간별 정답률 변화
        time_intervals = max(1, len(responses) // 3)
            
        accuracy_over_time = []
        for i in range(0, len(responses), time_intervals):
            interval_responses = responses[i:i+time_intervals]
            if interval_responses:
                accuracy = sum(r.get('is_correct', False) for r in interval_responses) / len(interval_responses)
                accuracy_over_time.append(accuracy)
        
        # 학습 곡선 기울기
        if len(accuracy_over_time) > 1:
            learning_slope = (accuracy_over_time[-1] - accuracy_over_time[0]) / (len(accuracy_over_time) - 1)
        else:
            learning_slope = 0.0
        
        # 개념별 진행도
        domain_progress = {}
        for domain_kr, domain_en in self.domain_mapping.items():
            domain_responses = [r for r in responses if r.get('domain') == domain_kr]
            if domain_responses:
                domain_accuracy = sum(r.get('is_correct', False) for r in domain_responses) / len(domain_responses)
                mastery_score = concept_mastery.get(domain_en, 0.5)
                
                # 진행도 = (현재 정확도 + 예측 숙련도) / 2
                progress = (domain_accuracy + mastery_score) / 2
                domain_progress[domain_kr] = {
                    'current_accuracy': domain_accuracy,
                    'predicted_mastery': mastery_score,
                    'progress_score': progress,
                    'question_count': len(domain_responses)
                }
        
        overall_progress = float(np.mean([dp['progress_score'] for dp in domain_progress.values()])) if domain_progress else 0.5
        
        return {
            'accuracy_trend': accuracy_over_time,
            'learning_slope': learning_slope,
            'improvement_rate': max(0, learning_slope),
            'domain_progress': domain_progress,
            'overall_progress': overall_progress
        }
    
    def _generate_domain_predictions(self, concept_mastery: Dict[str, float]) -> Dict[str, Any]:
        """도메인별 예측 생성"""
        
        predictions = {}
        
        for domain_kr, domain_en in self.domain_mapping.items():
            mastery = concept_mastery.get(domain_en, 0.5)
            
            # 숙련도 레벨 결정
            if mastery >= 0.8:
                level = "우수"
                next_action = "심화 문제 도전"
            elif mastery >= 0.6:
                level = "양호"
                next_action = "연습 문제 풀이"
            elif mastery >= 0.4:
                level = "보통"
                next_action = "기초 개념 복습"
            else:
                level = "부족"
                next_action = "기본 이론 학습"
            
            predictions[domain_kr] = {
                'mastery_score': mastery,
                'level': level,
                'next_action': next_action,
                'confidence': min(mastery * 1.2, 1.0)  # 신뢰도
            }
        
        return predictions
    
    def _analyze_learning_trajectory(self, responses: List[Dict]) -> Dict[str, Any]:
        """학습 궤적 분석"""
        
        if len(responses) < 5:
            return {'status': 'insufficient_data'}
        
        # 정답률 변화 패턴
        accuracy_sequence = [float(r.get('is_correct', False)) for r in responses]
        
        # 이동 평균 계산 (window=5)
        window_size = min(5, len(accuracy_sequence))
        moving_avg = []
        for i in range(len(accuracy_sequence) - window_size + 1):
            avg = np.mean(accuracy_sequence[i:i+window_size])
            moving_avg.append(avg)
        
        # 학습 단계 분류
        if len(moving_avg) > 2:
            initial_phase = np.mean(moving_avg[:max(1, len(moving_avg)//3)])
            final_phase = np.mean(moving_avg[-max(1, len(moving_avg)//3):])
            
            if final_phase > initial_phase + 0.2:
                trajectory_type = "상승형"
                trajectory_desc = "학습이 지속적으로 향상되고 있습니다"
            elif initial_phase > final_phase + 0.2:
                trajectory_type = "하락형"
                trajectory_desc = "집중력 저하나 피로가 의심됩니다"
            else:
                trajectory_type = "안정형"
                trajectory_desc = "일정한 수준을 유지하고 있습니다"
        else:
            trajectory_type = "판단불가"
            trajectory_desc = "더 많은 데이터가 필요합니다"
        
        return {
            'trajectory_type': trajectory_type,
            'description': trajectory_desc,
            'accuracy_sequence': accuracy_sequence,
            'moving_average': moving_avg,
            'initial_performance': float(np.mean(accuracy_sequence[:3])),
            'final_performance': float(np.mean(accuracy_sequence[-3:])),
            'volatility': float(np.std(accuracy_sequence))
        }
    
    async def _perform_deepseek_analysis(
        self,
        test_responses: List[Dict],
        dkt_analysis: Dict[str, Any],
        pattern_analysis: Dict[str, Any],
        test_session: Dict
    ) -> Dict[str, Any]:
        """DeepSeek AI 종합 분석"""
        
        try:
            # DeepSeek 서비스가 없으면 로컬 분석
            if not self.deepseek_service:
                return self._generate_local_analysis(dkt_analysis, pattern_analysis)
            
            # 분석 데이터 준비
            analysis_data = self._prepare_comprehensive_data(
                test_responses, dkt_analysis, pattern_analysis, test_session
            )
            
            # DeepSeek 분석 요청
            deepseek_result = await self.deepseek_service.chat_completion(
                messages=[
                    {"role": "system", "content": "당신은 물리치료학과 전문 교육 분석가입니다."},
                    {"role": "user", "content": analysis_data}
                ],
                temperature=0.3
            )
            
            if deepseek_result.get("success"):
                content = deepseek_result.get('content', '')
                
                return {
                    'status': 'success',
                    'analysis_summary': content,
                    'insights': self._extract_insights_from_deepseek(content),
                    'recommendations': self._extract_recommendations_from_deepseek(content),
                    'generated_at': datetime.now().isoformat()
                }
            else:
                logger.warning("DeepSeek 분석 실패, 로컬 분석 사용")
                return self._generate_local_analysis(dkt_analysis, pattern_analysis)
                
        except Exception as e:
            logger.error(f"DeepSeek 분석 오류: {str(e)}")
            return self._generate_local_analysis(dkt_analysis, pattern_analysis)
    
    def _prepare_comprehensive_data(
        self,
        responses: List[Dict],
        dkt_analysis: Dict[str, Any],
        pattern_analysis: Dict[str, Any],
        test_session: Dict
    ) -> str:
        """종합 분석용 데이터 준비 (실제 진단 테스트 기반)"""
        
        # 기본 통계
        total_questions = len(responses)
        correct_answers = sum(r.get('is_correct', False) for r in responses)
        accuracy_rate = correct_answers / total_questions if total_questions > 0 else 0
        
        # 평균 응답 시간 (매우 중요!)
        avg_response_time = np.mean([r.get('time_spent', 2) for r in responses]) if responses else 2.0
        total_time = sum([r.get('time_spent', 2) for r in responses]) if responses else 60
        
        # 진단 테스트 도메인별 성과 (실제 구성 반영)
        domain_stats = {}
        domain_mapping = {
            '근골격계': ['근골격계', '근골격계/소아/노인'],
            '신경계': ['신경계', '신경계/뇌신경', '신경계/신경과학 기본', '신경계/근골격계'],
            '심폐계': ['심폐'],
            '기타/기초의학': ['기타', '기타 (생물학적 기본 개념)', '기타(눈의 구조와 기능)', '기타 (생리학/의학교육)']
        }
        
        for main_domain, sub_domains in domain_mapping.items():
            domain_responses = [r for r in responses if any(sub in r.get('domain', '') for sub in sub_domains)]
            if domain_responses:
                domain_accuracy = sum(r.get('is_correct', False) for r in domain_responses) / len(domain_responses)
                domain_time = np.mean([r.get('time_spent', 2) for r in domain_responses])
                domain_stats[main_domain] = {
                    'accuracy': domain_accuracy,
                    'avg_time': domain_time,
                    'question_count': len(domain_responses)
                }
        
        # 1분 미만 풀이 패턴 분석
        time_analysis_str = ""
        if total_time < 60:
            time_analysis_str = f"""
⚠️  **매우 빠른 응답 패턴 감지** ⚠️
- 총 소요시간: {total_time:.0f}초 (1분 미만)
- 문항당 평균: {avg_response_time:.1f}초
- 정상 풀이시간: 문항당 60-120초

이는 다음을 시사합니다:
1. 문제를 충분히 읽지 않고 추측으로 답함
2. 물리치료학 기초 지식이 매우 부족함  
3. 학습에 대한 진지한 접근이 부족함
4. 체계적 학습이 시급히 필요함
"""
        elif avg_response_time < 30:
            time_analysis_str = f"""
⚠️ **성급한 응답 패턴**
- 문항당 평균: {avg_response_time:.1f}초
- 권장 시간: 60-120초/문항

빠른 추측보다는 신중한 사고가 필요합니다.
"""
        
        # 학습 패턴 정보
        learning_style = pattern_analysis.get('learning_style', {})
        cognitive_metrics = pattern_analysis.get('cognitive_metrics', {})
        time_analysis = pattern_analysis.get('time_analysis', {})
        
        # 분석 요청 작성
        analysis_request = f"""
물리치료학과 진단테스트 심층 분석 요청

## 📊 기본 성과 정보
- 총 문항: {total_questions}개 (근골격계 11문항, 신경계 8문항, 심폐 2문항, 기타 9문항)
- 정답: {correct_answers}개 
- 정답률: {accuracy_rate:.1%}
- 총 소요시간: {total_time:.0f}초

{time_analysis_str}

## 🎯 도메인별 성과 분석 (진단테스트 실제 구성)
"""
        
        for domain, stats in domain_stats.items():
            expected_questions = {'근골격계': 11, '신경계': 8, '심폐계': 2, '기타/기초의학': 9}.get(domain, 0)
            analysis_request += f"""
### {domain} 영역 (전체 {expected_questions}문항 중 {stats['question_count']}문항 응답)
- 정답률: {stats['accuracy']:.1%}
- 평균 소요시간: {stats['avg_time']:.0f}초
- 예상 수준: {'기초 부족' if stats['accuracy'] < 0.6 else '보통' if stats['accuracy'] < 0.8 else '양호'}
"""
        
        analysis_request += f"""
## 🧠 AI 학습 패턴 분석
- 응답 스타일: {learning_style.get('response_style', '알 수 없음')}
- 인지 부하: {cognitive_metrics.get('cognitive_load', 0):.1%}
- 주의력 수준: {cognitive_metrics.get('attention_level', 0):.1%}
- 시간 일관성: {time_analysis.get('time_consistency', 0):.1%}
- 시간 트렌드: {time_analysis.get('time_trend', '알 수 없음')}
- 피로도 감지: {'예' if time_analysis.get('fatigue_detected', False) else '아니오'}

## 🔍 DKT 모델 예측 (Deep Knowledge Tracing)
전체 학습 상태: {dkt_analysis.get('knowledge_state', {}).get('overall_mastery', 0):.1%}
개념별 숙련도:
"""
        
        concept_mastery = dkt_analysis.get('concept_mastery', {})
        domain_name_mapping = {
            'anatomy': '해부학 (근골격계)',
            'physiology': '생리학 (기초의학)', 
            'kinesiology': '운동학 (근골격계)',
            'therapy': '치료학 (임상)',
            'assessment': '평가학 (임상)'
        }
        
        for domain_en, score in concept_mastery.items():
            domain_display = domain_name_mapping.get(domain_en, domain_en)
            analysis_request += f"- {domain_display}: {score:.1%}\n"
        
        analysis_request += f"""
## 🚨 주요 우려사항
{"- **극도로 빠른 풀이**: 1분 미만은 추측/찍기를 의미하며 정확한 실력 진단이 어려움" if total_time < 60 else ""}
{"- **기초 의학 지식 부족**: 물리치료사 국가고시 수준의 기본기가 부족함" if accuracy_rate < 0.6 else ""}
- **체계적 학습 필요**: 무작정 문제 풀이보다는 개념 정리가 우선

## 📋 분석 요청사항 (물리치료학과 전문가 관점)
1. **정확한 실력 진단**: 빠른 풀이로 인한 신뢰도 문제 지적
2. **도메인별 약점 분석**: 근골격계, 신경계, 기초의학 각 영역의 구체적 문제점
3. **학습 방향성 제시**: 물리치료사 국가고시 준비를 위한 단계별 학습 계획
4. **기초 지식 보강 방안**: 해부학, 생리학, 병리학 등 기초 의학 학습법
5. **문제 풀이 태도 개선**: 신중하고 체계적인 접근법 제안
6. **동기부여 방안**: 물리치료사라는 목표를 위한 학습 동기 강화 방법

물리치료학과 학생의 관점에서 **실무에 필요한 핵심 역량**과 **국가고시 합격**을 목표로 한 
구체적이고 실용적인 분석과 조언을 한국어로 제공해주세요.
"""
        
        return analysis_request
    
    def _extract_insights_from_deepseek(self, content: str) -> Dict[str, Any]:
        """DeepSeek 응답에서 인사이트 추출"""
        
        insights = {
            'key_findings': [],
            'strength_areas': [],
            'improvement_areas': [],
            'learning_characteristics': []
        }
        
        # 간단한 키워드 기반 추출 (실제로는 더 정교한 NLP 필요)
        lines = content.split('\n')
        
        for line in lines:
            line = line.strip()
            if '강점' in line or '우수' in line:
                insights['strength_areas'].append(line)
            elif '약점' in line or '보완' in line or '개선' in line:
                insights['improvement_areas'].append(line)
            elif '특성' in line or '성향' in line:
                insights['learning_characteristics'].append(line)
            elif line and len(line) > 10:
                insights['key_findings'].append(line)
        
        return insights
    
    def _extract_recommendations_from_deepseek(self, content: str) -> List[str]:
        """DeepSeek 응답에서 추천사항 추출"""
        
        recommendations = []
        lines = content.split('\n')
        
        for line in lines:
            line = line.strip()
            if any(keyword in line for keyword in ['추천', '제안', '권장', '방법', '전략']):
                if len(line) > 5:
                    recommendations.append(line)
        
        # 기본 추천사항이 없으면 일반적인 것 추가
        if not recommendations:
            recommendations = [
                "지속적인 학습을 통해 약점 영역을 보강하세요",
                "강점 영역을 활용하여 자신감을 기르세요",
                "규칙적인 복습 스케줄을 만들어 실천하세요"
            ]
        
        return recommendations[:5]  # 최대 5개
    
    def _generate_local_analysis(
        self, 
        dkt_analysis: Dict[str, Any], 
        pattern_analysis: Dict[str, Any]
    ) -> Dict[str, Any]:
        """로컬 분석 결과 생성 (DeepSeek 실패시 대안)"""
        
        # DKT 기반 인사이트
        concept_mastery = dkt_analysis.get('concept_mastery', {})
        if concept_mastery:
            strongest_domain = max(concept_mastery.items(), key=lambda x: x[1])[0]
            weakest_domain = min(concept_mastery.items(), key=lambda x: x[1])[0]
        else:
            strongest_domain, weakest_domain = 'anatomy', 'physiology'
        
        # 도메인 이름 변환
        domain_names = {v: k for k, v in self.domain_mapping.items()}
        strongest_kr = domain_names.get(strongest_domain, '해부학')
        weakest_kr = domain_names.get(weakest_domain, '생리학')
        
        # 학습 패턴 기반 인사이트
        learning_style = pattern_analysis.get('learning_style', {}).get('response_style', '균형형')
        cognitive_load = pattern_analysis.get('cognitive_metrics', {}).get('cognitive_load', 0.5)
        
        # 분석 요약 생성
        analysis_summary = f"""
## AI 모델 기반 학습 분석 결과

**강점 영역**: {strongest_kr} 
- 이 영역에서 우수한 성과를 보이고 있습니다.

**개선 영역**: {weakest_kr}
- 추가적인 학습과 복습이 필요한 영역입니다.

**학습 특성**:
- 응답 스타일: {learning_style}
- 인지 부하 수준: {'높음' if cognitive_load > 0.7 else '적절함'}

**종합 평가**:
전반적으로 물리치료학 기초 지식을 갖추고 있으나, 
균형잡힌 발전을 위해 약점 영역의 보강이 필요합니다.
"""
        
        # 추천사항 생성
        recommendations = [
            f"{strongest_kr} 영역의 강점을 활용하여 다른 영역 학습에 연계하세요",
            f"{weakest_kr} 영역의 기초 개념부터 차근차근 복습하세요",
            f"{learning_style} 특성에 맞는 학습 방법을 지속적으로 활용하세요"
        ]
        
        if cognitive_load > 0.7:
            recommendations.append("현재 인지 부하가 높으므로 적절한 휴식을 취하세요")
        else:
            recommendations.append("현재 컨디션이 좋으니 집중적인 학습을 진행하세요")
        
        return {
            'status': 'local_analysis',
            'analysis_summary': analysis_summary.strip(),
            'insights': {
                'strongest_domain': strongest_kr,
                'weakest_domain': weakest_kr,
                'learning_style': learning_style,
                'cognitive_status': '높은 부하' if cognitive_load > 0.7 else '적절한 상태'
            },
            'recommendations': recommendations,
            'generated_at': datetime.now().isoformat(),
            'source': 'local_ai_models'
        }
    
    def _integrate_ai_analyses(
        self,
        dkt_analysis: Dict[str, Any],
        pattern_analysis: Dict[str, Any],
        deepseek_analysis: Dict[str, Any]
    ) -> Dict[str, Any]:
        """AI 분석 결과 통합"""
        
        return {
            'dkt_insights': dkt_analysis,
            'learning_patterns': pattern_analysis,
            'deepseek_analysis': deepseek_analysis,
            'integration_metadata': {
                'analysis_timestamp': datetime.now().isoformat(),
                'models_used': ['DKT', 'LSTM', 'RNN', 'DeepSeek'],
                'confidence_score': self._calculate_integration_confidence(
                    dkt_analysis, pattern_analysis, deepseek_analysis
                )
            }
        }
    
    def _calculate_integration_confidence(
        self,
        dkt_analysis: Dict[str, Any],
        pattern_analysis: Dict[str, Any],
        deepseek_analysis: Dict[str, Any]
    ) -> float:
        """통합 분석 신뢰도 계산"""
        
        confidence_factors = []
        
        # DKT 신뢰도
        dkt_confidence = dkt_analysis.get('knowledge_state', {}).get('confidence_score')
        if dkt_confidence:
            confidence_factors.append(dkt_confidence)
        
        # 패턴 분석 신뢰도
        pattern_confidence = pattern_analysis.get('learning_style', {}).get('style_confidence')
        if pattern_confidence:
            confidence_factors.append(pattern_confidence)
        
        # DeepSeek 분석 성공 여부
        if deepseek_analysis.get('status') == 'success':
            confidence_factors.append(0.9)
        else:
            confidence_factors.append(0.6)
        
        return float(np.mean(confidence_factors)) if confidence_factors else 0.7
    
    def _get_default_dkt_analysis(self) -> Dict[str, Any]:
        """기본 DKT 분석 (데이터 부족시)"""
        
        return {
            'concept_mastery': {
                'anatomy': 0.7,
                'physiology': 0.6,
                'kinesiology': 0.75,
                'therapy': 0.65,
                'assessment': 0.7
            },
            'learning_progress': {
                'overall_progress': 0.65,
                'improvement_rate': 0.1,
                'domain_progress': {}
            },
            'knowledge_state': {
                'overall_mastery': 0.68,
                'confidence_score': 0.6,
                'difficulty_prediction': 0.4,
                'time_estimation': 55.0
            }
        }
    
    def _get_statistical_analysis(self, responses: List[Dict]) -> Dict[str, Any]:
        """통계적 분석 (AI 모델 없이)"""
        
        if not responses:
            return self._get_fallback_analysis([])
        
        # 기본 통계
        total = len(responses)
        correct = sum(r.get('is_correct', False) for r in responses)
        accuracy = correct / total
        avg_time = np.mean([r.get('time_spent', 60) for r in responses])
        
        # 도메인별 분석
        domain_stats = {}
        for domain_kr in self.domain_mapping.keys():
            domain_responses = [r for r in responses if r.get('domain') == domain_kr]
            if domain_responses:
                domain_accuracy = sum(r.get('is_correct', False) for r in domain_responses) / len(domain_responses)
                domain_time = np.mean([r.get('time_spent', 60) for r in domain_responses])
                domain_stats[domain_kr] = {
                    'accuracy': domain_accuracy,
                    'avg_time': domain_time,
                    'question_count': len(domain_responses)
                }
        
        # 최고/최저 도메인
        if domain_stats:
            best_domain = max(domain_stats.items(), key=lambda x: x[1]['accuracy'])[0]
            worst_domain = min(domain_stats.items(), key=lambda x: x[1]['accuracy'])[0]
        else:
            best_domain, worst_domain = '해부학', '생리학'
        
        return {
            'dkt_insights': {
                'concept_mastery': {self.domain_mapping.get(k, k): v['accuracy'] for k, v in domain_stats.items()},
                'knowledge_state': {
                    'overall_mastery': accuracy,
                    'confidence_score': 0.7
                }
            },
            'learning_patterns': {
                'learning_style': {'response_style': '균형형'},
                'time_analysis': {
                    'average_response_time': avg_time,
                    'time_consistency': 0.7,
                    'time_trend': '일관됨',
                    'fatigue_detected': False
                }
            },
            'deepseek_analysis': {
                'status': 'statistical',
                'analysis_summary': f"""
## 통계적 분석 결과

**전체 성과**: 총 {total}문항 중 {correct}문항 정답 (정답률 {accuracy:.1%})
**평균 소요시간**: {avg_time:.0f}초

**도메인별 성과**:
- 최고 성과: {best_domain} ({domain_stats.get(best_domain, {}).get('accuracy', 0):.1%})
- 개선 필요: {worst_domain} ({domain_stats.get(worst_domain, {}).get('accuracy', 0):.1%})

**학습 분석**: AI 모델을 활용한 더 정확한 분석이 가능합니다.
""",
                'recommendations': [
                    f"{best_domain} 영역의 강점을 유지하세요",
                    f"{worst_domain} 영역의 추가 학습이 필요합니다",
                    "정기적인 복습을 통해 전체적인 균형을 맞추세요"
                ]
            },
            'integration_metadata': {
                'analysis_timestamp': datetime.now().isoformat(),
                'models_used': ['statistical'],
                'confidence_score': 0.5
            }
        }
    
    def _get_fallback_analysis(self, responses: List[Dict]) -> Dict[str, Any]:
        """대안 분석 (모든 것이 실패했을 때)"""
        
        total = len(responses) if responses else 0
        correct = sum(r.get('is_correct', False) for r in responses) if responses else 0
        accuracy = correct / total if total > 0 else 0.5
        
        return {
            'dkt_insights': self._get_default_dkt_analysis(),
            'learning_patterns': {
                'learning_style': {'response_style': '균형형'},
                'time_analysis': {
                    'average_response_time': 56.0,
                    'time_consistency': 0.7,
                    'time_trend': '일관됨',
                    'fatigue_detected': False
                }
            },
            'deepseek_analysis': {
                'status': 'fallback',
                'analysis_summary': f"기본 분석: 총 {total}문항 중 {correct}문항 정답 (정답률 {accuracy:.1%})",
                'recommendations': [
                    "더 많은 문제를 풀어 정확한 분석을 받아보세요",
                    "지속적인 학습을 통해 실력을 향상시키세요"
                ]
            },
            'integration_metadata': {
                'analysis_timestamp': datetime.now().isoformat(),
                'models_used': ['fallback'],
                'confidence_score': 0.3
            }
        }
    
    def _load_models(self):
        """AI 모델들 로드"""
        try:
            if self.dkt_trainer:
                self.dkt_trainer.load_model(f"{self.model_dir}/dkt_model.pth")
                logger.info("DKT 모델 로드 시도 완료")
        except Exception as e:
            logger.warning(f"AI 모델 로드 실패: {e}")

# 싱글톤 인스턴스
knowledge_tracer = KnowledgeTracer() 