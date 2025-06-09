"""
통합 파싱 및 매핑 시스템
실제 문제지/답안지 + 교수님들의 평가 데이터 매핑하여 완전한 데이터셋 생성
"""
import os
import json
import logging
import asyncio
from typing import Dict, List, Any, Optional, Tuple
from pathlib import Path
from datetime import datetime
import re

from app.services.question_parser import QuestionParser
from app.services.difficulty_domain_mapper import difficulty_domain_mapper

logger = logging.getLogger(__name__)

class IntegratedParserMapper:
    """
    통합 파싱 및 매핑 시스템
    
    기능:
    1. uploads/questions 폴더의 실제 문제지/답안지 파싱
    2. data/평가위원 수행결과의 교수님 평가 데이터와 매핑
    3. 완전한 통합 데이터셋을 data/save_parser에 저장
    """
    
    def __init__(self):
        # API 키 직접 전달하여 파서 초기화
        gemini_api_key = "AIzaSyAU_5m68cNAMIBn7m1uQPrYKNFR0oPO3QA"
        self.parser = QuestionParser(api_key=gemini_api_key)
        self.questions_dir = Path("uploads/questions")
        self.evaluation_dir = Path("data/평가위원 수행결과")
        self.output_dir = Path("data/save_parser")
        
        # 출력 디렉토리 생성
        self.output_dir.mkdir(exist_ok=True, parents=True)
    
    async def process_all_files(self) -> Dict[str, Any]:
        """
        모든 파일을 처리하고 통합 데이터셋 생성
        
        Returns:
            처리 결과 요약
        """
        
        logger.info("🚀 통합 파싱 및 매핑 시스템 시작")
        logger.info("="*80)
        
        try:
            # 1. 업로드된 파일들 분석
            logger.info("📂 1단계: 업로드된 파일들 분석")
            file_groups = await self._analyze_uploaded_files()
            
            # 2. 교수님 평가 데이터 로드
            logger.info("🎓 2단계: 교수님 평가 데이터 로드")
            await difficulty_domain_mapper.load_professor_evaluation_data()
            
            # 3. 각 연도/학과별 파일 처리
            logger.info("⚙️ 3단계: 파일별 파싱 및 매핑")
            integrated_datasets = {}
            
            for key, files in file_groups.items():
                logger.info(f"📊 {key} 처리 중...")
                dataset = await self._process_file_group(key, files)
                if dataset:
                    integrated_datasets[key] = dataset
            
            # 4. 통합 데이터셋 저장
            logger.info("💾 4단계: 통합 데이터셋 저장")
            saved_files = await self._save_integrated_datasets(integrated_datasets)
            
            # 5. 결과 요약
            summary = self._generate_summary(integrated_datasets, saved_files)
            
            logger.info("="*80)
            logger.info("✅ 통합 파싱 및 매핑 시스템 완료!")
            
            return summary
            
        except Exception as e:
            logger.error(f"❌ 통합 파싱 및 매핑 실패: {e}")
            import traceback
            traceback.print_exc()
            raise
    
    async def _analyze_uploaded_files(self) -> Dict[str, Dict[str, Path]]:
        """
        업로드된 파일들을 연도/학과별로 그룹화
        
        Returns:
            파일 그룹 딕셔너리
        """
        
        file_groups = {}
        
        if not self.questions_dir.exists():
            logger.error(f"❌ 문제 디렉토리가 없습니다: {self.questions_dir}")
            return file_groups
        
        # 파일 패턴 분석
        for file_path in self.questions_dir.iterdir():
            if file_path.is_file() and file_path.suffix.lower() == '.pdf':
                # 숨김 파일 제외
                if file_path.name.startswith('._'):
                    continue
                
                # 파일명에서 정보 추출
                info = self._extract_file_info(file_path.name)
                if info:
                    year, department, file_type = info
                    key = f"{year}_{department}"
                    
                    if key not in file_groups:
                        file_groups[key] = {}
                    
                    file_groups[key][file_type] = file_path
                    
                    logger.info(f"   📄 {file_path.name}")
                    logger.info(f"      → {year}년 {department} {file_type}")
        
        logger.info(f"📊 총 {len(file_groups)}개 그룹 발견:")
        for key, files in file_groups.items():
            logger.info(f"   {key}: {list(files.keys())}")
        
        return file_groups
    
    def _extract_file_info(self, filename: str) -> Optional[Tuple[str, str, str]]:
        """
        파일명에서 연도, 학과, 파일 타입 추출
        
        Args:
            filename: 파일명
            
        Returns:
            (연도, 학과, 파일타입) 또는 None
        """
        
        # 연도 추출
        year_match = re.search(r'(20\d{2})', filename)
        if not year_match:
            return None
        year = year_match.group(1)
        
        # 학과 추출
        if '물리치료사' in filename:
            department = '물리치료학과'
        elif '작업치료사' in filename:
            department = '작업치료학과'
        else:
            return None
        
        # 파일 타입 추출
        if '기출문제' in filename or '1교시' in filename:
            file_type = 'questions'
        elif '답안' in filename or '가답안' in filename:
            file_type = 'answers'
        else:
            return None
        
        return year, department, file_type
    
    async def _process_file_group(self, group_key: str, files: Dict[str, Path]) -> Optional[Dict[str, Any]]:
        """
        파일 그룹 처리 (문제지 + 답안지 + 평가 데이터)
        
        Args:
            group_key: 그룹 키 (예: "2024_물리치료학과")
            files: 파일 딕셔너리
            
        Returns:
            통합 데이터셋
        """
        
        try:
            year, department = group_key.split('_')
            
            # 문제지와 답안지가 모두 있는지 확인
            if 'questions' not in files or 'answers' not in files:
                logger.warning(f"⚠️ {group_key}: 문제지 또는 답안지 누락")
                logger.warning(f"   보유 파일: {list(files.keys())}")
                return None
            
            questions_file = files['questions']
            answers_file = files['answers']
            
            logger.info(f"   📖 문제지 파싱: {questions_file.name}")
            
            # 문제지 파싱
            questions_result = await self.parser.parse_any_file(
                str(questions_file), 
                "questions", 
                department
            )
            
            if questions_result.get("error"):
                logger.error(f"   ❌ 문제지 파싱 실패: {questions_result['error']}")
                return None
            
            questions_data = questions_result.get("data", [])
            logger.info(f"   ✅ {len(questions_data)}개 문제 파싱 완료")
            
            logger.info(f"   📝 답안지 파싱: {answers_file.name}")
            
            # 답안지 파싱
            answers_result = await self.parser.parse_any_file(
                str(answers_file), 
                "answers", 
                department
            )
            
            if answers_result.get("error"):
                logger.error(f"   ❌ 답안지 파싱 실패: {answers_result['error']}")
                return None
            
            answers_data = answers_result.get("data", [])
            logger.info(f"   ✅ {len(answers_data)}개 답안 파싱 완료")
            
            # 문제와 답안 매칭
            logger.info(f"   🔗 문제-답안 매칭 중...")
            matched_data = self._match_questions_and_answers(questions_data, answers_data)
            logger.info(f"   ✅ {len(matched_data)}개 문제-답안 매칭 완료")
            
            # 교수님 평가 데이터와 매핑
            logger.info(f"   🎯 교수님 평가 데이터 매핑 중...")
            enhanced_data = await self._apply_professor_evaluations(matched_data, year, department)
            logger.info(f"   ✅ 교수님 평가 데이터 매핑 완료")
            
            # 메타데이터 추가
            dataset = {
                "metadata": {
                    "year": year,
                    "department": department,
                    "questions_file": questions_file.name,
                    "answers_file": answers_file.name,
                    "processed_at": datetime.now().isoformat(),
                    "total_questions": len(enhanced_data)
                },
                "questions": enhanced_data
            }
            
            return dataset
            
        except Exception as e:
            logger.error(f"❌ {group_key} 파일 그룹 처리 실패: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    def _match_questions_and_answers(self, questions_data: List[Dict], answers_data: List[Dict]) -> List[Dict]:
        """
        문제와 답안 매칭
        
        Args:
            questions_data: 파싱된 문제 데이터
            answers_data: 파싱된 답안 데이터
            
        Returns:
            매칭된 데이터
        """
        
        matched_data = []
        
        # 답안을 문제 번호별로 인덱싱
        answers_by_number = {}
        for answer in answers_data:
            q_num = answer.get('question_number')
            if q_num:
                answers_by_number[q_num] = answer
        
        # 문제와 답안 매칭
        for question in questions_data:
            q_num = question.get('question_number')
            if q_num and q_num in answers_by_number:
                answer = answers_by_number[q_num]
                
                # 문제 데이터에 답안 정보 병합
                merged = {**question}  # 문제 데이터 복사
                
                # 답안 정보 추가
                merged['correct_answer'] = answer.get('correct_answer', '')
                
                # 답안지에서 추가 정보가 있으면 병합
                if answer.get('subject'):
                    merged['subject'] = answer['subject']
                if answer.get('area_name'):
                    merged['area_name'] = answer['area_name']
                if answer.get('difficulty'):
                    merged['difficulty'] = answer['difficulty']
                
                matched_data.append(merged)
            else:
                # 답안이 없는 문제도 포함
                matched_data.append(question)
        
        return matched_data
    
    async def _apply_professor_evaluations(self, matched_data: List[Dict], year: str, department: str) -> List[Dict]:
        """
        교수님 평가 데이터 적용
        
        Args:
            matched_data: 매칭된 문제-답안 데이터
            year: 연도
            department: 학과
            
        Returns:
            교수님 평가가 적용된 데이터
        """
        
        enhanced_data = []
        
        for question in matched_data:
            try:
                # 기본 데이터 복사
                enhanced = {**question}
                
                # 문제 내용이 있는 경우에만 AI 예측 적용
                question_content = question.get('content', '')
                if question_content and len(question_content) > 10:
                    
                    # AI 기반 난이도/분야 예측
                    prediction = await difficulty_domain_mapper.predict_difficulty_and_domain(
                        question_content, department
                    )
                    
                    # 기존 데이터가 없거나 기본값인 경우 AI 예측 적용
                    if not enhanced.get('difficulty') or enhanced.get('difficulty') in ['', '중', None]:
                        enhanced['difficulty'] = prediction.get('difficulty', '중')
                        enhanced['ai_difficulty_applied'] = True
                        enhanced['ai_difficulty_confidence'] = prediction.get('confidence', 0.7)
                    
                    if not enhanced.get('area_name') or enhanced.get('area_name') in ['', '일반', None]:
                        enhanced['area_name'] = prediction.get('domain', '일반')
                        enhanced['ai_domain_applied'] = True
                        enhanced['ai_domain_confidence'] = prediction.get('confidence', 0.7)
                    
                    # AI 분석 정보 추가
                    enhanced['ai_analysis'] = {
                        'reasoning': prediction.get('reasoning', 'AI 자동 분석'),
                        'department': department,
                        'year': year,
                        'mapped_at': datetime.now().isoformat()
                    }
                
                # 교수님 평가 데이터 매핑
                professor_evaluations = await self._get_professor_evaluations_for_question(
                    question, year, department
                )
                if professor_evaluations:
                    enhanced['professor_evaluations'] = professor_evaluations
                
                enhanced_data.append(enhanced)
                
            except Exception as e:
                logger.warning(f"⚠️ 문제 {question.get('question_number', '?')} 평가 매핑 실패: {e}")
                enhanced_data.append(question)  # 원본 데이터 유지
                continue
        
        return enhanced_data
    
    async def _get_professor_evaluations_for_question(self, question: Dict, year: str, department: str) -> Optional[List[Dict]]:
        """
        특정 문제에 대한 교수님 평가 데이터 조회
        
        Args:
            question: 문제 데이터
            year: 연도
            department: 학과
            
        Returns:
            교수님 평가 데이터 리스트
        """
        
        try:
            # 학습된 교수님 평가 데이터에서 해당 문제 번호의 평가 찾기
            question_number = question.get('question_number')
            if not question_number:
                return None
            
            # difficulty_domain_mapper의 학습 데이터에서 해당 문제 평가 찾기
            training_data = difficulty_domain_mapper.training_data.get(department, {})
            professor_evaluations = training_data.get('professor_evaluations', {})
            
            evaluations = []
            for professor, prof_data in professor_evaluations.items():
                for eval_question in prof_data:
                    if eval_question.get('question_number') == question_number:
                        evaluations.append({
                            'professor': professor,
                            'difficulty': eval_question.get('difficulty'),
                            'domain': eval_question.get('domain'),
                            'year': year
                        })
            
            return evaluations if evaluations else None
            
        except Exception as e:
            logger.warning(f"⚠️ 교수님 평가 데이터 조회 실패: {e}")
            return None
    
    async def _save_integrated_datasets(self, datasets: Dict[str, Dict]) -> List[str]:
        """
        통합 데이터셋들을 JSON 파일로 저장
        
        Args:
            datasets: 통합 데이터셋들
            
        Returns:
            저장된 파일 목록
        """
        
        saved_files = []
        
        for key, dataset in datasets.items():
            try:
                # 파일명 생성
                filename = f"integrated_{key}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
                filepath = self.output_dir / filename
                
                # JSON으로 저장
                with open(filepath, 'w', encoding='utf-8') as f:
                    json.dump(dataset, f, ensure_ascii=False, indent=2)
                
                saved_files.append(str(filepath))
                logger.info(f"   💾 저장됨: {filename}")
                logger.info(f"      📊 총 {dataset['metadata']['total_questions']}개 문제")
                
            except Exception as e:
                logger.error(f"❌ {key} 데이터셋 저장 실패: {e}")
                continue
        
        return saved_files
    
    def _generate_summary(self, datasets: Dict[str, Dict], saved_files: List[str]) -> Dict[str, Any]:
        """
        처리 결과 요약 생성
        
        Args:
            datasets: 처리된 데이터셋들
            saved_files: 저장된 파일 목록
            
        Returns:
            요약 정보
        """
        
        total_questions = sum(dataset['metadata']['total_questions'] for dataset in datasets.values())
        
        summary = {
            'success': True,
            'processed_datasets': len(datasets),
            'total_questions': total_questions,
            'saved_files': saved_files,
            'datasets_summary': {}
        }
        
        for key, dataset in datasets.items():
            metadata = dataset['metadata']
            summary['datasets_summary'][key] = {
                'year': metadata['year'],
                'department': metadata['department'],
                'total_questions': metadata['total_questions'],
                'questions_file': metadata['questions_file'],
                'answers_file': metadata['answers_file']
            }
        
        return summary

# 전역 인스턴스
integrated_parser_mapper = IntegratedParserMapper() 