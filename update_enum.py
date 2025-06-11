from app.db.database import engine
from sqlalchemy import text

try:
    with engine.connect() as conn:
        # DiagnosisSubject enum에 physical_therapy 값 추가
        conn.execute(text("ALTER TYPE diagnosissubject ADD VALUE IF NOT EXISTS 'physical_therapy'"))
        conn.commit()
        print("✅ DiagnosisSubject enum에 'physical_therapy' 값이 성공적으로 추가되었습니다!")
except Exception as e:
    print(f"❌ Enum 업데이트 실패: {e}")

if __name__ == "__main__":
    update_enum() 