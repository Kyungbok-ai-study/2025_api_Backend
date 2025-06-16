#!/usr/bin/env python3
"""
사용자 진단테스트 상태 직접 리셋
PostgreSQL 직접 연결로 데이터 정리
"""

import psycopg2
from datetime import datetime

def reset_user_diagnosis(user_id: int = 33):
    """사용자 진단테스트 상태 직접 리셋"""
    
    # 데이터베이스 연결 정보 (환경에 맞게 수정)
    conn_params = {
        'host': 'localhost',
        'database': 'campus_on_db',
        'user': 'postgres',
        'password': 'your_password',  # 실제 비밀번호로 변경
        'port': '5432'
    }
    
    try:
        # 데이터베이스 연결
        conn = psycopg2.connect(**conn_params)
        cur = conn.cursor()
        
        print(f"🔗 데이터베이스 연결 성공")
        
        # 1. 사용자 현재 상태 확인
        cur.execute("""
            SELECT id, name, diagnosis_info 
            FROM users 
            WHERE id = %s
        """, (user_id,))
        
        user_data = cur.fetchone()
        if not user_data:
            print(f"❌ 사용자 ID {user_id}를 찾을 수 없습니다.")
            return
        
        print(f"👤 사용자: {user_data[1]} (ID: {user_data[0]})")
        print(f"📊 현재 diagnosis_info: {user_data[2]}")
        
        # 2. 진단테스트 세션들 조회
        cur.execute("""
            SELECT session_id, round_number, status, created_at
            FROM diagnostic_sessions 
            WHERE user_id = %s
            ORDER BY round_number, created_at
        """, (user_id,))
        
        sessions = cur.fetchall()
        print(f"📋 기존 세션 개수: {len(sessions)}")
        
        for session in sessions:
            print(f"  - 세션 {session[0]}: {session[1]}차, 상태: {session[2]}")
        
        # 3. 관련 데이터 삭제
        if sessions:
            print(f"🗑️ 기존 데이터 삭제 중...")
            
            # AI 분석 데이터 삭제
            cur.execute("""
                DELETE FROM diagnostic_ai_analysis 
                WHERE session_id IN (
                    SELECT session_id FROM diagnostic_sessions WHERE user_id = %s
                )
            """, (user_id,))
            
            # 답변 데이터 삭제
            cur.execute("""
                DELETE FROM diagnostic_answers 
                WHERE session_id IN (
                    SELECT session_id FROM diagnostic_sessions WHERE user_id = %s
                )
            """, (user_id,))
            
            # 세션 삭제
            cur.execute("""
                DELETE FROM diagnostic_sessions 
                WHERE user_id = %s
            """, (user_id,))
            
            print(f"✅ {len(sessions)}개 세션 관련 데이터 삭제 완료")
        
        # 4. 사용자 진단테스트 상태 초기화
        print(f"🔄 사용자 진단테스트 상태 초기화...")
        
        reset_diagnosis_info = {
            "completed": False,
            "completed_at": None,
            "latest_score": None,
            "test_count": 0
        }
        
        cur.execute("""
            UPDATE users 
            SET diagnosis_info = %s, updated_at = %s
            WHERE id = %s
        """, (psycopg2.extras.Json(reset_diagnosis_info), datetime.utcnow(), user_id))
        
        # 변경사항 커밋
        conn.commit()
        
        # 5. 결과 확인
        cur.execute("""
            SELECT diagnosis_info 
            FROM users 
            WHERE id = %s
        """, (user_id,))
        
        new_diagnosis_info = cur.fetchone()[0]
        
        print(f"✅ 리셋 완료!")
        print(f"📊 새로운 diagnosis_info: {new_diagnosis_info}")
        print(f"")
        print(f"🎉 이제 1차 진단테스트부터 다시 시작할 수 있습니다!")
        
    except psycopg2.Error as e:
        print(f"❌ 데이터베이스 오류: {e}")
        if conn:
            conn.rollback()
    except Exception as e:
        print(f"❌ 오류 발생: {e}")
    finally:
        if cur:
            cur.close()
        if conn:
            conn.close()

if __name__ == "__main__":
    print("🧹 사용자 진단테스트 상태 리셋 시작...")
    print("⚠️ 데이터베이스 연결 정보를 확인하고 실행하세요.")
    
    # 실행하려면 아래 주석을 해제하세요
    # reset_user_diagnosis()
    
    print("📝 스크립트 준비 완료. 데이터베이스 정보 확인 후 실행하세요.") 