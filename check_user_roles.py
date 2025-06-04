import psycopg2
from psycopg2.extras import RealDictCursor

def check_user_roles():
    try:
        conn = psycopg2.connect(
            host='localhost',
            database='kb_learning_db',
            user='admin',
            password='1234'
        )
        
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            # 모든 사용자 정보 조회
            cur.execute('''
                SELECT user_id, name, role, is_verified, school, department, 
                       terms_agreed, privacy_agreed, identity_verified, age_verified
                FROM users 
                ORDER BY created_at
            ''')
            users = cur.fetchall()
            
            print('🔍 현재 데이터베이스 사용자 정보:')
            print('=' * 100)
            for user in users:
                print(f"ID: {user['user_id']:<12} | 이름: {user['name']:<10} | "
                      f"역할: {user['role']:<10} | 인증: {user['is_verified']:<5} | "
                      f"학교: {user['school']:<15} | 학과: {user['department']}")
            
            print('\n📊 역할별 분포:')
            print('-' * 30)
            cur.execute('SELECT role, COUNT(*) as count FROM users GROUP BY role ORDER BY role')
            role_counts = cur.fetchall()
            for role in role_counts:
                print(f"{role['role']}: {role['count']}명")
            
            print('\n📋 인증 상태별 분포:')
            print('-' * 30)
            cur.execute('SELECT is_verified, COUNT(*) as count FROM users GROUP BY is_verified ORDER BY is_verified')
            verify_counts = cur.fetchall()
            for verify in verify_counts:
                status = "인증됨" if verify['is_verified'] else "미인증"
                print(f"{status}: {verify['count']}명")
                
            # 약관 동의 상태 확인
            print('\n📋 약관 동의 상태:')
            print('-' * 50)
            cur.execute('''
                SELECT 
                    CASE 
                        WHEN terms_agreed AND privacy_agreed AND identity_verified AND age_verified THEN '모든 약관 동의'
                        WHEN terms_agreed AND privacy_agreed THEN '기본 약관만 동의'
                        ELSE '약관 미동의'
                    END as agreement_status,
                    COUNT(*) as count
                FROM users 
                GROUP BY 
                    CASE 
                        WHEN terms_agreed AND privacy_agreed AND identity_verified AND age_verified THEN '모든 약관 동의'
                        WHEN terms_agreed AND privacy_agreed THEN '기본 약관만 동의'
                        ELSE '약관 미동의'
                    END
                ORDER BY count DESC
            ''')
            agreement_counts = cur.fetchall()
            for agreement in agreement_counts:
                print(f"{agreement['agreement_status']}: {agreement['count']}명")
        
        conn.close()
        print('\n✅ 데이터베이스 확인 완료')
        
    except Exception as e:
        print(f'❌ 데이터베이스 연결 실패: {e}')

if __name__ == "__main__":
    check_user_roles() 