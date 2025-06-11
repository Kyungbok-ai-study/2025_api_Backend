"""
물리치료학과 진단테스트 문제 생성기
88개 학습된 문제에서 AI가 분석하여 학생 수준 진단에 최적화된 30문제 선별
"""
import json
import asyncio
from pathlib import Path
from typing import List, Dict, Any
from datetime import datetime
import random

from app.services.deepseek_service import LocalDeepSeekService

class DiagnosticTestCreator:
    """진단테스트 생성기"""
    
    def __init__(self):
        self.json_dir = Path("data/save_parser")
        self.deepseek = LocalDeepSeekService()
        self.target_count = 30
        
    async def load_all_questions(self) -> List[Dict[str, Any]]:
        """88개 학습된 문제 모두 로드"""
        json_files = list(self.json_dir.glob("*.json"))
        all_questions = []
        
        print(f"📂 JSON 파일 로딩: {len(json_files)}개")
        
        for json_file in json_files:
            print(f"📄 로딩 중: {json_file.name}")
            
            with open(json_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            questions = data.get("questions", [])
            
            # 문제에 추가 정보 삽입
            for i, q in enumerate(questions):
                q["source_file"] = json_file.name
                q["original_index"] = i
                q["unique_id"] = f"{q.get('year', 2024)}_{q.get('question_number', i+1)}"
                
            all_questions.extend(questions)
        
        print(f"✅ 총 로드된 문제: {len(all_questions)}개")
        return all_questions
    
    async def analyze_question_difficulty(self, question: Dict[str, Any]) -> Dict[str, Any]:
        """AI를 통한 문제 난이도 및 특성 분석"""
        
        question_text = question.get("content", "")
        options = question.get("options", {})
        subject = question.get("subject", "물리치료학")
        
        if options:
            options_text = "\n".join([f"{k}. {v}" for k, v in options.items()])
            full_question = f"{question_text}\n\n선택지:\n{options_text}"
        else:
            full_question = question_text
        
        # AI에게 문제 분석 요청
        analysis_prompt = f"""
당신은 물리치료학과 교육 전문가입니다. 다음 국가고시 문제를 분석해주세요.

문제:
{full_question}

과목: {subject}
연도: {question.get('year', '미상')}

다음 기준으로 분석해주세요:

1. 난이도 (1-10점, 5점이 보통)
2. 문제 유형 (기본개념/응용/실무/종합판단)
3. 주요 분야 (신경계/근골격계/심폐/소아/노인/스포츠/기타)
4. 진단테스트 적합성 (1-10점)
5. 학생 수준 변별력 (1-10점)

응답 형식 (JSON):
{{
  "difficulty": 숫자,
  "question_type": "문제유형",
  "domain": "주요분야", 
  "diagnostic_suitability": 숫자,
  "discrimination_power": 숫자,
  "reasoning": "선택 이유 간단 설명"
}}
"""
        
        try:
            messages = [
                {"role": "system", "content": "당신은 물리치료학과 교육 평가 전문가입니다. 정확하고 객관적인 분석을 제공해주세요."},
                {"role": "user", "content": analysis_prompt}
            ]
            
            result = await self.deepseek.chat_completion(messages, temperature=0.3)
            
            if result.get('success'):
                # JSON 응답 파싱 시도
                response_text = result.get('content', '')
                
                # JSON 부분만 추출
                try:
                    json_start = response_text.find('{')
                    json_end = response_text.rfind('}') + 1
                    json_text = response_text[json_start:json_end]
                    
                    analysis = json.loads(json_text)
                    
                    # 기본값 보정
                    analysis['difficulty'] = max(1, min(10, analysis.get('difficulty', 5)))
                    analysis['diagnostic_suitability'] = max(1, min(10, analysis.get('diagnostic_suitability', 5)))
                    analysis['discrimination_power'] = max(1, min(10, analysis.get('discrimination_power', 5)))
                    
                    return analysis
                    
                except json.JSONDecodeError:
                    print(f"⚠️ JSON 파싱 실패, 기본값 사용: {question.get('unique_id')}")
                    
            # 실패시 기본 분석값
            return self._get_default_analysis(question)
            
        except Exception as e:
            print(f"❌ 분석 오류: {e}")
            return self._get_default_analysis(question)
    
    def _get_default_analysis(self, question: Dict[str, Any]) -> Dict[str, Any]:
        """기본 분석값 (AI 분석 실패시)"""
        subject = question.get("subject", "").lower()
        
        # 과목별 기본 분야 매핑
        domain_mapping = {
            "신경": "신경계",
            "근골격": "근골격계", 
            "정형": "근골격계",
            "심폐": "심폐",
            "소아": "소아",
            "노인": "노인",
            "스포츠": "스포츠"
        }
        
        domain = "기타"
        for key, value in domain_mapping.items():
            if key in subject:
                domain = value
                break
        
        return {
            "difficulty": random.randint(4, 7),  # 중간 난이도
            "question_type": "응용",
            "domain": domain,
            "diagnostic_suitability": random.randint(6, 8),
            "discrimination_power": random.randint(5, 7),
            "reasoning": "기본 분석값 적용"
        }
    
    async def select_diagnostic_questions(self, questions: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """진단테스트용 30문제 선별"""
        print(f"🤖 AI 분석 시작: {len(questions)}개 문제")
        
        # 1단계: 모든 문제 AI 분석
        analyzed_questions = []
        
        for i, question in enumerate(questions, 1):
            print(f"📊 분석 중 ({i}/{len(questions)}): {question.get('unique_id')}")
            
            analysis = await self.analyze_question_difficulty(question)
            
            # 분석 결과를 문제에 추가
            question['ai_analysis'] = analysis
            analyzed_questions.append(question)
            
            # 과부하 방지
            await asyncio.sleep(0.1)
        
        # 2단계: 진단테스트 적합성 기준으로 필터링
        suitable_questions = [
            q for q in analyzed_questions 
            if q['ai_analysis'].get('diagnostic_suitability', 0) >= 6
        ]
        
        print(f"🎯 진단테스트 적합 문제: {len(suitable_questions)}개")
        
        # 3단계: 균형 잡힌 30문제 선별
        selected_questions = self._balance_selection(suitable_questions)
        
        print(f"✅ 최종 선별된 문제: {len(selected_questions)}개")
        
        return selected_questions
    
    def _balance_selection(self, questions: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """균형 잡힌 문제 선별"""
        
        # 난이도별 분포 목표
        difficulty_targets = {
            "쉬움": 8,    # 1-4점: 기본 개념 확인
            "보통": 14,   # 5-7점: 핵심 역량 평가  
            "어려움": 8   # 8-10점: 고급 사고력
        }
        
        # 분야별 분포 목표
        domain_targets = {
            "신경계": 6,
            "근골격계": 8, 
            "심폐": 4,
            "소아": 2,
            "노인": 2,
            "스포츠": 3,
            "기타": 5
        }
        
        # 문제 유형별 분포 목표
        type_targets = {
            "기본개념": 8,
            "응용": 12,
            "실무": 6,
            "종합판단": 4
        }
        
        # 선별 알고리즘
        selected = []
        remaining = questions.copy()
        
        # 1단계: 난이도별 선별
        for difficulty_range, target_count in [
            ((1, 4), difficulty_targets["쉬움"]),
            ((5, 7), difficulty_targets["보통"]), 
            ((8, 10), difficulty_targets["어려움"])
        ]:
            candidates = [
                q for q in remaining 
                if difficulty_range[0] <= q['ai_analysis'].get('difficulty', 5) <= difficulty_range[1]
            ]
            
            # 변별력 순으로 정렬해서 상위 선택
            candidates.sort(key=lambda x: x['ai_analysis'].get('discrimination_power', 0), reverse=True)
            
            selected_count = min(target_count, len(candidates))
            selected.extend(candidates[:selected_count])
            
            # 선택된 문제들 제거
            for q in candidates[:selected_count]:
                if q in remaining:
                    remaining.remove(q)
        
        # 2단계: 부족한 분야 보완
        while len(selected) < self.target_count and remaining:
            # 가장 부족한 분야 찾기
            current_domains = {}
            for q in selected:
                domain = q['ai_analysis'].get('domain', '기타')
                current_domains[domain] = current_domains.get(domain, 0) + 1
            
            most_needed_domain = None
            max_deficit = 0
            
            for domain, target in domain_targets.items():
                current = current_domains.get(domain, 0)
                deficit = target - current
                if deficit > max_deficit:
                    max_deficit = deficit
                    most_needed_domain = domain
            
            if most_needed_domain:
                # 해당 분야에서 변별력이 높은 문제 선택
                candidates = [
                    q for q in remaining 
                    if q['ai_analysis'].get('domain') == most_needed_domain
                ]
                
                if candidates:
                    best_candidate = max(candidates, key=lambda x: x['ai_analysis'].get('discrimination_power', 0))
                    selected.append(best_candidate)
                    remaining.remove(best_candidate)
                else:
                    # 해당 분야가 없으면 변별력 높은 문제 선택
                    if remaining:
                        best_candidate = max(remaining, key=lambda x: x['ai_analysis'].get('discrimination_power', 0))
                        selected.append(best_candidate)
                        remaining.remove(best_candidate)
            else:
                break
        
        # 정확히 30개가 되도록 조정
        if len(selected) > self.target_count:
            # 변별력 낮은 순으로 제거
            selected.sort(key=lambda x: x['ai_analysis'].get('discrimination_power', 0), reverse=True)
            selected = selected[:self.target_count]
        
        return selected
    
    async def create_diagnostic_test_json(self, selected_questions: List[Dict[str, Any]]) -> Dict[str, Any]:
        """진단테스트 JSON 생성"""
        
        # 진단테스트 메타데이터
        diagnostic_test = {
            "test_info": {
                "title": "물리치료학과 수준 진단테스트",
                "description": "물리치료사 국가고시 기출문제 기반 학생 수준 진단",
                "total_questions": len(selected_questions),
                "time_limit": 60,  # 60분
                "created_at": datetime.now().isoformat(),
                "version": "1.0",
                "source": "2021-2024년 물리치료사 국가고시 기출"
            },
            
            "scoring_criteria": {
                "total_score": 100,
                "score_per_question": round(100 / len(selected_questions), 1),
                "difficulty_weights": {
                    "쉬움": 1.0,    # 기본 점수
                    "보통": 1.2,    # 20% 가산
                    "어려움": 1.5   # 50% 가산
                },
                "level_classification": {
                    "상급": {"min_score": 80, "description": "국가고시 합격 수준"},
                    "중급": {"min_score": 65, "description": "추가 학습 필요"},
                    "하급": {"min_score": 50, "description": "기초부터 체계적 학습 필요"},
                    "미흡": {"min_score": 0, "description": "전면적 재학습 권장"}
                }
            },
            
            "questions": []
        }
        
        # 문제 번호 재정렬
        for i, question in enumerate(selected_questions, 1):
            diagnostic_question = {
                "question_id": f"DIAG_{i:03d}",
                "question_number": i,
                "content": question.get("content", ""),
                "options": question.get("options", {}),
                "correct_answer": question.get("correct_answer", ""),
                "subject": question.get("subject", "물리치료학"),
                "area_name": question.get("area_name", ""),
                "year": question.get("year"),
                "original_question_number": question.get("question_number"),
                
                # AI 분석 결과
                "difficulty": question['ai_analysis'].get('difficulty'),
                "difficulty_level": self._categorize_difficulty(question['ai_analysis'].get('difficulty', 5)),
                "question_type": question['ai_analysis'].get('question_type'),
                "domain": question['ai_analysis'].get('domain'),
                "diagnostic_suitability": question['ai_analysis'].get('diagnostic_suitability'),
                "discrimination_power": question['ai_analysis'].get('discrimination_power'),
                
                # 진단테스트용 메타데이터
                "points": self._calculate_points(question['ai_analysis']),
                "source_info": {
                    "file": question.get("source_file"),
                    "unique_id": question.get("unique_id")
                }
            }
            
            diagnostic_test["questions"].append(diagnostic_question)
        
        # 통계 정보 추가
        diagnostic_test["statistics"] = self._calculate_test_statistics(selected_questions)
        
        return diagnostic_test
    
    def _categorize_difficulty(self, difficulty_score: int) -> str:
        """난이도 점수를 등급으로 변환"""
        if difficulty_score <= 4:
            return "쉬움"
        elif difficulty_score <= 7:
            return "보통"
        else:
            return "어려움"
    
    def _calculate_points(self, analysis: Dict[str, Any]) -> float:
        """문제별 점수 계산 (난이도와 변별력 고려)"""
        base_points = 100 / self.target_count  # 기본 점수
        difficulty = analysis.get('difficulty', 5)
        discrimination = analysis.get('discrimination_power', 5)
        
        # 난이도 가중치
        if difficulty <= 4:
            weight = 1.0
        elif difficulty <= 7:
            weight = 1.2
        else:
            weight = 1.5
        
        # 변별력 보정 (±10%)
        discrimination_factor = 0.9 + (discrimination / 50)
        
        return round(base_points * weight * discrimination_factor, 1)
    
    def _calculate_test_statistics(self, questions: List[Dict[str, Any]]) -> Dict[str, Any]:
        """테스트 통계 계산"""
        
        # 난이도 분포
        difficulty_dist = {"쉬움": 0, "보통": 0, "어려움": 0}
        domain_dist = {}
        type_dist = {}
        
        avg_difficulty = 0
        avg_discrimination = 0
        
        for q in questions:
            analysis = q['ai_analysis']
            
            difficulty = analysis.get('difficulty', 5)
            avg_difficulty += difficulty
            avg_discrimination += analysis.get('discrimination_power', 5)
            
            # 분포 계산
            difficulty_level = self._categorize_difficulty(difficulty)
            difficulty_dist[difficulty_level] += 1
            
            domain = analysis.get('domain', '기타')
            domain_dist[domain] = domain_dist.get(domain, 0) + 1
            
            question_type = analysis.get('question_type', '응용')
            type_dist[question_type] = type_dist.get(question_type, 0) + 1
        
        return {
            "difficulty_distribution": difficulty_dist,
            "domain_distribution": domain_dist,
            "type_distribution": type_dist,
            "average_difficulty": round(avg_difficulty / len(questions), 1),
            "average_discrimination": round(avg_discrimination / len(questions), 1),
            "total_questions": len(questions)
        }
    
    async def run_creation_process(self) -> str:
        """전체 진단테스트 생성 프로세스"""
        print("🚀 물리치료학과 진단테스트 생성 시작!")
        
        # 1. 88개 문제 로드
        all_questions = await self.load_all_questions()
        
        # 2. AI 분석을 통한 30문제 선별
        selected_questions = await self.select_diagnostic_questions(all_questions)
        
        # 3. 진단테스트 JSON 생성
        diagnostic_test = await self.create_diagnostic_test_json(selected_questions)
        
        # 4. 파일 저장
        output_file = Path("data/diagnostic_test_physics_therapy.json")
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(diagnostic_test, f, ensure_ascii=False, indent=2)
        
        print(f"💾 진단테스트 저장 완료: {output_file}")
        
        # 5. 요약 정보 출력
        self._print_summary(diagnostic_test)
        
        return str(output_file)
    
    def _print_summary(self, diagnostic_test: Dict[str, Any]):
        """진단테스트 요약 정보 출력"""
        print("\n📊 진단테스트 요약:")
        print(f"  📝 총 문제 수: {diagnostic_test['test_info']['total_questions']}문제")
        print(f"  ⏱️ 제한 시간: {diagnostic_test['test_info']['time_limit']}분")
        
        stats = diagnostic_test['statistics']
        print(f"  📈 평균 난이도: {stats['average_difficulty']}/10")
        print(f"  🎯 평균 변별력: {stats['average_discrimination']}/10")
        
        print("\n🎚️ 난이도 분포:")
        for level, count in stats['difficulty_distribution'].items():
            print(f"    {level}: {count}문제")
        
        print("\n🏥 분야별 분포:")
        for domain, count in stats['domain_distribution'].items():
            print(f"    {domain}: {count}문제")
        
        print("\n🔍 문제 유형 분포:")
        for qtype, count in stats['type_distribution'].items():
            print(f"    {qtype}: {count}문제")

async def main():
    """메인 실행 함수"""
    creator = DiagnosticTestCreator()
    output_file = await creator.run_creation_process()
    
    print(f"\n🎉 진단테스트 생성 완료!")
    print(f"📁 파일 위치: {output_file}")
    print("✅ 학생 수준 진단을 위한 30문제가 준비되었습니다!")

if __name__ == "__main__":
    asyncio.run(main()) 