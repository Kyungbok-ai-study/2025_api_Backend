"""
학생 진단테스트 차수 진행 상황 테이블 생성 스크립트
"""
import os
import sys
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

# 현재 디렉토리를 Python 경로에 추가
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.core.config import settings
from app.db.database import engine, SessionLocal

def create_tables():
    """학생 진단테스트 차수 진행 상황 테이블 생성"""
    
    # SQL 명령어들
    sql_commands = [
        # student_diagnosis_progress 테이블 생성 (이미 존재하는 경우 무시)
        """
        CREATE TABLE IF NOT EXISTS student_diagnosis_progress (
            id SERIAL PRIMARY KEY,
            user_id INTEGER NOT NULL REFERENCES users(id),
            department VARCHAR(100) NOT NULL,
            current_round INTEGER NOT NULL DEFAULT 0,
            max_available_round INTEGER NOT NULL DEFAULT 1,
            completed_rounds JSONB NOT NULL DEFAULT '[]'::jsonb,
            round_details JSONB NOT NULL DEFAULT '{}'::jsonb,
            total_tests_completed INTEGER NOT NULL DEFAULT 0,
            average_score REAL NOT NULL DEFAULT 0.0,
            total_study_time INTEGER NOT NULL DEFAULT 0,
            learning_pattern JSONB,
            next_recommendation JSONB,
            is_active BOOLEAN NOT NULL DEFAULT true,
            last_test_date TIMESTAMP WITH TIME ZONE,
            created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now(),
            updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now(),
            CONSTRAINT uq_student_department_progress UNIQUE (user_id, department)
        );
        """,
        
        # diagnosis_round_config 테이블 생성 (이미 존재하는 경우 무시)
        """
        CREATE TABLE IF NOT EXISTS diagnosis_round_config (
            id SERIAL PRIMARY KEY,
            department VARCHAR(100) NOT NULL,
            round_number INTEGER NOT NULL,
            title VARCHAR(200) NOT NULL,
            focus_area VARCHAR(100) NOT NULL,
            description VARCHAR(500),
            total_questions INTEGER NOT NULL DEFAULT 30,
            time_limit_minutes INTEGER NOT NULL DEFAULT 60,
            passing_score REAL NOT NULL DEFAULT 60.0,
            test_file_path VARCHAR(300) NOT NULL,
            prerequisite_rounds JSONB NOT NULL DEFAULT '[]'::jsonb,
            unlock_condition JSONB,
            is_active BOOLEAN NOT NULL DEFAULT true,
            created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now(),
            updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now(),
            CONSTRAINT uq_department_round UNIQUE (department, round_number)
        );
        """,
        
        # 인덱스 생성
        "CREATE INDEX IF NOT EXISTS ix_student_diagnosis_progress_user_id ON student_diagnosis_progress (user_id);",
        "CREATE INDEX IF NOT EXISTS ix_student_diagnosis_progress_department ON student_diagnosis_progress (department);",
        "CREATE INDEX IF NOT EXISTS ix_student_diagnosis_progress_current_round ON student_diagnosis_progress (current_round);",
        "CREATE INDEX IF NOT EXISTS ix_diagnosis_round_config_department ON diagnosis_round_config (department);",
        "CREATE INDEX IF NOT EXISTS ix_diagnosis_round_config_round_number ON diagnosis_round_config (round_number);",
        
        # 업데이트 트리거 함수 생성
        """
        CREATE OR REPLACE FUNCTION update_updated_at_column()
        RETURNS TRIGGER AS $$
        BEGIN
            NEW.updated_at = now();
            RETURN NEW;
        END;
        $$ language 'plpgsql';
        """,
        
        # student_diagnosis_progress 업데이트 트리거
        """
        DROP TRIGGER IF EXISTS update_student_diagnosis_progress_updated_at ON student_diagnosis_progress;
        CREATE TRIGGER update_student_diagnosis_progress_updated_at
            BEFORE UPDATE ON student_diagnosis_progress
            FOR EACH ROW
            EXECUTE FUNCTION update_updated_at_column();
        """,
        
        # diagnosis_round_config 업데이트 트리거
        """
        DROP TRIGGER IF EXISTS update_diagnosis_round_config_updated_at ON diagnosis_round_config;
        CREATE TRIGGER update_diagnosis_round_config_updated_at
            BEFORE UPDATE ON diagnosis_round_config
            FOR EACH ROW
            EXECUTE FUNCTION update_updated_at_column();
        """,
    ]
    
    print("🚀 학생 진단테스트 차수 진행 상황 테이블 생성 시작...")
    
    try:
        with engine.connect() as connection:
            for i, sql in enumerate(sql_commands, 1):
                print(f"📝 {i}/{len(sql_commands)} 실행 중...")
                connection.execute(text(sql))
                connection.commit()
        
        print("✅ 모든 테이블 및 인덱스 생성 완료!")
        return True
        
    except Exception as e:
        print(f"❌ 테이블 생성 실패: {e}")
        return False

def insert_initial_config():
    """초기 진단테스트 차수별 설정 데이터 삽입"""
    
    print("📊 초기 진단테스트 설정 데이터 삽입 시작...")
    
    # 물리치료학과 설정
    physics_therapy_configs = [
        (1, "물리치료학과 1차 - 물리치료학 기초", "물리치료학 기초", "기본 개념과 기초 의학", "data/departments/medical/diagnostic_test_physics_therapy_round1.json"),
        (2, "물리치료학과 2차 - 운동치료학", "운동치료학", "운동치료 원리와 기법", "data/departments/medical/diagnostic_test_physics_therapy_round2.json"),
        (3, "물리치료학과 3차 - 신경계 물리치료", "신경계 물리치료", "중추신경계 및 말초신경계 질환", "data/departments/medical/diagnostic_test_physics_therapy_round3.json"),
        (4, "물리치료학과 4차 - 근골격계 물리치료", "근골격계 물리치료", "근골격계 손상 및 기능장애", "data/departments/medical/diagnostic_test_physics_therapy_round4.json"),
        (5, "물리치료학과 5차 - 심폐 물리치료", "심폐 물리치료", "심장 및 폐 질환 재활", "data/departments/medical/diagnostic_test_physics_therapy_round5.json"),
        (6, "물리치료학과 6차 - 소아 물리치료", "소아 물리치료", "소아 발달 및 신경발달치료", "data/departments/medical/diagnostic_test_physics_therapy_round6.json"),
        (7, "물리치료학과 7차 - 노인 물리치료", "노인 물리치료", "노인성 질환 및 기능 저하", "data/departments/medical/diagnostic_test_physics_therapy_round7.json"),
        (8, "물리치료학과 8차 - 스포츠 물리치료", "스포츠 물리치료", "스포츠 손상 예방 및 재활", "data/departments/medical/diagnostic_test_physics_therapy_round8.json"),
        (9, "물리치료학과 9차 - 정형외과 물리치료", "정형외과 물리치료", "수술 전후 재활 및 기능회복", "data/departments/medical/diagnostic_test_physics_therapy_round9.json"),
        (10, "물리치료학과 10차 - 종합 평가", "종합 평가", "모든 영역 종합 평가", "data/departments/medical/diagnostic_test_physics_therapy_round10.json"),
    ]
    
    # 작업치료학과 설정
    occupational_therapy_configs = [
        (1, "작업치료학과 1차 - 작업치료학 기초", "작업치료학 기초", "기본 개념과 기초 의학", "data/departments/medical/diagnostic_test_occupational_therapy_round1.json"),
        (2, "작업치료학과 2차 - 일상생활활동(ADL)", "일상생활활동(ADL)", "일상생활활동 평가 및 훈련", "data/departments/medical/diagnostic_test_occupational_therapy_round2.json"),
        (3, "작업치료학과 3차 - 인지재활치료", "인지재활치료", "인지기능 평가 및 재활치료", "data/departments/medical/diagnostic_test_occupational_therapy_round3.json"),
        (4, "작업치료학과 4차 - 작업수행분석", "작업수행분석", "작업과 활동의 분석 및 적용", "data/departments/medical/diagnostic_test_occupational_therapy_round4.json"),
        (5, "작업치료학과 5차 - 정신사회작업치료", "정신사회작업치료", "정신건강 및 사회적 기능 향상", "data/departments/medical/diagnostic_test_occupational_therapy_round5.json"),
        (6, "작업치료학과 6차 - 소아작업치료", "소아작업치료", "소아 발달 및 감각통합치료", "data/departments/medical/diagnostic_test_occupational_therapy_round6.json"),
        (7, "작업치료학과 7차 - 신체장애작업치료", "신체장애작업치료", "신체장애 환자의 기능 회복", "data/departments/medical/diagnostic_test_occupational_therapy_round7.json"),
        (8, "작업치료학과 8차 - 감각통합치료", "감각통합치료", "감각통합 이론 및 치료 기법", "data/departments/medical/diagnostic_test_occupational_therapy_round8.json"),
        (9, "작업치료학과 9차 - 보조공학", "보조공학", "보조기구 및 환경 적응", "data/departments/medical/diagnostic_test_occupational_therapy_round9.json"),
        (10, "작업치료학과 10차 - 종합 평가", "종합 평가", "모든 영역 종합 평가", "data/departments/medical/diagnostic_test_occupational_therapy_round10.json"),
    ]
    
    insert_sql = """
        INSERT INTO diagnosis_round_config 
        (department, round_number, title, focus_area, description, test_file_path, prerequisite_rounds) 
        VALUES (%(department)s, %(round_number)s, %(title)s, %(focus_area)s, %(description)s, %(test_file_path)s, %(prerequisite_rounds)s::jsonb)
        ON CONFLICT (department, round_number) DO UPDATE SET
            title = EXCLUDED.title,
            focus_area = EXCLUDED.focus_area,
            description = EXCLUDED.description,
            test_file_path = EXCLUDED.test_file_path,
            updated_at = now();
    """
    
    try:
        with engine.connect() as connection:
            # 물리치료학과 설정 삽입
            for round_num, title, focus_area, description, file_path in physics_therapy_configs:
                prerequisite = str([round_num - 1] if round_num > 1 else []).replace("'", '"')
                specific_sql = f"""
                    INSERT INTO diagnosis_round_config 
                    (department, round_number, title, focus_area, description, test_file_path, prerequisite_rounds) 
                    VALUES ('물리치료학과', {round_num}, '{title}', '{focus_area}', '{description}', '{file_path}', '{prerequisite}'::jsonb)
                    ON CONFLICT (department, round_number) DO UPDATE SET
                        title = EXCLUDED.title,
                        focus_area = EXCLUDED.focus_area,
                        description = EXCLUDED.description,
                        test_file_path = EXCLUDED.test_file_path,
                        updated_at = now();
                """
                connection.execute(text(specific_sql))
                print(f"  ✅ 물리치료학과 {round_num}차 설정 완료")
            
            # 작업치료학과 설정 삽입
            for round_num, title, focus_area, description, file_path in occupational_therapy_configs:
                prerequisite = str([round_num - 1] if round_num > 1 else []).replace("'", '"')
                specific_sql = f"""
                    INSERT INTO diagnosis_round_config 
                    (department, round_number, title, focus_area, description, test_file_path, prerequisite_rounds) 
                    VALUES ('작업치료학과', {round_num}, '{title}', '{focus_area}', '{description}', '{file_path}', '{prerequisite}'::jsonb)
                    ON CONFLICT (department, round_number) DO UPDATE SET
                        title = EXCLUDED.title,
                        focus_area = EXCLUDED.focus_area,
                        description = EXCLUDED.description,
                        test_file_path = EXCLUDED.test_file_path,
                        updated_at = now();
                """
                connection.execute(text(specific_sql))
                print(f"  ✅ 작업치료학과 {round_num}차 설정 완료")
            
            connection.commit()
        
        print("✅ 초기 설정 데이터 삽입 완료!")
        return True
        
    except Exception as e:
        print(f"❌ 초기 데이터 삽입 실패: {e}")
        return False

def verify_tables():
    """테이블 생성 확인"""
    
    print("🔍 테이블 생성 확인 중...")
    
    verification_queries = [
        "SELECT COUNT(*) FROM student_diagnosis_progress;",
        "SELECT COUNT(*) FROM diagnosis_round_config;",
        "SELECT department, COUNT(*) as round_count FROM diagnosis_round_config GROUP BY department;",
    ]
    
    try:
        with engine.connect() as connection:
            for query in verification_queries:
                result = connection.execute(text(query))
                rows = result.fetchall()
                print(f"📊 {query}")
                for row in rows:
                    print(f"   결과: {row}")
        
        print("✅ 테이블 검증 완료!")
        return True
        
    except Exception as e:
        print(f"❌ 테이블 검증 실패: {e}")
        return False

def main():
    """메인 실행 함수"""
    print("🏥 학생 진단테스트 차수 진행 상황 시스템 설정")
    print("=" * 60)
    
    # 1. 테이블 생성
    if not create_tables():
        print("❌ 테이블 생성 실패. 종료합니다.")
        return False
    
    # 2. 초기 데이터 삽입
    if not insert_initial_config():
        print("❌ 초기 데이터 삽입 실패. 종료합니다.")
        return False
    
    # 3. 테이블 검증
    if not verify_tables():
        print("❌ 테이블 검증 실패. 종료합니다.")
        return False
    
    print("\n🎉 학생 진단테스트 차수 진행 상황 시스템 설정 완료!")
    print("\n📋 설정된 내용:")
    print("   - student_diagnosis_progress 테이블 (학생별 진행 상황)")
    print("   - diagnosis_round_config 테이블 (차수별 설정)")
    print("   - 물리치료학과 1차~10차 설정")
    print("   - 작업치료학과 1차~10차 설정")
    
    return True

if __name__ == "__main__":
    main() 