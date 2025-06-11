"""
진단테스트 데이터베이스 저장 확인
"""
import sys
from pathlib import Path

# 모듈 경로 추가
sys.path.append(str(Path(__file__).parent))

from app.db.database import get_db
from app.models.diagnostic_test import DiagnosticTest, DiagnosticQuestion

def check_diagnostic_test():
    """진단테스트 데이터베이스 확인"""
    db = next(get_db())
    
    try:
        # 진단테스트 확인
        test = db.query(DiagnosticTest).filter(
            DiagnosticTest.department == "물리치료학과"
        ).first()
        
        if test:
            print(f"✅ 진단테스트: {test.title}")
            print(f"📚 학과: {test.department}")
            print(f"📊 문제 수: {test.total_questions}")
            
            # 실제 문제 수 확인
            question_count = db.query(DiagnosticQuestion).filter(
                DiagnosticQuestion.test_id == test.id
            ).count()
            print(f"📝 실제 저장된 문제 수: {question_count}개")
            
            return True
        else:
            print("❌ 물리치료학과 진단테스트가 없습니다.")
            return False
            
    except Exception as e:
        print(f"❌ 확인 오류: {e}")
        return False
        
    finally:
        db.close()

if __name__ == "__main__":
    print("🔍 진단테스트 데이터베이스 확인")
    success = check_diagnostic_test()
    
    if success:
        print("✅ 진단테스트가 정상적으로 저장되었습니다!")
    else:
        print("❌ 진단테스트 저장에 문제가 있습니다.") 