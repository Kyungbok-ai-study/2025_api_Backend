from app.db.database import engine
from sqlalchemy import text

try:
    with engine.connect() as conn:
        result = conn.execute(text("SELECT unnest(enum_range(NULL::diagnosissubject))"))
        values = [row[0] for row in result]
        print("DiagnosisSubject enum 값들:")
        for i, value in enumerate(values, 1):
            print(f"  {i}. '{value}'")
        
        if 'physical_therapy' in values and 'PHYSICAL_THERAPY' in values:
            print("✅ 필요한 모든 enum 값이 존재합니다!")
        else:
            print("❌ 일부 enum 값이 누락되었습니다.")
            
except Exception as e:
    print(f"❌ 오류: {e}") 