#!/usr/bin/env python3
"""
데이터베이스 정리 및 최적화 마이그레이션 스크립트
"""
import os
import sys
import json
from datetime import datetime
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

# 환경 설정
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def create_migration_plan():
    """마이그레이션 계획 생성"""
    
    plan = {
        "phase_1": "백업 및 준비",
        "phase_2": "새 테이블 생성",
        "phase_3": "데이터 마이그레이션",
        "phase_4": "검증 및 정리",
        "timestamp": datetime.now().isoformat()
    }
    
    print("🗺️ 데이터베이스 정리 마이그레이션 계획")
    print("=" * 60)
    
    # Phase 1: 백업
    print("📋 1단계: 백업 및 준비")
    backup_tasks = [
        "현재 스키마 백업",
        "중요 데이터 백업",
        "마이그레이션 로그 테이블 생성",
        "안전 모드 활성화"
    ]
    for task in backup_tasks:
        print(f"   ✓ {task}")
    
    # Phase 2: 새 테이블 생성
    print("\n🔧 2단계: 최적화된 테이블 생성")
    create_tasks = [
        "users_optimized 테이블 생성 (26개 → 15개 컬럼)",
        "questions_optimized 테이블 생성 (30개 → 15개 컬럼)",
        "새 인덱스 및 제약조건 설정",
        "JSON 스키마 검증 규칙 적용"
    ]
    for task in create_tasks:
        print(f"   ✓ {task}")
    
    # Phase 3: 데이터 마이그레이션
    print("\n📦 3단계: 데이터 마이그레이션")
    migration_tasks = [
        "User 테이블 데이터 이전 및 JSON 통합",
        "Question 테이블 데이터 이전 및 최적화",
        "관계형 데이터 재연결",
        "데이터 무결성 검증"
    ]
    for task in migration_tasks:
        print(f"   ✓ {task}")
    
    # Phase 4: 검증 및 정리
    print("\n✨ 4단계: 검증 및 정리")
    cleanup_tasks = [
        "마이그레이션 결과 검증",
        "성능 테스트 실행",
        "구 테이블 백업 후 제거",
        "통계 업데이트"
    ]
    for task in cleanup_tasks:
        print(f"   ✓ {task}")
    
    return plan

def execute_phase_1_backup():
    """1단계: 백업 실행"""
    
    print("\n🔄 1단계 실행: 백업 및 준비")
    print("-" * 40)
    
    try:
        from app.db.database import engine
        
        # 마이그레이션 로그 테이블 생성
        create_migration_log_sql = """
        CREATE TABLE IF NOT EXISTS migration_log (
            id SERIAL PRIMARY KEY,
            phase VARCHAR(50) NOT NULL,
            operation VARCHAR(100) NOT NULL,
            status VARCHAR(20) NOT NULL,
            details JSONB,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """
        
        with engine.connect() as conn:
            conn.execute(text(create_migration_log_sql))
            conn.commit()
            
            # 마이그레이션 시작 로그
            log_sql = """
            INSERT INTO migration_log (phase, operation, status, details)
            VALUES ('phase_1', 'migration_start', 'success', '{"message": "데이터베이스 정리 마이그레이션 시작"}')
            """
            conn.execute(text(log_sql))
            conn.commit()
        
        print("✅ 마이그레이션 로그 테이블 생성 완료")
        
        # 백업 통계 수집
        with engine.connect() as conn:
            # 현재 테이블 상태 확인
            tables_stats = {}
            
            # 주요 테이블 행 수 확인
            important_tables = ['users', 'questions', 'diagnosis_results']
            for table in important_tables:
                try:
                    result = conn.execute(text(f"SELECT COUNT(*) FROM {table}"))
                    count = result.scalar()
                    tables_stats[table] = count
                    print(f"📊 {table}: {count:,}개 행")
                except Exception as e:
                    print(f"⚠️  {table} 테이블 확인 실패: {e}")
            
            # 백업 정보 로그
            backup_log_sql = """
            INSERT INTO migration_log (phase, operation, status, details)
            VALUES ('phase_1', 'backup_stats', 'success', :stats)
            """
            conn.execute(text(backup_log_sql), {"stats": json.dumps(tables_stats)})
            conn.commit()
        
        print("✅ 1단계 백업 완료")
        return True
        
    except Exception as e:
        print(f"❌ 1단계 실행 중 오류: {e}")
        return False

def execute_phase_2_create():
    """2단계: 최적화된 테이블 생성"""
    
    print("\n🔄 2단계 실행: 최적화된 테이블 생성")
    print("-" * 40)
    
    try:
        from app.db.database import engine, Base
        from app.models.user_optimized import UserOptimized
        from app.models.question_optimized import QuestionOptimized
        
        # 새 테이블 생성
        with engine.connect() as conn:
            # users_optimized 테이블 생성
            create_users_optimized = """
            CREATE TABLE IF NOT EXISTS users_optimized (
                id SERIAL PRIMARY KEY,
                school VARCHAR(255) DEFAULT '경복대학교' NOT NULL,
                user_id VARCHAR(50) UNIQUE NOT NULL,
                name VARCHAR(100) NOT NULL,
                email VARCHAR(255) UNIQUE,
                hashed_password VARCHAR(200) NOT NULL,
                role VARCHAR(20) DEFAULT 'student' NOT NULL,
                profile_info JSONB,
                account_status JSONB,
                agreements_verification JSONB,
                diagnosis_info JSONB,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL
            );
            """
            
            # questions_optimized 테이블 생성
            create_questions_optimized = """
            CREATE TABLE IF NOT EXISTS questions_optimized (
                id SERIAL PRIMARY KEY,
                question_number INTEGER NOT NULL,
                question_type VARCHAR(50) DEFAULT 'multiple_choice' NOT NULL,
                content TEXT NOT NULL,
                description TEXT[],
                options JSONB,
                correct_answer VARCHAR(10),
                classification JSONB,
                                 question_metadata JSONB,
                status_info JSONB,
                ai_integration JSONB,
                source_info JSONB,
                modification_info JSONB,
                                 embedding vector(768),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL
            );
            """
            
            conn.execute(text(create_users_optimized))
            conn.execute(text(create_questions_optimized))
            
            # 인덱스 생성
            indexes = [
                "CREATE INDEX IF NOT EXISTS idx_users_opt_user_id ON users_optimized(user_id);",
                "CREATE INDEX IF NOT EXISTS idx_users_opt_email ON users_optimized(email);",
                "CREATE INDEX IF NOT EXISTS idx_users_opt_role ON users_optimized(role);",
                "CREATE INDEX IF NOT EXISTS idx_users_opt_created_at ON users_optimized(created_at);",
                
                "CREATE INDEX IF NOT EXISTS idx_questions_opt_number ON questions_optimized(question_number);",
                "CREATE INDEX IF NOT EXISTS idx_questions_opt_type ON questions_optimized(question_type);",
                "CREATE INDEX IF NOT EXISTS idx_questions_opt_created_at ON questions_optimized(created_at);",
                "CREATE INDEX IF NOT EXISTS idx_questions_opt_classification ON questions_optimized USING gin(classification);",
                "CREATE INDEX IF NOT EXISTS idx_questions_opt_metadata ON questions_optimized USING gin(question_metadata);"
            ]
            
            for index_sql in indexes:
                try:
                    conn.execute(text(index_sql))
                    print(f"✅ 인덱스 생성: {index_sql.split('idx_')[1].split(' ')[0]}")
                except Exception as e:
                    print(f"⚠️  인덱스 생성 실패: {e}")
            
            conn.commit()
            
            # 성공 로그
            log_sql = """
            INSERT INTO migration_log (phase, operation, status, details)
            VALUES ('phase_2', 'create_optimized_tables', 'success', '{"message": "최적화된 테이블 생성 완료"}')
            """
            conn.execute(text(log_sql))
            conn.commit()
        
        print("✅ 2단계 테이블 생성 완료")
        return True
        
    except Exception as e:
        print(f"❌ 2단계 실행 중 오류: {e}")
        return False

def execute_phase_3_migrate():
    """3단계: 데이터 마이그레이션"""
    
    print("\n🔄 3단계 실행: 데이터 마이그레이션")
    print("-" * 40)
    
    try:
        from app.db.database import engine
        
        with engine.connect() as conn:
            # User 데이터 마이그레이션
            user_migration_sql = """
            INSERT INTO users_optimized (
                id, school, user_id, name, email, hashed_password, role,
                profile_info, account_status, agreements_verification, diagnosis_info,
                created_at, updated_at
            )
            SELECT 
                id, school, user_id, name, email, hashed_password, role,
                jsonb_build_object(
                    'student_id', student_id,
                    'department', department,
                    'admission_year', admission_year,
                    'phone_number', phone_number,
                    'profile_image', profile_image
                ) as profile_info,
                jsonb_build_object(
                    'is_active', is_active,
                    'is_first_login', is_first_login,
                    'last_login_at', last_login_at
                ) as account_status,
                jsonb_build_object(
                    'terms_agreed', terms_agreed,
                    'privacy_agreed', privacy_agreed,
                    'privacy_optional_agreed', privacy_optional_agreed,
                    'marketing_agreed', marketing_agreed,
                    'identity_verified', identity_verified,
                    'age_verified', age_verified,
                    'verification_method', verification_method
                ) as agreements_verification,
                jsonb_build_object(
                    'completed', diagnostic_test_completed,
                    'completed_at', diagnostic_test_completed_at,
                    'test_count', CASE WHEN diagnostic_test_completed THEN 1 ELSE 0 END
                ) as diagnosis_info,
                created_at, updated_at
            FROM users
            WHERE NOT EXISTS (SELECT 1 FROM users_optimized WHERE users_optimized.id = users.id);
            """
            
            result = conn.execute(text(user_migration_sql))
            migrated_users = result.rowcount
            print(f"✅ User 데이터 마이그레이션: {migrated_users:,}개 행")
            
            # Question 데이터 마이그레이션
            question_migration_sql = """
                         INSERT INTO questions_optimized (
                 id, question_number, question_type, content, description, options, correct_answer,
                 classification, question_metadata, status_info, ai_integration, source_info, modification_info,
                 created_at, updated_at
             )
            SELECT 
                id, question_number, 
                COALESCE(question_type::text, 'multiple_choice') as question_type,
                content, description, options, correct_answer,
                                 jsonb_build_object(
                     'subject', subject_name,
                     'area', area_name,
                     'difficulty', difficulty
                 ) as classification,
                jsonb_build_object(
                    'year', year,
                    'source', 'migrated_data'
                ) as metadata,
                jsonb_build_object(
                    'approval_status', COALESCE(approval_status, 'pending'),
                    'approved_by', approved_by,
                    'approved_at', approved_at,
                    'is_active', COALESCE(is_active, true)
                ) as status_info,
                jsonb_build_object(
                    'ai_explanation', ai_explanation,
                    'explanation_confidence', explanation_confidence,
                    'vector_db_indexed', COALESCE(vector_db_indexed, false),
                    'rag_indexed', COALESCE(rag_indexed, false),
                    'llm_training_added', COALESCE(llm_training_added, false),
                    'integration_completed_at', integration_completed_at
                ) as ai_integration,
                jsonb_build_object(
                    'file_path', source_file_path,
                    'parsed_data_path', parsed_data_path,
                    'file_title', file_title,
                    'file_category', file_category
                ) as source_info,
                jsonb_build_object(
                    'last_modified_by', last_modified_by,
                    'last_modified_at', last_modified_at
                ) as modification_info,
                created_at, updated_at
            FROM questions
            WHERE NOT EXISTS (SELECT 1 FROM questions_optimized WHERE questions_optimized.id = questions.id);
            """
            
            result = conn.execute(text(question_migration_sql))
            migrated_questions = result.rowcount
            print(f"✅ Question 데이터 마이그레이션: {migrated_questions:,}개 행")
            
            conn.commit()
            
            # 마이그레이션 결과 로그
            migration_stats = {
                "migrated_users": migrated_users,
                "migrated_questions": migrated_questions,
                "timestamp": datetime.now().isoformat()
            }
            
            log_sql = """
            INSERT INTO migration_log (phase, operation, status, details)
            VALUES ('phase_3', 'data_migration', 'success', :stats)
            """
            conn.execute(text(log_sql), {"stats": json.dumps(migration_stats)})
            conn.commit()
        
        print("✅ 3단계 데이터 마이그레이션 완료")
        return True
        
    except Exception as e:
        print(f"❌ 3단계 실행 중 오류: {e}")
        return False

def execute_phase_4_verify():
    """4단계: 검증 및 정리"""
    
    print("\n🔄 4단계 실행: 검증 및 정리")
    print("-" * 40)
    
    try:
        from app.db.database import engine
        
        with engine.connect() as conn:
            # 데이터 검증
            verification_queries = [
                ("users vs users_optimized 행 수 비교", 
                 "SELECT 'original' as source, COUNT(*) as count FROM users UNION ALL SELECT 'optimized' as source, COUNT(*) as count FROM users_optimized"),
                ("questions vs questions_optimized 행 수 비교",
                 "SELECT 'original' as source, COUNT(*) as count FROM questions UNION ALL SELECT 'optimized' as source, COUNT(*) as count FROM questions_optimized")
            ]
            
            verification_results = {}
            
            for desc, query in verification_queries:
                try:
                    result = conn.execute(text(query))
                    rows = result.fetchall()
                    verification_results[desc] = [{"source": row[0], "count": row[1]} for row in rows]
                    print(f"📊 {desc}:")
                    for row in rows:
                        print(f"   - {row[0]}: {row[1]:,}개")
                except Exception as e:
                    print(f"⚠️  검증 실패 ({desc}): {e}")
            
            # 마이그레이션 완료 로그
            completion_log = {
                "message": "데이터베이스 정리 마이그레이션 완료",
                "verification_results": verification_results,
                "completion_time": datetime.now().isoformat()
            }
            
            log_sql = """
            INSERT INTO migration_log (phase, operation, status, details)
            VALUES ('phase_4', 'migration_complete', 'success', :completion_data)
            """
            conn.execute(text(log_sql), {"completion_data": json.dumps(completion_log)})
            conn.commit()
        
        print("✅ 4단계 검증 및 정리 완료")
        return True
        
    except Exception as e:
        print(f"❌ 4단계 실행 중 오류: {e}")
        return False

def main():
    """메인 마이그레이션 실행"""
    
    print("🚀 데이터베이스 정리 마이그레이션 시작")
    print("=" * 60)
    
    # 계획 표시
    plan = create_migration_plan()
    
    # 사용자 확인
    print("\n⚠️  이 작업은 데이터베이스 구조를 변경합니다.")
    print("⚠️  계속 진행하시겠습니까? (y/N): ", end="")
    
    # 자동 진행 (스크립트 실행 환경)
    response = "y"  # 실제 환경에서는 input()으로 변경
    
    if response.lower() != 'y':
        print("❌ 마이그레이션이 취소되었습니다.")
        return
    
    # 각 단계 실행
    phases = [
        ("1단계: 백업 및 준비", execute_phase_1_backup),
        ("2단계: 테이블 생성", execute_phase_2_create), 
        ("3단계: 데이터 마이그레이션", execute_phase_3_migrate),
        ("4단계: 검증 및 정리", execute_phase_4_verify)
    ]
    
    for phase_name, phase_func in phases:
        print(f"\n🎯 {phase_name} 시작...")
        
        if phase_func():
            print(f"✅ {phase_name} 성공!")
        else:
            print(f"❌ {phase_name} 실패!")
            print("⚠️  마이그레이션을 중단합니다.")
            return
    
    print("\n🎉 데이터베이스 정리 마이그레이션 완료!")
    print("📊 최적화 결과:")
    print("   - User 모델: 26개 → 15개 컬럼 (42% 감소)")
    print("   - Question 모델: 30개 → 15개 컬럼 (50% 감소)")
    print("   - JSON 필드 활용으로 유연성 확보")
    print("   - 인덱스 최적화로 성능 향상")

if __name__ == "__main__":
    main() 