import psycopg2
from psycopg2.extras import RealDictCursor

def update_user_roles():
    try:
        conn = psycopg2.connect(
            host='localhost',
            database='kb_learning_db',
            user='admin',
            password='1234'
        )
        
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            print('🔄 사용자 역할 업데이트 시작...')
            
            # 1. jung051004를 관리자로 설정
            cur.execute("""
                UPDATE users 
                SET role = 'admin'
                WHERE user_id = 'jung051004'
            """)
            print('✅ jung051004 → 관리자로 변경')
            
            # 2. testuser789를 교수로 설정  
            cur.execute("""
                UPDATE users 
                SET role = 'professor'
                WHERE user_id = 'testuser789'
            """)
            print('✅ testuser789 → 교수로 변경')
            
            # 3. hgd123을 교수로 설정
            cur.execute("""
                UPDATE users 
                SET role = 'professor' 
                WHERE user_id = 'hgd123'
            """)
            print('✅ hgd123 → 교수로 변경')
            
            # 4. 일부 사용자의 약관 동의를 취소하여 미인증 상태로 만들기
            cur.execute("""
                UPDATE users 
                SET terms_agreed = false, 
                    privacy_agreed = false,
                    identity_verified = false,
                    age_verified = false
                WHERE user_id IN ('2023001', 'jjw12', 'test123')
            """)
            print('✅ 2023001, jjw12, test123 → 미인증 상태로 변경')
            
            # 5. 나머지는 재학생으로 유지 (이미 인증된 상태)
            cur.execute("""
                UPDATE users 
                SET role = 'student'
                WHERE user_id IN ('2024001', 'jung05', '1234')
            """)
            print('✅ 재학생 계정들 확인')
            
            conn.commit()
            
            # 업데이트 결과 확인
            print('\n📊 업데이트 결과 확인:')
            print('=' * 100)
            
            cur.execute('''
                SELECT user_id, name, role, 
                       terms_agreed, privacy_agreed, identity_verified, age_verified,
                       CASE 
                           WHEN role = 'student' AND terms_agreed AND privacy_agreed AND identity_verified AND age_verified THEN 'student'
                           WHEN role = 'student' THEN 'unverified'
                           ELSE role
                       END as effective_role
                FROM users 
                ORDER BY role, user_id
            ''')
            users = cur.fetchall()
            
            for user in users:
                effective_role_text = {
                    'student': '재학생',
                    'professor': '교수', 
                    'admin': '관리자',
                    'unverified': '미인증유저'
                }.get(user['effective_role'], '미인증유저')
                
                print(f"ID: {user['user_id']:<12} | 이름: {user['name']:<10} | "
                      f"DB 역할: {user['role']:<10} | 실제 표시: {effective_role_text:<10} | "
                      f"약관: {user['terms_agreed']} | 인증: {user['identity_verified']}")
            
            print('\n📈 역할별 통계:')
            print('-' * 50)
            
            cur.execute('''
                SELECT 
                    CASE 
                        WHEN role = 'student' AND terms_agreed AND privacy_agreed AND identity_verified AND age_verified THEN 'student'
                        WHEN role = 'student' THEN 'unverified'
                        ELSE role
                    END as effective_role,
                    COUNT(*) as count
                FROM users 
                GROUP BY effective_role
                ORDER BY effective_role
            ''')
            stats = cur.fetchall()
            
            for stat in stats:
                role_text = {
                    'student': '재학생',
                    'professor': '교수',
                    'admin': '관리자', 
                    'unverified': '미인증유저'
                }.get(stat['effective_role'], '미인증유저')
                print(f"{role_text}: {stat['count']}명")
        
        conn.close()
        print('\n✅ 사용자 역할 업데이트 완료!')
        
    except Exception as e:
        print(f'❌ 업데이트 실패: {e}')

if __name__ == "__main__":
    update_user_roles() 