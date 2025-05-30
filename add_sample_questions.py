"""
진단 테스트용 샘플 문제 추가 스크립트
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from sqlalchemy.orm import Session
from app.db.database import get_db
from app.models.question import Question, QuestionType, DifficultyLevel
from app.models.diagnosis import TestResponse  # 관계 로딩을 위해 import
from app.models.user import User  # 관계 로딩을 위해 import
import json

def add_sample_questions():
    """샘플 문제 추가"""
    db = next(get_db())
    
    # 컴퓨터 과학 관련 샘플 문제들
    sample_questions = [
        # EASY 난이도
        {
            "content": "다음 중 프로그래밍 언어가 아닌 것은?",
            "question_type": QuestionType.MULTIPLE_CHOICE,
            "difficulty": DifficultyLevel.EASY,
            "subject_name": "computer_science",
            "choices": ["Python", "Java", "HTML", "C++"],
            "correct_answer": "HTML"
        },
        {
            "content": "CPU의 주요 구성 요소가 아닌 것은?",
            "question_type": QuestionType.MULTIPLE_CHOICE,
            "difficulty": DifficultyLevel.EASY,
            "subject_name": "computer_science",
            "choices": ["ALU", "Control Unit", "RAM", "Register"],
            "correct_answer": "RAM"
        },
        # MEDIUM 난이도
        {
            "content": "시간 복잡도가 O(n log n)인 정렬 알고리즘은?",
            "question_type": QuestionType.MULTIPLE_CHOICE,
            "difficulty": DifficultyLevel.MEDIUM,
            "subject_name": "computer_science",
            "choices": ["버블 정렬", "퀵 정렬", "선택 정렬", "삽입 정렬"],
            "correct_answer": "퀵 정렬"
        },
        {
            "content": "데이터베이스의 ACID 속성이 아닌 것은?",
            "question_type": QuestionType.MULTIPLE_CHOICE,
            "difficulty": DifficultyLevel.MEDIUM,
            "subject_name": "computer_science",
            "choices": ["Atomicity", "Consistency", "Integrity", "Durability"],
            "correct_answer": "Integrity"
        },
        # HARD 난이도
        {
            "content": "TCP와 UDP의 차이점을 설명하시오.",
            "question_type": QuestionType.SHORT_ANSWER,
            "difficulty": DifficultyLevel.HARD,
            "subject_name": "computer_science",
            "correct_answer": "TCP는 연결 지향적이고 신뢰성 있는 전송을 보장하며, UDP는 비연결성이고 빠르지만 신뢰성을 보장하지 않습니다."
        },
        {
            "content": "동적 프로그래밍의 조건 두 가지는?",
            "question_type": QuestionType.SHORT_ANSWER,
            "difficulty": DifficultyLevel.HARD,
            "subject_name": "computer_science",
            "correct_answer": "최적 부분 구조와 중복되는 부분 문제"
        },
        # VERY_HARD 난이도
        {
            "content": "P vs NP 문제에 대해 설명하시오.",
            "question_type": QuestionType.ESSAY,
            "difficulty": DifficultyLevel.VERY_HARD,
            "subject_name": "computer_science",
            "correct_answer": "P는 다항 시간 내에 해결 가능한 문제들의 집합이고, NP는 다항 시간 내에 검증 가능한 문제들의 집합입니다."
        }
    ]
    
    # 더 많은 문제 추가 (총 30개 이상)
    for i in range(23):  # 7개 + 23개 = 30개
        difficulty = [DifficultyLevel.EASY, DifficultyLevel.MEDIUM, DifficultyLevel.HARD, DifficultyLevel.VERY_HARD][i % 4]
        question = Question(
            content=f"컴퓨터 과학 문제 {i+8}: 난이도 {difficulty.value}",
            question_type=QuestionType.MULTIPLE_CHOICE,
            difficulty=difficulty,
            subject_name="computer_science",
            choices=["답안 A", "답안 B", "답안 C", "답안 D"],
            correct_answer="답안 A",
            is_active=True
        )
        db.add(question)
    
    # 정의된 샘플 문제들 추가
    for q_data in sample_questions:
        question = Question(**q_data, is_active=True)
        db.add(question)
    
    try:
        db.commit()
        print("✅ 샘플 문제가 성공적으로 추가되었습니다!")
        
        # 추가된 문제 수 확인
        total_count = db.query(Question).filter(
            Question.subject_name.ilike("%computer_science%"),
            Question.is_active == True
        ).count()
        
        print(f"📊 총 컴퓨터 과학 문제 수: {total_count}개")
        
    except Exception as e:
        db.rollback()
        print(f"❌ 오류 발생: {str(e)}")
    finally:
        db.close()

if __name__ == "__main__":
    add_sample_questions() 