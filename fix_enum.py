from app.db.database import engine
from sqlalchemy import text

try:
    with engine.connect() as conn:
        # 대소문자 구분 값 모두 추가
        conn.execute(text("ALTER TYPE diagnosissubject ADD VALUE IF NOT EXISTS 'PHYSICAL_THERAPY'"))
        conn.commit()
        print("✅ PHYSICAL_THERAPY 값 추가 완료!")
except Exception as e:
    print(f"❌ 오류: {e}") 