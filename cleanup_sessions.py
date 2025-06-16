#!/usr/bin/env python3
"""
기존 진단테스트 세션 정리 스크립트
- 사용자 33번의 잘못된 회차 세션들을 정리
- 1차 진단테스트 완료 상태 초기화
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from datetime import datetime
from app.database import get_db
from app.models.user import User
from app.models.diagnosis import DiagnosticSession, DiagnosticAnswer, DiagnosticAIAnalysis

def cleanup_user_sessions(user_id: int = 33):
    """사용자의 진단테스트 세션 정리"""
    
    # 데이터베이스 연결
    db = next(get_db())
    
    try:
        # 사용자 조회
        user = db.query(User).filter(User.id == user_id).first()
        
        if not user:
            print(f"❌ 사용자 ID {user_id}를 찾을 수 없습니다.")
            return
        
        print(f"👤 사용자 정보: {user.name} (ID: {user.id})")
        print(f"📊 현재 diagnosis_info: {user.diagnosis_info}")
        
        # 기존 진단테스트 세션들 조회
        sessions = db.query(DiagnosticSession).filter(
            DiagnosticSession.user_id == user_id
        ).all()
        
        print(f"📋 기존 세션 개수: {len(sessions)}")
        
        for session in sessions:
            print(f"  - 세션 {session.session_id}: {session.round_number}차, 상태: {session.status}")
        
        # 모든 세션 삭제
        if sessions:
            print(f"🗑️ 기존 세션들 삭제 중...")
            
            # 관련 답변들 먼저 삭제
            for session in sessions:
                answers = db.query(DiagnosticAnswer).filter(
                    DiagnosticAnswer.session_id == session.session_id
                ).all()
                for answer in answers:
                    db.delete(answer)
                
                # AI 분석 데이터 삭제
                ai_analyses = db.query(DiagnosticAIAnalysis).filter(
                    DiagnosticAIAnalysis.session_id == session.session_id
                ).all()
                for analysis in ai_analyses:
                    db.delete(analysis)
                
                # 세션 삭제
                db.delete(session)
            
            print(f"✅ {len(sessions)}개 세션 삭제 완료")
        
        # 사용자 진단테스트 완료 상태 초기화
        print(f"🔄 사용자 진단테스트 상태 초기화...")
        user.set_diagnostic_test_info(
            completed=False,
            completed_at=None,
            latest_score=None,
            test_count=0
        )
        user.updated_at = datetime.utcnow()
        
        # 데이터베이스 커밋
        db.commit()
        db.refresh(user)
        
        print(f"✅ 정리 완료!")
        print(f"📊 새로운 diagnosis_info: {user.diagnosis_info}")
        print(f"🎯 diagnostic_test_completed: {user.diagnostic_test_completed}")
        print(f"")
        print(f"🎉 이제 1차 진단테스트부터 다시 시작할 수 있습니다!")
        
    except Exception as e:
        print(f"❌ 오류 발생: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    print("🧹 진단테스트 세션 정리 시작...")
    cleanup_user_sessions()
    print("🎯 정리 완료! 이제 1차 진단테스트를 시작해보세요.") 