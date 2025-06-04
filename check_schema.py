import psycopg2
from psycopg2.extras import RealDictCursor

def check_database_schema():
    try:
        conn = psycopg2.connect(
            host='localhost',
            database='kb_learning_db',
            user='admin',
            password='1234'
        )
        
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            # 테이블 구조 확인
            cur.execute("""
                SELECT column_name, data_type, is_nullable, column_default
                FROM information_schema.columns 
                WHERE table_name = 'users' 
                ORDER BY ordinal_position;
            """)
            columns = cur.fetchall()
            
            print('📋 users 테이블 구조:')
            print('=' * 80)
            for col in columns:
                print(f"컬럼명: {col['column_name']:<20} | 타입: {col['data_type']:<15} | "
                      f"NULL 허용: {col['is_nullable']:<3} | 기본값: {col['column_default']}")
            
            print('\n🔍 현재 데이터베이스 사용자 정보:')
            print('=' * 100)
            
            # 모든 사용자 정보 조회 (올바른 컬럼명 사용)
            cur.execute('''
                SELECT user_id, name, role, school, department, 
                       terms_agreed, privacy_agreed, identity_verified, age_verified
                FROM users 
                ORDER BY created_at
            ''')
            users = cur.fetchall()
            
            for user in users:
                print(f"ID: {user['user_id']:<12} | 이름: {user['name']:<10} | "
                      f"역할: {user['role']:<10} | 학교: {user['school']:<15} | "
                      f"학과: {user['department']}")
                print(f"   → 약관동의: {user['terms_agreed']} | 개인정보동의: {user['privacy_agreed']} | "
                      f"신분인증: {user['identity_verified']} | 연령인증: {user['age_verified']}")
                print()
            
            print('\n📊 역할별 분포:')
            print('-' * 30)
            cur.execute('SELECT role, COUNT(*) as count FROM users GROUP BY role ORDER BY role')
            role_counts = cur.fetchall()
            for role in role_counts:
                print(f"{role['role']}: {role['count']}명")
        
        conn.close()
        print('\n✅ 스키마 확인 완료')
        
    except Exception as e:
        print(f'❌ 데이터베이스 연결 실패: {e}')

if __name__ == "__main__":
    check_database_schema() 