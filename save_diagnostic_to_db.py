"""
진단테스트 JSON 데이터를 데이터베이스에 저장
물리치료학과 30문제 진단테스트 DB 저장
"""
import json
import sys
from pathlib import Path
from sqlalchemy.orm import Session

# 모듈 경로 추가
sys.path.append(str(Path(__file__).parent))

from app.db.database import get_db, engine
from app.models.diagnostic_test import DiagnosticTest, DiagnosticQuestion
from app.models.user import User  # User 모델 import
from app.db.database import Base
from sqlalchemy import func

def create_tables():
    """진단테스트 테이블 생성"""
    print("📊 진단테스트 테이블 생성 중...")
    try:
        Base.metadata.create_all(bind=engine)
        print("✅ 테이블 생성 완료")
    except Exception as e:
        print(f"❌ 테이블 생성 오류: {e}")

def save_diagnostic_test_to_db():
    """진단테스트 JSON을 데이터베이스에 저장"""
    
    # JSON 파일 로드
    json_file = Path("data/diagnostic_test_physics_therapy.json")
    
    if not json_file.exists():
        print(f"❌ 진단테스트 파일이 없습니다: {json_file}")
        return False
    
    print(f"📄 진단테스트 JSON 로딩: {json_file}")
    
    with open(json_file, 'r', encoding='utf-8') as f:
        diagnostic_data = json.load(f)
    
    db = next(get_db())
    
    try:
        # 기존 물리치료학과 진단테스트 확인
        existing_test = db.query(DiagnosticTest).filter(
            DiagnosticTest.department == "물리치료학과"
        ).first()
        
        if existing_test:
            print("🔄 기존 물리치료학과 진단테스트 업데이트")
            
            # 기존 문제들 삭제
            db.query(DiagnosticQuestion).filter(
                DiagnosticQuestion.test_id == existing_test.id
            ).delete()
            
            # 테스트 정보 업데이트
            existing_test.title = diagnostic_data["test_info"]["title"]
            existing_test.description = diagnostic_data["test_info"]["description"]
            existing_test.total_questions = diagnostic_data["test_info"]["total_questions"]
            existing_test.time_limit = diagnostic_data["test_info"]["time_limit"]
            existing_test.version = diagnostic_data["test_info"]["version"]
            existing_test.scoring_criteria = diagnostic_data["scoring_criteria"]
            
            diagnostic_test = existing_test
            
        else:
            print("🆕 새로운 물리치료학과 진단테스트 생성")
            
            # 새 진단테스트 생성
            diagnostic_test = DiagnosticTest(
                department="물리치료학과",
                title=diagnostic_data["test_info"]["title"],
                description=diagnostic_data["test_info"]["description"],
                total_questions=diagnostic_data["test_info"]["total_questions"],
                time_limit=diagnostic_data["test_info"]["time_limit"],
                version=diagnostic_data["test_info"]["version"],
                scoring_criteria=diagnostic_data["scoring_criteria"],
                is_active=True
            )
            
            db.add(diagnostic_test)
            db.flush()  # ID 생성을 위해
        
        # 문제들 저장
        print(f"📝 {len(diagnostic_data['questions'])}개 문제 저장 중...")
        
        for question_data in diagnostic_data["questions"]:
            diagnostic_question = DiagnosticQuestion(
                test_id=diagnostic_test.id,
                question_id=question_data["question_id"],
                question_number=question_data["question_number"],
                content=question_data["content"],
                options=question_data["options"],
                correct_answer=question_data["correct_answer"],
                
                # 과목 정보
                subject=question_data.get("subject"),
                area_name=question_data.get("area_name"),
                year=question_data.get("year"),
                original_question_number=question_data.get("original_question_number"),
                
                # AI 분석 결과
                difficulty=question_data.get("difficulty"),
                difficulty_level=question_data.get("difficulty_level"),
                question_type=question_data.get("question_type"),
                domain=question_data.get("domain"),
                diagnostic_suitability=question_data.get("diagnostic_suitability"),
                discrimination_power=question_data.get("discrimination_power"),
                
                # 진단테스트용 메타데이터
                points=question_data.get("points", 0.0),
                source_info=question_data.get("source_info")
            )
            
            db.add(diagnostic_question)
        
        # 커밋
        db.commit()
        
        print("✅ 진단테스트 데이터베이스 저장 완료!")
        print(f"📊 테스트 ID: {diagnostic_test.id}")
        print(f"📝 저장된 문제 수: {diagnostic_test.total_questions}개")
        
        # 저장 확인
        verify_saved_data(db, diagnostic_test.id)
        
        return True
        
    except Exception as e:
        db.rollback()
        print(f"❌ 데이터베이스 저장 오류: {e}")
        return False
        
    finally:
        db.close()

def verify_saved_data(db: Session, test_id: int):
    """저장된 데이터 확인"""
    print("\n🔍 저장 데이터 검증:")
    
    # 테스트 정보 확인
    test = db.query(DiagnosticTest).filter(DiagnosticTest.id == test_id).first()
    if test:
        print(f"  ✅ 테스트: {test.title}")
        print(f"  📚 학과: {test.department}")
        print(f"  📊 문제 수: {test.total_questions}")
        print(f"  ⏰ 제한 시간: {test.time_limit}분")
    
    # 문제 수 확인
    question_count = db.query(DiagnosticQuestion).filter(
        DiagnosticQuestion.test_id == test_id
    ).count()
    print(f"  📝 실제 저장된 문제 수: {question_count}개")
    
    # 난이도별 분포 확인
    difficulty_stats = db.query(
        DiagnosticQuestion.difficulty_level,
        func.count(DiagnosticQuestion.id)
    ).filter(
        DiagnosticQuestion.test_id == test_id
    ).group_by(DiagnosticQuestion.difficulty_level).all()
    
    print("  🎚️ 난이도 분포:")
    for level, count in difficulty_stats:
        print(f"    {level}: {count}문제")
    
    # 분야별 분포 확인
    domain_stats = db.query(
        DiagnosticQuestion.domain,
        func.count(DiagnosticQuestion.id)
    ).filter(
        DiagnosticQuestion.test_id == test_id
    ).group_by(DiagnosticQuestion.domain).all()
    
    print("  🏥 분야별 분포:")
    for domain, count in domain_stats[:5]:  # 상위 5개만
        print(f"    {domain}: {count}문제")

def main():
    """메인 실행 함수"""
    print("🚀 물리치료학과 진단테스트 데이터베이스 저장 시작!")
    
    # 1. 테이블 생성
    create_tables()
    
    # 2. 진단테스트 데이터 저장
    success = save_diagnostic_test_to_db()
    
    if success:
        print("\n🎉 진단테스트 데이터베이스 저장 완료!")
        print("✅ 물리치료학과 학생들이 진단테스트를 이용할 수 있습니다.")
    else:
        print("\n❌ 진단테스트 저장 실패")

if __name__ == "__main__":
    main() 