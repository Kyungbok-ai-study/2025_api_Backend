#!/usr/bin/env python3
"""
테스트 사용자 생성 스크립트
"""
import sys
import os
from datetime import datetime

# 프로젝트 루트를 Python 경로에 추가
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from sqlalchemy.orm import Session
from app.db.database import SessionLocal, engine
from app.models.user import User
from app.utils.auth import get_password_hash
from sqlalchemy import text

# 외래키 관련 모델들 import
try:
    from app.models.diagnosis import DiagnosticSession, DiagnosticAnswer, DiagnosticAIAnalysis
    from app.models.unified_diagnosis import DiagnosisSession as UnifiedDiagnosisSession, DiagnosisResponse
    from app.models.diagnostic_test import DiagnosticSubmission, DiagnosticResponse as OldDiagnosticResponse
except ImportError:
    # 모델이 없을 경우 None으로 설정
    DiagnosticSession = None
    DiagnosticAnswer = None
    DiagnosticAIAnalysis = None
    UnifiedDiagnosisSession = None
    DiagnosisResponse = None
    DiagnosticSubmission = None
    OldDiagnosticResponse = None

def delete_user_related_data(db: Session, user_ids: list):
    """사용자 관련 데이터를 외래키 순서에 맞게 삭제"""
    try:
        print(f"사용자 관련 데이터 삭제 중... (사용자 ID: {user_ids})")
        
        # SQL로 직접 삭제 (외래키 순서에 맞게)
        user_ids_str = ','.join(map(str, user_ids))
        
        # 모든 가능한 테이블에서 사용자 관련 데이터 삭제
        delete_queries = [
            # 1단계: 가장 하위 테이블들부터 삭제
            f"DELETE FROM diagnostic_ai_analysis WHERE session_id IN (SELECT session_id FROM diagnostic_sessions WHERE user_id IN ({user_ids_str}))",
            f"DELETE FROM diagnostic_answers WHERE session_id IN (SELECT session_id FROM diagnostic_sessions WHERE user_id IN ({user_ids_str}))",
            
            # 2단계: 응답 관련 테이블들
            f"DELETE FROM diagnosis_responses WHERE session_id IN (SELECT id FROM diagnosis_sessions WHERE user_id IN ({user_ids_str}))",
            f"DELETE FROM diagnostic_responses WHERE user_id IN ({user_ids_str})",
            f"DELETE FROM test_responses WHERE user_id IN ({user_ids_str})",
            
            # 3단계: 세션 관련 테이블들
            f"DELETE FROM diagnostic_sessions WHERE user_id IN ({user_ids_str})",
            f"DELETE FROM diagnosis_sessions WHERE user_id IN ({user_ids_str})",
            f"DELETE FROM test_sessions WHERE user_id IN ({user_ids_str})",
            
            # 4단계: 기타 사용자 관련 테이블들
            f"DELETE FROM diagnostic_submissions WHERE user_id IN ({user_ids_str})",
            f"DELETE FROM diagnosis_results WHERE user_id IN ({user_ids_str})",
            f"DELETE FROM learning_level_history WHERE user_id IN ({user_ids_str})",
            f"DELETE FROM student_diagnostic_history WHERE user_id IN ({user_ids_str})",
        ]
        
        for query in delete_queries:
            try:
                result = db.execute(text(query))
                if result.rowcount > 0:
                    table_name = query.split("FROM ")[1].split(" ")[0]
                    print(f"  - {table_name} {result.rowcount}개 삭제")
            except Exception as e:
                # 테이블이 없거나 컬럼이 없는 경우 무시
                pass
        
        # 마지막으로 남은 diagnostic_sessions 데이터 강제 삭제
        try:
            # 남은 데이터 확인
            remaining_sessions = db.execute(text(f"SELECT COUNT(*) FROM diagnostic_sessions WHERE user_id IN ({user_ids_str})")).scalar()
            if remaining_sessions > 0:
                print(f"  - 남은 diagnostic_sessions 데이터 {remaining_sessions}개 발견, 강제 삭제 시도")
                # 모든 관련 데이터를 한번에 삭제
                db.execute(text(f"DELETE FROM diagnostic_sessions WHERE user_id IN ({user_ids_str})"))
                print(f"  - diagnostic_sessions 강제 삭제 완료")
        except Exception as e:
            print(f"  - diagnostic_sessions 삭제 중 오류: {str(e)}")
        
        db.commit()
        print("관련 데이터 삭제 완료")
        
    except Exception as e:
        db.rollback()
        print(f"관련 데이터 삭제 중 오류 발생: {str(e)}")
        raise

def create_test_users():
    """테스트 사용자들 생성"""
    db = SessionLocal()
    
    try:
        # 테스트 사용자들 정의
        test_users = [
            {
                'user_id': 'test123',
                'password': 'testpass123',
                'name': '테스트 사용자',
                'email': 'test@kbu.ac.kr',
                'school': '경복대학교',
                'department': '물리치료학과',
                'student_id': 'test123',
                'admission_year': 2024,
                'phone_number': '010-1234-5678',
                'verification_method': 'student_id',
                'role': 'student'
            },
            {
                'user_id': 'physics_student',
                'password': 'physics123',
                'name': '물리치료 학생',
                'email': 'physics@kbu.ac.kr',
                'school': '경복대학교',
                'department': '물리치료학과',
                'student_id': 'physics_student',
                'admission_year': 2024,
                'phone_number': '010-1111-2222',
                'verification_method': 'student_id',
                'role': 'student'
            },
            {
                'user_id': 'nursing_student',
                'password': 'nursing123',
                'name': '간호학과 학생',
                'email': 'nursing@kbu.ac.kr',
                'school': '경복대학교',
                'department': '간호학과',
                'student_id': 'nursing_student',
                'admission_year': 2024,
                'phone_number': '010-2222-3333',
                'verification_method': 'student_id',
                'role': 'student'
            },
            {
                'user_id': 'ot_student',
                'password': 'ot123',
                'name': '작업치료 학생',
                'email': 'ot@kbu.ac.kr',
                'school': '경복대학교',
                'department': '작업치료학과',
                'student_id': 'ot_student',
                'admission_year': 2024,
                'phone_number': '010-3333-4444',
                'verification_method': 'student_id',
                'role': 'student'
            },
            {
                'user_id': 'admin',
                'password': 'admin123',
                'name': '관리자',
                'email': 'admin@kbu.ac.kr',
                'school': '경복대학교',
                'department': '관리부',
                'student_id': 'admin',
                'admission_year': 2020,
                'phone_number': '010-9999-0000',
                'verification_method': 'manual',
                'role': 'admin'
            },
            {
                'user_id': 'prof_physics',
                'password': 'prof123',
                'name': '김교수',
                'email': 'prof.kim@kbu.ac.kr',
                'school': '경복대학교',
                'department': '물리치료학과',
                'student_id': 'prof_physics',
                'admission_year': 2010,
                'phone_number': '010-5555-6666',
                'verification_method': 'manual',
                'role': 'professor'
            },
            {
                'user_id': 'prof_nursing',
                'password': 'prof123',
                'name': '이교수',
                'email': 'prof.lee@kbu.ac.kr',
                'school': '경복대학교',
                'department': '간호학과',
                'student_id': 'prof_nursing',
                'admission_year': 2008,
                'phone_number': '010-6666-7777',
                'verification_method': 'manual',
                'role': 'professor'
            },
            {
                'user_id': 'prof_ot',
                'password': 'prof123',
                'name': '박교수',
                'email': 'prof.park@kbu.ac.kr',
                'school': '경복대학교',
                'department': '작업치료학과',
                'student_id': 'prof_ot',
                'admission_year': 2012,
                'phone_number': '010-7777-8888',
                'verification_method': 'manual',
                'role': 'professor'
            }
        ]
        
        # 개별 사용자별로 존재 여부 확인 및 생성
        created_users = []
        skipped_users = []
        
        for user_data in test_users:
            # 기존 사용자 확인
            existing_user = db.query(User).filter(User.user_id == user_data['user_id']).first()
            
            if existing_user:
                skipped_users.append(user_data)
                print(f"⏭️  {user_data['user_id']} ({user_data['name']}) - 이미 존재함")
                continue
            
            # 기본 사용자 객체 생성
            user = User(
                user_id=user_data['user_id'],
                hashed_password=get_password_hash(user_data['password']),
                name=user_data['name'],
                email=user_data['email'],
                school=user_data['school'],
                role=user_data['role'],
                created_at=datetime.utcnow()
            )
            
            # JSON 필드들 설정
            user.set_profile_info(
                student_id=user_data['student_id'],
                department=user_data['department'],
                admission_year=user_data['admission_year'],
                phone_number=user_data['phone_number']
            )
            
            user.set_account_status(
                is_active=True,
                is_first_login=False
            )
            
            user.set_agreements(
                terms_agreed=True,
                privacy_agreed=True,
                privacy_optional_agreed=True,
                marketing_agreed=False
            )
            
            user.set_verification_status(
                identity_verified=True,
                age_verified=True,
                verification_method=user_data['verification_method']
            )
            
            user.set_diagnostic_test_info(
                completed=False
            )
            
            db.add(user)
            created_users.append(user_data)
            print(f"✅ {user_data['user_id']} ({user_data['name']}) - 생성됨")
        
        db.commit()
        
        print(f"\n📊 사용자 생성 결과:")
        print(f"✅ 새로 생성된 사용자: {len(created_users)}명")
        print(f"⏭️  이미 존재하는 사용자: {len(skipped_users)}명")
        
        if created_users:
            print(f"\n🎉 새로 생성된 계정들:")
            for user_data in created_users:
                print(f"  - 아이디: {user_data['user_id']}")
                print(f"    비밀번호: {user_data['password']}")
                print(f"    이름: {user_data['name']}")
                print(f"    학과: {user_data['department']}")
                print(f"    역할: {user_data['role']}")
                print()
        
        if skipped_users:
            print(f"⏭️  이미 존재하는 계정들:")
            for user_data in skipped_users:
                print(f"  - {user_data['user_id']} ({user_data['name']}, {user_data['department']}, {user_data['role']})")
        
        print("\n🎯 로그인 테스트:")
        print("  프론트엔드에서 다음 계정들로 로그인해보세요:")
        print("  📚 학생 계정: test123 / testpass123")  
        print("  👨‍🏫 교수 계정: prof_physics / prof123")
        print("  🛡️  관리자 계정: admin / admin123")
        
    except Exception as e:
        db.rollback()
        print(f"❌ 사용자 생성 중 오류 발생: {str(e)}")
        raise
    finally:
        db.close()

if __name__ == "__main__":
    print("=== 테스트 사용자 생성 스크립트 ===")
    create_test_users() 