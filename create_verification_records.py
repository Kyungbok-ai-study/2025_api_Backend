import psycopg2
from psycopg2.extras import RealDictCursor
from datetime import datetime, timedelta
import json

def create_verification_table():
    """인증 요청 테이블 생성"""
    try:
        conn = psycopg2.connect(
            host='localhost',
            database='kb_learning_db',
            user='admin',
            password='1234'
        )
        
        with conn.cursor() as cur:
            # 인증 요청 테이블 생성
            cur.execute("""
                CREATE TABLE IF NOT EXISTS verification_requests (
                    id SERIAL PRIMARY KEY,
                    request_number INTEGER UNIQUE NOT NULL,
                    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
                    verification_type VARCHAR(20) NOT NULL,
                    reason TEXT NOT NULL,
                    status VARCHAR(20) DEFAULT 'pending' NOT NULL,
                    submitted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    reviewed_at TIMESTAMP,
                    reviewer_comment TEXT,
                    documents TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """)
            
            # 인덱스 생성
            cur.execute("""
                CREATE INDEX IF NOT EXISTS idx_verification_user_id ON verification_requests(user_id);
                CREATE INDEX IF NOT EXISTS idx_verification_status ON verification_requests(status);
                CREATE INDEX IF NOT EXISTS idx_verification_request_number ON verification_requests(request_number);
            """)
            
            conn.commit()
            print("✅ verification_requests 테이블 생성 완료")
            
    except Exception as e:
        print(f"❌ 테이블 생성 실패: {e}")
    finally:
        if conn:
            conn.close()

def create_dummy_verification_records():
    """더미 인증 기록 생성"""
    try:
        conn = psycopg2.connect(
            host='localhost',
            database='kb_learning_db',
            user='admin',
            password='1234'
        )
        
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            # 인증된 사용자들 조회
            cur.execute("""
                SELECT id, user_id, name, role 
                FROM users 
                WHERE role IN ('student', 'professor', 'admin')
            """)
            verified_users = cur.fetchall()
            
            print(f"📋 인증된 사용자 {len(verified_users)}명 발견")
            
            # 기존 인증 기록 확인
            cur.execute("SELECT COUNT(*) as count FROM verification_requests")
            existing_count = cur.fetchone()['count']
            
            if existing_count > 0:
                print(f"⚠️  기존 인증 기록 {existing_count}개 발견. 새로운 기록을 추가합니다.")
            
            # 각 인증된 사용자에 대해 더미 기록 생성
            request_number_start = 2024001 + existing_count
            
            for i, user in enumerate(verified_users):
                request_number = request_number_start + i
                
                # 인증 유형 결정
                verification_type = 'professor' if user['role'] == 'professor' else 'student'
                
                # 신청일시 (1-3개월 전)
                days_ago = 30 + (i * 20)  # 각 사용자마다 다른 날짜
                submitted_at = datetime.now() - timedelta(days=days_ago)
                reviewed_at = submitted_at + timedelta(days=3)  # 신청 3일 후 승인
                
                # 신청 사유
                reason_templates = {
                    'student': f"안녕하세요. {user['name']}입니다. 재학생 인증을 통해 캠퍼스온의 모든 학습 기능을 이용하고 싶습니다. 첨부된 재학증명서와 학생증을 확인해주세요.",
                    'professor': f"안녕하세요. {user['name']}입니다. 교수 인증을 신청합니다. 캠퍼스온에서 강의 관련 기능을 활용하여 학생들의 학습을 도울 수 있도록 승인 부탁드립니다."
                }
                reason = reason_templates.get(verification_type, "인증을 신청합니다.")
                
                # 검토자 코멘트
                reviewer_comments = [
                    "제출해주신 서류를 검토한 결과, 모든 요건을 충족하여 승인 처리되었습니다.",
                    "첨부된 증빙서류가 확인되어 인증을 승인합니다. 앞으로 모든 서비스를 이용하실 수 있습니다.",
                    "서류 검토 완료 후 승인 처리되었습니다. 캠퍼스온 서비스를 자유롭게 이용해주세요.",
                    "인증 요청 검토 결과 승인되었습니다. 이제 모든 기능을 사용하실 수 있습니다."
                ]
                reviewer_comment = reviewer_comments[i % len(reviewer_comments)]
                
                # 제출 서류 정보 (JSON 형태)
                if verification_type == 'student':
                    documents = json.dumps([
                        {"name": "재학증명서.pdf", "size": 1024000, "uploaded_at": submitted_at.isoformat()},
                        {"name": "학생증_앞면.jpg", "size": 512000, "uploaded_at": submitted_at.isoformat()},
                        {"name": "학생증_뒷면.jpg", "size": 487000, "uploaded_at": submitted_at.isoformat()}
                    ], ensure_ascii=False)
                else:
                    documents = json.dumps([
                        {"name": "교직원증.pdf", "size": 890000, "uploaded_at": submitted_at.isoformat()},
                        {"name": "대학홈페이지_교수소개_캡처.png", "size": 1200000, "uploaded_at": submitted_at.isoformat()},
                        {"name": "재직증명서.pdf", "size": 756000, "uploaded_at": submitted_at.isoformat()}
                    ], ensure_ascii=False)
                
                # 인증 기록 삽입
                cur.execute("""
                    INSERT INTO verification_requests 
                    (request_number, user_id, verification_type, reason, status, 
                     submitted_at, reviewed_at, reviewer_comment, documents)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                """, (
                    request_number,
                    user['id'],
                    verification_type,
                    reason,
                    'approved',
                    submitted_at,
                    reviewed_at,
                    reviewer_comment,
                    documents
                ))
                
                print(f"✅ {user['name']} ({user['user_id']}) - 인증기록 #{request_number} 생성")
            
            conn.commit()
            print(f"\n🎉 총 {len(verified_users)}개의 인증 기록 생성 완료!")
            
            # 생성된 기록 확인
            cur.execute("""
                SELECT vr.request_number, u.name, u.user_id, vr.verification_type, vr.status
                FROM verification_requests vr
                JOIN users u ON vr.user_id = u.id
                ORDER BY vr.request_number
            """)
            records = cur.fetchall()
            
            print("\n📋 생성된 인증 기록:")
            print("=" * 80)
            for record in records:
                print(f"#{record['request_number']} | {record['name']} ({record['user_id']}) | "
                      f"{record['verification_type']} | {record['status']}")
            
    except Exception as e:
        print(f"❌ 더미 데이터 생성 실패: {e}")
    finally:
        if conn:
            conn.close()

if __name__ == "__main__":
    print("🚀 인증 기록 시스템 초기화 시작...")
    create_verification_table()
    create_dummy_verification_records()
    print("\n✅ 모든 작업 완료!") 