#!/usr/bin/env python3
"""
진단테스트 데이터베이스 저장 확인 스크립트
"""

import os
import sys
from datetime import datetime
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
import json

# 현재 디렉토리를 Python path에 추가
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.db.database import get_db, engine
from app.models.diagnosis import (
    DiagnosticSession, DiagnosticAnswer, DiagnosticAIAnalysis, 
    DiagnosticStatistics, SessionStatus
)

def check_database_connection():
    """데이터베이스 연결 확인"""
    print("🔍 데이터베이스 연결 확인 중...")
    try:
        with engine.connect() as conn:
            result = conn.execute(text("SELECT version()"))
            version = result.fetchone()[0]
            print(f"✅ PostgreSQL 연결 성공: {version}")
            return True
    except Exception as e:
        print(f"❌ 데이터베이스 연결 실패: {e}")
        return False

def check_diagnosis_tables():
    """진단테스트 관련 테이블 존재 확인"""
    print("\n📋 진단테스트 테이블 확인 중...")
    
    tables_to_check = [
        'diagnostic_sessions',
        'diagnostic_answers', 
        'diagnostic_ai_analysis',
        'diagnostic_statistics'
    ]
    
    try:
        with engine.connect() as conn:
            for table in tables_to_check:
                result = conn.execute(text(f"""
                    SELECT EXISTS (
                        SELECT FROM information_schema.tables 
                        WHERE table_name = '{table}'
                    )
                """))
                exists = result.fetchone()[0]
                status = "✅ 존재" if exists else "❌ 없음"
                print(f"  {table}: {status}")
                
                if exists:
                    # 테이블 행 수 확인
                    count_result = conn.execute(text(f"SELECT COUNT(*) FROM {table}"))
                    count = count_result.fetchone()[0]
                    print(f"    → 데이터 개수: {count}개")
        
        return True
    except Exception as e:
        print(f"❌ 테이블 확인 실패: {e}")
        return False

def check_diagnostic_sessions():
    """진단테스트 세션 데이터 확인"""
    print("\n🎯 진단테스트 세션 데이터 확인...")
    
    try:
        db = next(get_db())
        sessions = db.query(DiagnosticSession).order_by(DiagnosticSession.created_at.desc()).limit(10).all()
        
        if not sessions:
            print("📭 저장된 세션이 없습니다.")
            return
        
        print(f"📊 최근 세션 {len(sessions)}개:")
        for i, session in enumerate(sessions, 1):
            print(f"\n  {i}. 세션 ID: {session.session_id}")
            print(f"     사용자 ID: {session.user_id}")
            print(f"     테스트 타입: {session.test_type}")
            print(f"     학과: {session.department}")
            print(f"     문제 수: {session.total_questions}")
            print(f"     상태: {session.status}")
            print(f"     시작: {session.started_at}")
            print(f"     완료: {session.completed_at}")
            if session.total_score is not None:
                print(f"     점수: {session.total_score}점")
                print(f"     정답/오답: {session.correct_answers}/{session.wrong_answers}")
                print(f"     소요시간: {session.total_time_ms/1000:.1f}초" if session.total_time_ms else "N/A")
        
        db.close()
        
    except Exception as e:
        print(f"❌ 세션 데이터 확인 실패: {e}")

def check_diagnostic_answers(session_id=None):
    """진단테스트 답변 데이터 확인"""
    print("\n📝 진단테스트 답변 데이터 확인...")
    
    try:
        db = next(get_db())
        
        if session_id:
            answers = db.query(DiagnosticAnswer).filter(
                DiagnosticAnswer.session_id == session_id
            ).order_by(DiagnosticAnswer.question_number).all()
            print(f"🎯 세션 {session_id}의 답변 데이터:")
        else:
            # 최근 답변들 확인
            answers = db.query(DiagnosticAnswer).order_by(
                DiagnosticAnswer.created_at.desc()
            ).limit(20).all()
            print("📊 최근 답변 20개:")
        
        if not answers:
            print("📭 저장된 답변이 없습니다.")
            return
        
        # 통계 계산
        total_answers = len(answers)
        correct_count = sum(1 for answer in answers if answer.is_correct)
        accuracy = (correct_count / total_answers) * 100 if total_answers > 0 else 0
        
        print(f"\n📈 답변 통계:")
        print(f"  총 답변 수: {total_answers}개")
        print(f"  정답 수: {correct_count}개")
        print(f"  정답률: {accuracy:.1f}%")
        
        # 상세 답변 샘플 (최근 5개)
        print(f"\n📋 답변 상세 (최근 5개):")
        for i, answer in enumerate(answers[:5], 1):
            result_icon = "✅" if answer.is_correct else "❌"
            print(f"  {i}. 문제 {answer.question_number}: {result_icon}")
            print(f"     세션: {answer.session_id}")
            print(f"     선택답: {answer.selected_answer}, 정답: {answer.correct_answer}")
            print(f"     풀이시간: {answer.time_spent_ms/1000:.1f}초")
            if answer.difficulty_level:
                print(f"     난이도: {answer.difficulty_level}")
            if answer.domain:
                print(f"     영역: {answer.domain}")
            if answer.question_type:
                print(f"     유형: {answer.question_type}")
        
        db.close()
        return answers[0].session_id if answers else None
        
    except Exception as e:
        print(f"❌ 답변 데이터 확인 실패: {e}")
        return None

def check_ai_analysis():
    """AI 분석 결과 확인"""
    print("\n🤖 AI 분석 결과 확인...")
    
    try:
        db = next(get_db())
        analyses = db.query(DiagnosticAIAnalysis).order_by(
            DiagnosticAIAnalysis.created_at.desc()
        ).limit(5).all()
        
        if not analyses:
            print("📭 저장된 AI 분석 결과가 없습니다.")
            return
        
        print(f"📊 AI 분석 결과 {len(analyses)}개:")
        for i, analysis in enumerate(analyses, 1):
            print(f"\n  {i}. 세션 ID: {analysis.session_id}")
            print(f"     분석 타입: {analysis.analysis_type}")
            print(f"     AI 모델: {analysis.ai_model_version}")
            print(f"     신뢰도: {analysis.confidence_score}")
            print(f"     생성일: {analysis.created_at}")
            
            if analysis.weak_areas:
                print(f"     약한 영역: {analysis.weak_areas}")
            
            if analysis.recommendations:
                print(f"     권장사항: {analysis.recommendations[:2]}...")  # 처음 2개만
            
            # 분석 데이터 샘플
            if analysis.analysis_data:
                analysis_sample = analysis.analysis_data
                if isinstance(analysis_sample, dict):
                    print(f"     분석 데이터 키: {list(analysis_sample.keys())}")
                    
                    # 유형별 분석 결과
                    if 'type_analysis' in analysis_sample:
                        type_analysis = analysis_sample['type_analysis']
                        print(f"     유형별 정답률: {type_analysis}")
        
        db.close()
        
    except Exception as e:
        print(f"❌ AI 분석 데이터 확인 실패: {e}")

def check_statistics():
    """진단테스트 통계 확인"""
    print("\n📈 진단테스트 통계 확인...")
    
    try:
        db = next(get_db())
        stats = db.query(DiagnosticStatistics).order_by(
            DiagnosticStatistics.last_updated.desc()
        ).limit(10).all()
        
        if not stats:
            print("📭 저장된 통계가 없습니다.")
            return
        
        print(f"📊 문제별 통계 {len(stats)}개:")
        for i, stat in enumerate(stats, 1):
            accuracy = (stat.correct_attempts / stat.total_attempts * 100) if stat.total_attempts > 0 else 0
            print(f"\n  {i}. 문제 ID: {stat.question_id}")
            print(f"     테스트 타입: {stat.test_type}")
            print(f"     학과: {stat.department}")
            print(f"     총 시도: {stat.total_attempts}회")
            print(f"     정답률: {accuracy:.1f}%")
            print(f"     평균 시간: {stat.avg_time_ms/1000:.1f}초")
            print(f"     난이도 평가: {stat.difficulty_rating}/4.0")
            print(f"     마지막 업데이트: {stat.last_updated}")
        
        db.close()
        
    except Exception as e:
        print(f"❌ 통계 데이터 확인 실패: {e}")

def main():
    """메인 함수"""
    print("🔍 진단테스트 데이터베이스 저장 확인 시작")
    print("=" * 60)
    
    # 1. 데이터베이스 연결 확인
    if not check_database_connection():
        return
    
    # 2. 테이블 존재 확인
    if not check_diagnosis_tables():
        return
    
    # 3. 세션 데이터 확인
    check_diagnostic_sessions()
    
    # 4. 답변 데이터 확인
    latest_session_id = check_diagnostic_answers()
    
    # 5. AI 분석 결과 확인
    check_ai_analysis()
    
    # 6. 통계 데이터 확인  
    check_statistics()
    
    print("\n" + "=" * 60)
    print("✅ 진단테스트 데이터베이스 확인 완료!")
    
    if latest_session_id:
        print(f"\n🔗 특정 세션 상세 확인을 원하면:")
        print(f"   python check_diagnosis_data.py --session {latest_session_id}")

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='진단테스트 데이터베이스 확인')
    parser.add_argument('--session', help='특정 세션 ID의 상세 데이터 확인')
    
    args = parser.parse_args()
    
    if args.session:
        print(f"🎯 세션 {args.session} 상세 확인")
        print("=" * 60)
        check_diagnostic_answers(args.session)
    else:
        main() 