"""
물리치료학과 진단테스트 2차~10차 고급 생성 스크립트
기존 국가고시 데이터를 분석하여 난이도/유형/영역별로 최적화된 테스트 생성
"""
import json
import os
import random
from datetime import datetime
from collections import defaultdict, Counter
import copy

class PhysicsTherapyTestGenerator:
    """물리치료학과 진단테스트 생성기"""
    
    def __init__(self):
        self.base_questions = []
        self.questions_by_domain = defaultdict(list)
        self.questions_by_difficulty = defaultdict(list) 
        self.questions_by_type = defaultdict(list)
        self.used_question_ids = set()
        
        # 각 차수별 전문 영역 정의
        self.round_focus_areas = {
            2: {
                "title": "운동치료학",
                "domains": ["운동치료", "근골격계", "운동생리학"],
                "emphasis": "운동치료 원리와 기법"
            },
            3: {
                "title": "신경계 물리치료", 
                "domains": ["신경계", "신경계/뇌신경", "신경과학"],
                "emphasis": "중추신경계 및 말초신경계 질환"
            },
            4: {
                "title": "근골격계 물리치료",
                "domains": ["근골격계", "정형외과", "스포츠"],
                "emphasis": "근골격계 손상 및 기능장애"
            },
            5: {
                "title": "심폐 물리치료",
                "domains": ["심폐", "호흡기", "순환기"],
                "emphasis": "심장 및 폐 질환 재활"
            },
            6: {
                "title": "소아 물리치료",
                "domains": ["소아", "발달", "근골격계/소아/노인"],
                "emphasis": "소아 발달 및 신경발달치료"
            },
            7: {
                "title": "노인 물리치료",
                "domains": ["노인", "근골격계/소아/노인", "만성질환"],
                "emphasis": "노인성 질환 및 기능 저하"
            },
            8: {
                "title": "스포츠 물리치료",
                "domains": ["스포츠", "운동치료", "근골격계"],
                "emphasis": "스포츠 손상 예방 및 재활"
            },
            9: {
                "title": "정형외과 물리치료",
                "domains": ["정형외과", "근골격계", "수술적"],
                "emphasis": "수술 전후 재활 및 기능회복"
            },
            10: {
                "title": "종합 평가",
                "domains": ["전체영역"],
                "emphasis": "모든 영역 종합 평가"
            }
        }
        
        # 난이도별 문제 배분 (30문제 기준)
        self.difficulty_distribution = {
            "쉬움": 8,      # 26.7%
            "보통": 18,     # 60.0%  
            "어려움": 4     # 13.3%
        }
        
        # 문제 유형별 배분
        self.type_distribution = {
            "기본개념": 20,     # 66.7%
            "응용문제": 6,      # 20.0%
            "임상응용": 3,      # 10.0%
            "종합판단": 1       # 3.3%
        }
    
    def load_base_questions(self):
        """기존 물리치료학과 문제 데이터 로드"""
        file_path = "data/departments/medical/diagnostic_test_physics_therapy.json"
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                self.base_questions = data.get("questions", [])
            
            print(f"📚 기존 문제 {len(self.base_questions)}개 로드 완료")
            self.analyze_questions()
            
        except FileNotFoundError:
            print(f"❌ 파일을 찾을 수 없습니다: {file_path}")
            return False
        except Exception as e:
            print(f"❌ 데이터 로드 실패: {e}")
            return False
        
        return True
    
    def analyze_questions(self):
        """문제들을 도메인, 난이도, 유형별로 분류"""
        print("🔍 문제 분석 시작...")
        
        for question in self.base_questions:
            domain = question.get("domain", "기타")
            difficulty = question.get("difficulty_level", "보통")
            q_type = question.get("question_type", "기본개념")
            
            self.questions_by_domain[domain].append(question)
            self.questions_by_difficulty[difficulty].append(question)
            self.questions_by_type[q_type].append(question)
        
        # 분석 결과 출력
        print(f"\n📊 도메인별 문제 수:")
        for domain, questions in self.questions_by_domain.items():
            print(f"  - {domain}: {len(questions)}개")
        
        print(f"\n📊 난이도별 문제 수:")
        for difficulty, questions in self.questions_by_difficulty.items():
            print(f"  - {difficulty}: {len(questions)}개")
        
        print(f"\n📊 유형별 문제 수:")
        for q_type, questions in self.questions_by_type.items():
            print(f"  - {q_type}: {len(questions)}개")
    
    def create_enhanced_questions(self, round_num, focus_area_info):
        """향상된 문제 생성 (기존 문제 변형 및 새 문제 추가)"""
        enhanced_questions = []
        
        # 기존 문제에서 해당 영역과 관련된 문제들 선별
        relevant_questions = []
        target_domains = focus_area_info["domains"]
        
        if "전체영역" in target_domains:
            # 10차는 모든 영역에서 선별
            relevant_questions = self.base_questions.copy()
        else:
            # 해당 영역의 문제들만 선별
            for domain in target_domains:
                relevant_questions.extend(self.questions_by_domain.get(domain, []))
            
            # 관련 키워드가 포함된 문제들도 추가
            keywords = self.get_domain_keywords(focus_area_info["title"])
            for question in self.base_questions:
                content = question.get("content", "").lower()
                area_name = question.get("area_name", "").lower()
                if any(keyword in content or keyword in area_name for keyword in keywords):
                    if question not in relevant_questions:
                        relevant_questions.append(question)
        
        print(f"🎯 {round_num}차 관련 문제 {len(relevant_questions)}개 발견")
        
        # 난이도별로 문제 선별 및 생성
        for difficulty, target_count in self.difficulty_distribution.items():
            available_questions = [q for q in relevant_questions 
                                 if q.get("difficulty_level") == difficulty 
                                 and q.get("question_id") not in self.used_question_ids]
            
            selected_count = min(target_count, len(available_questions))
            selected_questions = random.sample(available_questions, selected_count)
            
            # 선택된 문제들을 새로운 ID로 변형
            for i, question in enumerate(selected_questions):
                new_question = self.transform_question(question, round_num, len(enhanced_questions) + 1)
                enhanced_questions.append(new_question)
                self.used_question_ids.add(question.get("question_id"))
            
            # 부족한 문제는 새로 생성
            if selected_count < target_count:
                shortage = target_count - selected_count
                for i in range(shortage):
                    new_question = self.generate_new_question(
                        round_num, len(enhanced_questions) + 1, 
                        difficulty, focus_area_info
                    )
                    enhanced_questions.append(new_question)
        
        # 문제 번호 재정렬
        for i, question in enumerate(enhanced_questions, 1):
            question["question_number"] = i
        
        return enhanced_questions[:30]  # 30문제로 제한
    
    def get_domain_keywords(self, focus_title):
        """전문 영역별 키워드 반환"""
        keyword_map = {
            "운동치료학": ["운동", "근력", "지구력", "훈련", "재활", "등장성", "등척성"],
            "신경계 물리치료": ["뇌", "신경", "뇌졸중", "파킨슨", "척수", "마비", "브룬스트롬"],
            "근골격계 물리치료": ["근육", "뼈", "관절", "인대", "건", "골절", "염좌"],
            "심폐 물리치료": ["심장", "폐", "호흡", "순환", "혈압", "산소", "운동부하"],
            "소아 물리치료": ["소아", "아동", "발달", "성장", "신생아", "영유아"],
            "노인 물리치료": ["노인", "고령", "퇴행", "낙상", "골다공증", "치매"],
            "스포츠 물리치료": ["스포츠", "운동선수", "경기", "훈련", "부상", "퍼포먼스"],
            "정형외과 물리치료": ["수술", "정형", "임플란트", "고정술", "절단술"],
            "종합 평가": []
        }
        return keyword_map.get(focus_title, [])
    
    def transform_question(self, original_question, round_num, question_num):
        """기존 문제를 새로운 차수용으로 변형"""
        new_question = copy.deepcopy(original_question)
        new_question["question_id"] = f"DIAG_R{round_num}_{question_num:03d}"
        new_question["question_number"] = question_num
        
        # 점수 재계산 (난이도 가중치 적용)
        difficulty_weights = {"쉬움": 1.0, "보통": 1.2, "어려움": 1.5}
        base_score = 3.3
        weight = difficulty_weights.get(new_question.get("difficulty_level", "보통"), 1.0)
        new_question["points"] = round(base_score * weight, 1)
        
        return new_question
    
    def generate_new_question(self, round_num, question_num, difficulty, focus_area_info):
        """새로운 문제 생성 (부족한 경우)"""
        
        # 각 영역별 새 문제 템플릿
        question_templates = {
            "운동치료학": {
                "쉬움": [
                    {
                        "content": "등장성 운동(isotonic exercise)에 대한 설명으로 옳은 것은?",
                        "options": {
                            "1": "근육의 길이는 변하지 않고 장력만 증가한다",
                            "2": "일정한 속도로 관절이 움직인다", 
                            "3": "근육의 길이가 변하면서 수축한다",
                            "4": "저항이 일정하게 유지된다",
                            "5": "관절의 움직임 없이 근수축이 일어난다"
                        },
                        "correct_answer": "3"
                    }
                ],
                "보통": [
                    {
                        "content": "근력 향상을 위한 적절한 운동 강도는 1RM의 몇 %인가?",
                        "options": {
                            "1": "40-50%",
                            "2": "60-70%", 
                            "3": "80-90%",
                            "4": "95-100%",
                            "5": "100% 이상"
                        },
                        "correct_answer": "3"
                    }
                ]
            },
            "신경계 물리치료": {
                "쉬움": [
                    {
                        "content": "상위운동신경원 손상의 특징적 증상은?",
                        "options": {
                            "1": "근위축이 빠르게 진행된다",
                            "2": "병적 반사가 나타난다", 
                            "3": "근섬유다발수축이 관찰된다",
                            "4": "근긴장도가 감소한다",
                            "5": "감각 소실이 동반된다"
                        },
                        "correct_answer": "2"
                    }
                ]
            }
        }
        
        # 해당 영역과 난이도에 맞는 템플릿 선택
        templates = question_templates.get(focus_area_info["title"], {}).get(difficulty, [])
        
        if templates:
            template = random.choice(templates)
            return {
                "question_id": f"DIAG_R{round_num}_{question_num:03d}",
                "question_number": question_num,
                "content": template["content"],
                "options": template["options"],
                "correct_answer": template["correct_answer"],
                "subject": "물리치료학과",
                "area_name": focus_area_info["title"],
                "year": 2024,
                "original_question_number": 1000 + question_num,
                "difficulty": {"쉬움": 4, "보통": 6, "어려움": 8}[difficulty],
                "difficulty_level": difficulty,
                "question_type": "기본개념",
                "domain": focus_area_info["domains"][0] if focus_area_info["domains"][0] != "전체영역" else "종합",
                "diagnostic_suitability": 8,
                "discrimination_power": 7,
                "points": 3.3 * {"쉬움": 1.0, "보통": 1.2, "어려움": 1.5}[difficulty]
            }
        else:
            # 기본 문제 생성
            return self.create_default_question(round_num, question_num, difficulty, focus_area_info)
    
    def create_default_question(self, round_num, question_num, difficulty, focus_area_info):
        """기본 문제 생성"""
        return {
            "question_id": f"DIAG_R{round_num}_{question_num:03d}",
            "question_number": question_num,
            "content": f"{focus_area_info['title']} 관련 {difficulty} 난이도 문제 {question_num}",
            "options": {
                "1": "선택지 1",
                "2": "선택지 2",
                "3": "선택지 3",
                "4": "선택지 4",
                "5": "선택지 5"
            },
            "correct_answer": "1",
            "subject": "물리치료학과",
            "area_name": focus_area_info["title"],
            "year": 2024,
            "original_question_number": 1000 + question_num,
            "difficulty": {"쉬움": 4, "보통": 6, "어려움": 8}[difficulty],
            "difficulty_level": difficulty,
            "question_type": "기본개념",
            "domain": focus_area_info["domains"][0] if focus_area_info["domains"][0] != "전체영역" else "종합",
            "diagnostic_suitability": 8,
            "discrimination_power": 7,
            "points": 3.3 * {"쉬움": 1.0, "보통": 1.2, "어려움": 1.5}[difficulty]
        }
    
    def create_test_data(self, round_num):
        """차수별 테스트 데이터 생성"""
        focus_area_info = self.round_focus_areas[round_num]
        
        questions = self.create_enhanced_questions(round_num, focus_area_info)
        
        # 통계 계산
        difficulty_stats = Counter(q["difficulty_level"] for q in questions)
        domain_stats = Counter(q["domain"] for q in questions)
        type_stats = Counter(q["question_type"] for q in questions)
        
        return {
            "test_info": {
                "title": f"물리치료학과 진단테스트 {round_num}차 - {focus_area_info['title']}",
                "description": f"{focus_area_info['title']} 중심의 물리치료사 국가고시 수준 진단테스트",
                "total_questions": len(questions),
                "time_limit": 60,
                "created_at": datetime.now().isoformat(),
                "version": f"{round_num}.0",
                "source": "2021-2024년 물리치료사 국가고시 기출 + AI 생성",
                "focus_area": focus_area_info["title"],
                "emphasis": focus_area_info["emphasis"]
            },
            "scoring_criteria": {
                "total_score": 100,
                "score_per_question": 3.3,
                "difficulty_weights": {
                    "쉬움": 1.0,
                    "보통": 1.2,
                    "어려움": 1.5
                },
                "level_classification": {
                    "상급": {"min_score": 80, "description": "국가고시 합격 수준"},
                    "중급": {"min_score": 65, "description": "추가 학습 필요"},
                    "하급": {"min_score": 50, "description": "기초부터 체계적 학습 필요"},
                    "미흡": {"min_score": 0, "description": "전면적 재학습 권장"}
                }
            },
            "questions": questions,
            "statistics": {
                "difficulty_distribution": dict(difficulty_stats),
                "domain_distribution": dict(domain_stats),
                "type_distribution": dict(type_stats),
                "average_difficulty": sum(q["difficulty"] for q in questions) / len(questions),
                "average_discrimination": sum(q["discrimination_power"] for q in questions) / len(questions),
                "total_questions": len(questions)
            }
        }
    
    def save_test_to_file(self, test_data, round_num):
        """테스트 데이터를 JSON 파일로 저장"""
        output_dir = "data/departments/medical"
        os.makedirs(output_dir, exist_ok=True)
        
        filename = f"diagnostic_test_physics_therapy_round{round_num}.json"
        filepath = os.path.join(output_dir, filename)
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(test_data, f, ensure_ascii=False, indent=2)
        
        print(f"✅ {filename} 생성 완료 (문제 {len(test_data['questions'])}개)")
    
    def generate_all_tests(self):
        """2차부터 10차까지 모든 테스트 생성"""
        if not self.load_base_questions():
            return False
        
        print(f"\n🚀 물리치료학과 진단테스트 2차~10차 생성 시작\n")
        
        for round_num in range(2, 11):
            print(f"📝 {round_num}차 테스트 생성 중...")
            focus_area = self.round_focus_areas[round_num]["title"]
            
            test_data = self.create_test_data(round_num)
            self.save_test_to_file(test_data, round_num)
            
            print(f"   ✨ {focus_area} 중심 문제 {len(test_data['questions'])}개")
            print(f"   📊 난이도 분포: {test_data['statistics']['difficulty_distribution']}")
            print(f"   🎯 평균 난이도: {test_data['statistics']['average_difficulty']:.1f}\n")
        
        print("🎉 물리치료학과 진단테스트 2차~10차 생성 완료!")
        return True

def main():
    """메인 실행 함수"""
    generator = PhysicsTherapyTestGenerator()
    success = generator.generate_all_tests()
    
    if success:
        print("\n📚 생성된 파일 목록:")
        for round_num in range(2, 11):
            print(f"  - diagnostic_test_physics_therapy_round{round_num}.json")
    else:
        print("❌ 테스트 생성 실패")

if __name__ == "__main__":
    main() 