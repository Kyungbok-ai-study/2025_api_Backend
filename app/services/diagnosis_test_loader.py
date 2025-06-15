"""
학과별 진단테스트 JSON 파일 로더 서비스
"""
import json
import os
from typing import Dict, List, Optional, Any
from pathlib import Path

from app.models.enums import DiagnosisSubject, DEPARTMENT_TEST_FILE_MAPPING


class DiagnosisTestLoader:
    """학과별 진단테스트 파일을 로드하는 서비스"""
    
    def __init__(self, data_directory: str = "data"):
        self.data_directory = Path(data_directory)
        self._cache: Dict[str, Dict] = {}
    
    def get_test_file_path(self, subject: DiagnosisSubject) -> Path:
        """학과에 해당하는 진단테스트 파일 경로를 반환"""
        relative_path = DEPARTMENT_TEST_FILE_MAPPING.get(subject)
        if not relative_path:
            raise ValueError(f"No test file mapping found for subject: {subject}")
        
        return self.data_directory / relative_path
    
    def load_test_data(self, subject: DiagnosisSubject, use_cache: bool = True) -> Dict[str, Any]:
        """진단테스트 데이터를 로드"""
        file_path = self.get_test_file_path(subject)
        cache_key = str(file_path)
        
        # 캐시에서 확인
        if use_cache and cache_key in self._cache:
            return self._cache[cache_key]
        
        # 파일 존재 확인
        if not file_path.exists():
            raise FileNotFoundError(f"Test file not found: {file_path}")
        
        # JSON 파일 로드
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # 캐시에 저장
            if use_cache:
                self._cache[cache_key] = data
            
            return data
            
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON format in file {file_path}: {e}")
        except Exception as e:
            raise Exception(f"Error loading test file {file_path}: {e}")
    
    def get_questions(self, subject: DiagnosisSubject, limit: Optional[int] = None) -> List[Dict]:
        """특정 학과의 문제들을 반환"""
        test_data = self.load_test_data(subject)
        questions = test_data.get('questions', [])
        
        if limit:
            questions = questions[:limit]
        
        return questions
    
    def get_test_info(self, subject: DiagnosisSubject) -> Dict[str, Any]:
        """테스트 기본 정보를 반환"""
        test_data = self.load_test_data(subject)
        return test_data.get('test_info', {})
    
    def get_scoring_criteria(self, subject: DiagnosisSubject) -> Dict[str, Any]:
        """채점 기준을 반환"""
        test_data = self.load_test_data(subject)
        return test_data.get('scoring_criteria', {})
    
    def get_statistics(self, subject: DiagnosisSubject) -> Dict[str, Any]:
        """테스트 통계를 반환"""
        test_data = self.load_test_data(subject)
        return test_data.get('statistics', {})
    
    def list_available_subjects(self) -> List[DiagnosisSubject]:
        """사용 가능한 진단테스트 과목 목록을 반환"""
        available_subjects = []
        
        for subject in DiagnosisSubject:
            try:
                file_path = self.get_test_file_path(subject)
                if file_path.exists():
                    available_subjects.append(subject)
            except ValueError:
                continue
        
        return available_subjects
    
    def validate_test_files(self) -> Dict[str, Any]:
        """모든 테스트 파일의 유효성을 검사"""
        validation_results = {
            'valid_files': [],
            'invalid_files': [],
            'missing_files': [],
            'errors': []
        }
        
        for subject in DiagnosisSubject:
            try:
                file_path = self.get_test_file_path(subject)
                
                if not file_path.exists():
                    validation_results['missing_files'].append({
                        'subject': subject.value,
                        'file_path': str(file_path)
                    })
                    continue
                
                # JSON 구조 검증
                test_data = self.load_test_data(subject, use_cache=False)
                
                # 필수 필드 확인
                required_fields = ['test_info', 'scoring_criteria', 'questions']
                missing_fields = [field for field in required_fields 
                                if field not in test_data]
                
                if missing_fields:
                    validation_results['invalid_files'].append({
                        'subject': subject.value,
                        'file_path': str(file_path),
                        'missing_fields': missing_fields
                    })
                else:
                    validation_results['valid_files'].append({
                        'subject': subject.value,
                        'file_path': str(file_path),
                        'question_count': len(test_data.get('questions', []))
                    })
                    
            except Exception as e:
                validation_results['errors'].append({
                    'subject': subject.value,
                    'error': str(e)
                })
        
        return validation_results
    
    def clear_cache(self):
        """캐시를 초기화"""
        self._cache.clear()
    
    def reload_test_data(self, subject: DiagnosisSubject) -> Dict[str, Any]:
        """특정 과목의 테스트 데이터를 다시 로드"""
        # 캐시에서 제거
        file_path = self.get_test_file_path(subject)
        cache_key = str(file_path)
        if cache_key in self._cache:
            del self._cache[cache_key]
        
        # 다시 로드
        return self.load_test_data(subject, use_cache=True)


# 전역 인스턴스
diagnosis_test_loader = DiagnosisTestLoader() 