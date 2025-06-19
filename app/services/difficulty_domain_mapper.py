"""
난이도 및 분야 자동 매핑 시스템
교수님들의 평가 데이터를 학습하여 새로운 문제의 난이도와 분야를 자동 분류
"""
import os
import json
import pandas as pd
import logging
from typing import Dict, List, Tuple, Optional
from pathlib import Path
from datetime import datetime
import asyncio
import google.generativeai as genai
from openai import AsyncOpenAI

logger = logging.getLogger(__name__)

class DifficultyDomainMapper:
    """
    난이도 및 분야 자동 매핑 시스템
    
    기능:
    1. 교수님들의 평가 데이터 학습
    2. 새로운 문제의 난이도/분야 자동 분류
    3. 학과별 특성화된 분류 모델
    4. 상용화를 위한 동적 확장 지원
    """
    
    def __init__(self):
        self.training_data = {}  # 학과별 학습 데이터
        self.domain_keywords = {}  # 학과별 분야 키워드
        self.difficulty_patterns = {}  # 학과별 난이도 패턴
        self.professor_weights = {}  # 교수별 가중치
        
        # API 클라이언트 초기화
        self.openai_client = None
        self.gemini_model = None
        self._init_ai_clients()
    
    def _init_ai_clients(self):
        """AI 클라이언트 초기화"""
        try:
            # OpenAI 클라이언트
            openai_api_key = os.getenv("OPENAI_API_KEY")
            if openai_api_key:
                self.openai_client = AsyncOpenAI(api_key=openai_api_key)
            
            # Gemini 클라이언트
            gemini_api_key = os.getenv("GEMINI_API_KEY")
            if gemini_api_key:
                genai.configure(api_key=gemini_api_key)
                self.gemini_model = genai.GenerativeModel('gemini-pro')
                
        except Exception as e:
            logger.error(f"AI 클라이언트 초기화 실패: {e}")
    
    async def load_professor_evaluation_data(self, data_path: str = "data/평가위원 수행결과"):
        """
        교수님들의 평가 데이터 로드 및 학습
        
        Args:
            data_path: 평가 데이터 경로
        """
        logger.info("🎓 교수님들의 평가 데이터 학습 시작")
        
        try:
            base_path = Path(data_path)
            
            # 학과별 데이터 처리
            for department_dir in base_path.iterdir():
                if department_dir.is_dir():
                    department = self._extract_department_name(department_dir.name)
                    logger.info(f"📚 {department} 학과 데이터 처리 중...")
                    
                    await self._process_department_data(department, department_dir)
            
            # 학습 데이터 통합 및 패턴 분석
            await self._analyze_patterns()
            
            # 학습 결과 저장
            await self._save_training_results()
            
            logger.info("✅ 교수님들의 평가 데이터 학습 완료")
            
        except Exception as e:
            logger.error(f"❌ 평가 데이터 학습 실패: {e}")
            raise
    
    def _extract_department_name(self, dir_name: str) -> str:
        """디렉토리명에서 학과명 추출"""
        if "작업치료" in dir_name:
            return "작업치료학과"
        elif "물리치료" in dir_name:
            return "물리치료학과"
        else:
            return dir_name.replace("평가위원 수행결과_", "")
    
    async def _process_department_data(self, department: str, department_dir: Path):
        """학과별 데이터 처리"""
        
        department_data = []
        professor_evaluations = {}
        
        # 각 교수님의 엑셀 파일 처리
        for excel_file in department_dir.glob("*.xlsx"):
            professor_name = self._extract_professor_name(excel_file.name)
            logger.info(f"   👨‍🏫 {professor_name} 교수님 데이터 처리 중...")
            
            try:
                # 엑셀 파일 읽기 (pandas 사용)
                df = pd.read_excel(excel_file)
                
                # 데이터 정제 및 구조화
                professor_data = await self._parse_excel_data(df, professor_name)
                professor_evaluations[professor_name] = professor_data
                department_data.extend(professor_data)
                
            except Exception as e:
                logger.warning(f"⚠️ {professor_name} 교수님 데이터 처리 실패: {e}")
                continue
        
        # 학과별 데이터 저장
        self.training_data[department] = {
            "combined_data": department_data,
            "professor_evaluations": professor_evaluations,
            "total_questions": len(department_data)
        }
        
        logger.info(f"✅ {department} 총 {len(department_data)}개 문제 데이터 수집")
    
    def _extract_professor_name(self, filename: str) -> str:
        """파일명에서 교수명 추출"""
        # "2. 신장훈_작치_마스터코딩지.xlsx" -> "신장훈"
        parts = filename.split("_")
        if len(parts) >= 2:
            name_part = parts[0].replace("2. ", "").strip()
            return name_part
        return filename.split(".")[0]
    
    async def _parse_excel_data(self, df: pd.DataFrame, professor_name: str) -> List[Dict]:
        """엑셀 데이터 파싱 및 구조화"""
        
        parsed_data = []
        
        try:
            # 엑셀 구조 분석 (일반적인 컬럼명들)
            possible_columns = {
                "question": ["문제", "문항", "question", "문제내용", "내용"],
                "answer": ["정답", "답", "answer", "correct_answer", "가답안"],
                "difficulty": ["난이도", "difficulty", "수준", "레벨"],
                "domain": ["분야", "영역", "유형", "domain", "category", "분류"]
            }
            
            # 실제 컬럼 매핑
            column_mapping = {}
            for key, candidates in possible_columns.items():
                for col in df.columns:
                    if any(candidate in str(col).lower() for candidate in candidates):
                        column_mapping[key] = col
                        break
            
            logger.info(f"   📊 컬럼 매핑: {column_mapping}")
            
            # 데이터 추출
            for idx, row in df.iterrows():
                try:
                    question_data = {
                        "professor": professor_name,
                        "question_number": idx + 1,
                        "question": str(row.get(column_mapping.get("question", ""), "")).strip(),
                        "answer": str(row.get(column_mapping.get("answer", ""), "")).strip(),
                        "difficulty": str(row.get(column_mapping.get("difficulty", ""), "")).strip(),
                        "domain": str(row.get(column_mapping.get("domain", ""), "")).strip(),
                        "raw_data": row.to_dict()
                    }
                    
                    # 빈 데이터 필터링
                    if question_data["question"] and len(question_data["question"]) > 10:
                        parsed_data.append(question_data)
                        
                except Exception as e:
                    logger.warning(f"⚠️ 행 {idx} 처리 실패: {e}")
                    continue
            
        except Exception as e:
            logger.error(f"❌ 엑셀 데이터 파싱 실패: {e}")
        
        return parsed_data
    
    async def _analyze_patterns(self):
        """학습 데이터 패턴 분석"""
        
        logger.info("🔍 학습 데이터 패턴 분석 시작")
        
        for department, data in self.training_data.items():
            logger.info(f"📊 {department} 패턴 분석 중...")
            
            # 1. 난이도 분포 분석
            difficulty_analysis = await self._analyze_difficulty_patterns(data["combined_data"])
            
            # 2. 분야 키워드 추출
            domain_analysis = await self._extract_domain_keywords(data["combined_data"])
            
            # 3. 교수별 일치도 분석
            consistency_analysis = await self._analyze_professor_consistency(data["professor_evaluations"])
            
            # 결과 저장
            self.difficulty_patterns[department] = difficulty_analysis
            self.domain_keywords[department] = domain_analysis
            self.professor_weights[department] = consistency_analysis
            
            logger.info(f"✅ {department} 패턴 분석 완료")
    
    async def _analyze_difficulty_patterns(self, questions: List[Dict]) -> Dict:
        """난이도 패턴 분석"""
        
        difficulty_patterns = {
            "하": {"keywords": [], "characteristics": []},
            "중": {"keywords": [], "characteristics": []},
            "상": {"keywords": [], "characteristics": []}
        }
        
        # 난이도별 문제 그룹화
        by_difficulty = {}
        for q in questions:
            diff = q.get("difficulty", "").strip()
            if diff in ["하", "중", "상"]:
                if diff not in by_difficulty:
                    by_difficulty[diff] = []
                by_difficulty[diff].append(q["question"])
        
        # AI를 사용한 패턴 분석
        for difficulty, question_list in by_difficulty.items():
            if len(question_list) >= 3:  # 최소 3개 이상의 문제가 있을 때만 분석
                patterns = await self._extract_difficulty_characteristics(question_list, difficulty)
                difficulty_patterns[difficulty] = patterns
        
        return difficulty_patterns
    
    async def _extract_domain_keywords(self, questions: List[Dict]) -> Dict:
        """분야별 키워드 추출"""
        
        domain_keywords = {}
        
        # 분야별 문제 그룹화
        by_domain = {}
        for q in questions:
            domain = q.get("domain", "").strip()
            if domain and domain != "":
                if domain not in by_domain:
                    by_domain[domain] = []
                by_domain[domain].append(q["question"])
        
        # AI를 사용한 키워드 추출
        for domain, question_list in by_domain.items():
            if len(question_list) >= 2:  # 최소 2개 이상의 문제가 있을 때만 분석
                keywords = await self._extract_domain_characteristics(question_list, domain)
                domain_keywords[domain] = keywords
        
        return domain_keywords
    
    async def _analyze_professor_consistency(self, professor_evaluations: Dict) -> Dict:
        """교수별 평가 일치도 분석 및 가중치 계산"""
        
        consistency_scores = {}
        
        # 같은 문제에 대한 교수별 평가 비교 (향후 구현)
        # 현재는 균등 가중치 적용
        for professor in professor_evaluations.keys():
            consistency_scores[professor] = 1.0  # 균등 가중치
        
        return consistency_scores
    
    async def _extract_difficulty_characteristics(self, questions: List[str], difficulty: str) -> Dict:
        """AI를 사용한 난이도별 특성 추출"""
        
        try:
            # 문제들을 하나의 텍스트로 결합
            combined_text = "\n".join(questions[:10])  # 최대 10개 문제만 분석
            
            prompt = f"""
다음은 '{difficulty}' 난이도로 분류된 문제들입니다.
이 문제들의 공통적인 특성과 키워드를 분석해주세요.

문제들:
{combined_text}

분석 결과를 다음 JSON 형식으로 제공해주세요:
{{
    "keywords": ["키워드1", "키워드2", "키워드3"],
    "characteristics": ["특성1", "특성2", "특성3"],
    "complexity_indicators": ["복잡도지표1", "복잡도지표2"]
}}
"""
            
            # Gemini API 호출
            if self.gemini_model:
                response = await self._call_gemini_async(prompt)
                try:
                    # 통합 JSON 파서 사용
                    from app.services.question_parser import QuestionParser
                    result = QuestionParser.parse_ai_json_response(response)
                    if "error" not in result:
                        return result
                except:
                    pass
            
            # 기본값 반환
            return {
                "keywords": [],
                "characteristics": [],
                "complexity_indicators": []
            }
            
        except Exception as e:
            logger.warning(f"⚠️ 난이도 특성 추출 실패: {e}")
            return {"keywords": [], "characteristics": [], "complexity_indicators": []}
    
    async def _extract_domain_characteristics(self, questions: List[str], domain: str) -> Dict:
        """AI를 사용한 분야별 특성 추출"""
        
        try:
            combined_text = "\n".join(questions[:10])
            
            prompt = f"""
다음은 '{domain}' 분야로 분류된 문제들입니다.
이 분야의 핵심 키워드와 특성을 분석해주세요.

문제들:
{combined_text}

분석 결과를 다음 JSON 형식으로 제공해주세요:
{{
    "core_keywords": ["핵심키워드1", "핵심키워드2"],
    "technical_terms": ["전문용어1", "전문용어2"],
    "topic_indicators": ["주제지표1", "주제지표2"]
}}
"""
            
            if self.gemini_model:
                response = await self._call_gemini_async(prompt)
                try:
                    from app.services.question_parser import QuestionParser
                    result = QuestionParser.parse_ai_json_response(response)
                    if "error" not in result:
                        return result
                except:
                    pass
            
            return {
                "core_keywords": [],
                "technical_terms": [],
                "topic_indicators": []
            }
            
        except Exception as e:
            logger.warning(f"⚠️ 분야 특성 추출 실패: {e}")
            return {"core_keywords": [], "technical_terms": [], "topic_indicators": []}
    
    async def _call_gemini_async(self, prompt: str) -> str:
        """Gemini API 비동기 호출"""
        try:
            response = self.gemini_model.generate_content(prompt)
            return response.text
        except Exception as e:
            logger.error(f"Gemini API 호출 실패: {e}")
            return ""
    
    async def _save_training_results(self):
        """학습 결과 저장"""
        
        try:
            save_path = Path("data/llm_training")
            save_path.mkdir(exist_ok=True)
            
            # 학습 결과 저장
            training_results = {
                "timestamp": datetime.now().isoformat(),
                "difficulty_patterns": self.difficulty_patterns,
                "domain_keywords": self.domain_keywords,
                "professor_weights": self.professor_weights,
                "training_summary": {
                    dept: {
                        "total_questions": data["total_questions"],
                        "professors": list(data["professor_evaluations"].keys())
                    }
                    for dept, data in self.training_data.items()
                }
            }
            
            with open(save_path / "training_results.json", "w", encoding="utf-8") as f:
                json.dump(training_results, f, ensure_ascii=False, indent=2)
            
            logger.info(f"✅ 학습 결과 저장 완료: {save_path / 'training_results.json'}")
            
        except Exception as e:
            logger.error(f"❌ 학습 결과 저장 실패: {e}")
    
    async def predict_difficulty_and_domain(self, question: str, department: str) -> Dict:
        """
        새로운 문제의 난이도와 분야 예측
        
        Args:
            question: 분석할 문제 텍스트
            department: 학과명
            
        Returns:
            예측 결과 딕셔너리
        """
        
        try:
            # 학습 데이터 로드
            await self._load_training_results()
            
            # 학과별 패턴 적용
            if department not in self.difficulty_patterns:
                department = "작업치료학과"  # 기본값
            
            # AI 기반 예측
            prediction = await self._ai_predict(question, department)
            
            return {
                "difficulty": prediction.get("difficulty", "중"),
                "domain": prediction.get("domain", "일반"),
                "confidence": prediction.get("confidence", 0.7),
                "reasoning": prediction.get("reasoning", "AI 분석 결과")
            }
            
        except Exception as e:
            logger.error(f"❌ 난이도/분야 예측 실패: {e}")
            return {
                "difficulty": "중",
                "domain": "일반",
                "confidence": 0.5,
                "reasoning": "기본값 적용"
            }
    
    async def _load_training_results(self):
        """저장된 학습 결과 로드"""
        
        try:
            results_path = Path("data/llm_training/training_results.json")
            if results_path.exists():
                with open(results_path, "r", encoding="utf-8") as f:
                    results = json.load(f)
                
                self.difficulty_patterns = results.get("difficulty_patterns", {})
                self.domain_keywords = results.get("domain_keywords", {})
                self.professor_weights = results.get("professor_weights", {})
                
        except Exception as e:
            logger.warning(f"⚠️ 학습 결과 로드 실패: {e}")
    
    async def _ai_predict(self, question: str, department: str) -> Dict:
        """AI 기반 난이도/분야 예측"""
        
        try:
            # 학과별 학습 패턴 정보 구성
            dept_patterns = self.difficulty_patterns.get(department, {})
            dept_domains = self.domain_keywords.get(department, {})
            
            prompt = f"""
다음 문제의 난이도와 분야를 분석해주세요.

문제: {question}

학과: {department}

학습된 패턴 정보:
- 난이도 패턴: {json.dumps(dept_patterns, ensure_ascii=False)}
- 분야 키워드: {json.dumps(dept_domains, ensure_ascii=False)}

분석 기준:
1. 난이도: 하(기초개념, 단순암기), 중(응용, 이해), 상(종합분석, 고차원사고)
2. 분야: 학습된 분야 중에서 가장 적합한 것 선택

결과를 다음 JSON 형식으로 제공해주세요:
{{
    "difficulty": "하|중|상",
    "domain": "분야명",
    "confidence": 0.0-1.0,
    "reasoning": "분석 근거"
}}
"""
            
            if self.gemini_model:
                response = await self._call_gemini_async(prompt)
                try:
                    from app.services.question_parser import QuestionParser
                    result = QuestionParser.parse_ai_json_response(response)
                    if "error" not in result:
                        return result
                except:
                    pass
            
            # 기본값 반환
            return {
                "difficulty": "중",
                "domain": "일반",
                "confidence": 0.6,
                "reasoning": "기본 분석 결과"
            }
            
        except Exception as e:
            logger.error(f"❌ AI 예측 실패: {e}")
            return {
                "difficulty": "중",
                "domain": "일반",
                "confidence": 0.5,
                "reasoning": "예측 실패로 기본값 적용"
            }

# 전역 인스턴스
difficulty_domain_mapper = DifficultyDomainMapper() 