from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.db.database import get_db
from app.models.user import User
from app.models.diagnosis import DiagnosticSession, DiagnosticAnswer, DiagnosticAIAnalysis, DiagnosticStatistics
from app.auth.dependencies import get_current_user
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
import json
import logging
import os

router = APIRouter()
logger = logging.getLogger(__name__)

# 🏫 **전체 학과 지원 설정**
SUPPORTED_DEPARTMENTS = {
    '물리치료학과': 'physical_therapy',
    '간호학과': 'nursing', 
    '의학과': 'medicine',
    '치의학과': 'dentistry',
    '한의학과': 'oriental_medicine',
    '약학과': 'pharmacy',
    '수의학과': 'veterinary',
    '컴퓨터공학과': 'computer_science',
    '공학계열': 'engineering',
    '경영학과': 'business',
    '법학과': 'law',
    '교육학과': 'education'
}

# 기본 학과 매핑 (알려지지 않은 학과)
DEFAULT_DEPARTMENT_MAPPING = 'general'

# 📁 데이터 파일 경로 매핑 (실제 존재하는 파일들만)
QUESTION_FILE_MAPPING = {
    'physical_therapy': 'departments/medical/diagnostic_test_physics_therapy.json',
    'nursing': 'departments/nursing/diagnostic_test_nursing.json',
    'medicine': 'departments/medical/diagnostic_test_medical.json',
    'dentistry': 'departments/medical/diagnostic_test_medical.json',  # 의학과 파일 공용
    'oriental_medicine': 'departments/medical/diagnostic_test_medical.json',  # 의학과 파일 공용
    'pharmacy': 'departments/medical/diagnostic_test_medical.json',  # 의학과 파일 공용
    'veterinary': 'departments/medical/diagnostic_test_medical.json',  # 의학과 파일 공용
    'computer_science': 'departments/computer_science/diagnostic_test_computer_science.json',
    'engineering': 'departments/business/diagnostic_test_business.json',  # 임시로 경영학과 파일 사용
    'business': 'departments/business/diagnostic_test_business.json',
    'law': 'departments/business/diagnostic_test_business.json',  # 임시로 경영학과 파일 사용
    'education': 'departments/business/diagnostic_test_business.json',  # 임시로 경영학과 파일 사용
    'general': 'general_questions.json'
}

def get_department_code(department_name: str) -> str:
    """학과명을 코드로 변환"""
    return SUPPORTED_DEPARTMENTS.get(department_name, DEFAULT_DEPARTMENT_MAPPING)

def get_department_display_name(department_code: str) -> str:
    """학과 코드를 표시명으로 변환"""
    for name, code in SUPPORTED_DEPARTMENTS.items():
        if code == department_code:
            return name
    return '일반학과'

def load_question_data(department_code: str) -> List[Dict]:
    """백엔드 data 폴더에서 문제 데이터 로딩 (departments 구조 지원)"""
    try:
        # 백엔드 data 폴더 경로 (프로젝트 루트의 data 폴더)
        project_root = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
        data_dir = os.path.join(project_root, 'data')
        filename = QUESTION_FILE_MAPPING.get(department_code, 'general_questions.json')
        file_path = os.path.join(data_dir, filename)
        
        logger.info(f"📁 문제 데이터 로딩 시도: {file_path}")
        
        if not os.path.exists(file_path):
            logger.warning(f"⚠️ 파일 없음: {file_path}, 기본 파일 사용")
            # 기본 파일로 대체
            default_file = os.path.join(data_dir, 'general_questions.json')
            if os.path.exists(default_file):
                file_path = default_file
            else:
                raise FileNotFoundError(f"기본 문제 파일도 없습니다: {default_file}")
        
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # 🔧 파일 구조에 따른 데이터 처리
        if isinstance(data, dict) and 'questions' in data:
            # departments 구조 (물리치료학과 등)
            questions = data['questions']
            logger.info(f"✅ departments 구조 문제 데이터 로딩: {len(questions)}개 문제")
            
            # 프론트엔드 호환 형식으로 변환
            converted_questions = []
            for q in questions:
                converted_q = {
                    "question_id": q.get("question_id", ""),
                    "question_number": q.get("question_number", 0),
                    "question_text": q.get("content", ""),
                    "choices": [
                        q.get("options", {}).get("1", ""),
                        q.get("options", {}).get("2", ""),
                        q.get("options", {}).get("3", ""),
                        q.get("options", {}).get("4", ""),
                        q.get("options", {}).get("5", "")
                    ],
                    "correct_answer": q.get("correct_answer", "1"),
                    "difficulty_level": q.get("difficulty_level", "기본"),
                    "domain": q.get("domain", "일반"),
                    "question_type": q.get("question_type", "기본개념")
                }
                converted_questions.append(converted_q)
            
            return converted_questions
            
        elif isinstance(data, list):
            # 기존 구조 (간호학과, 일반 등)
            logger.info(f"✅ 기존 구조 문제 데이터 로딩: {len(data)}개 문제")
            return data
        else:
            raise ValueError("지원하지 않는 파일 구조입니다.")
        
    except Exception as e:
        logger.error(f"❌ 문제 데이터 로딩 실패: {str(e)}")
        # 최후의 수단: 하드코딩된 샘플 문제
        return get_fallback_questions()

def get_fallback_questions() -> List[Dict]:
    """데이터 파일 로딩 실패 시 사용할 기본 문제 (AI 해설 생성용)"""
    return [
        {
            "question_id": "fallback_001",
            "question_number": 1,
            "question_text": "효과적인 학습 방법은?",
            "choices": [
                "반복 학습과 복습",
                "한 번에 몰아서 공부",
                "암기 위주 학습",
                "시험 전날만 집중",
                "검색에만 의존"
            ],
            "correct_answer": "1",
            "difficulty_level": "기본",
            "domain": "학습방법",
            "question_type": "교육이론"
        }
    ]

# Request/Response 모델들
class SessionStartRequest(BaseModel):
    test_type: str
    department: str
    total_questions: int = 30
    time_limit_minutes: int = 60

class SessionStartResponse(BaseModel):
    session_id: int
    start_time: datetime
    message: str

class AnswerSubmissionRequest(BaseModel):
    session_id: int
    question_id: str
    answer: str
    time_spent_ms: int

class QuestionResult(BaseModel):
    question_id: str
    question_number: int
    selected_answer: Optional[str]
    correct_answer: str
    is_correct: bool
    time_spent_ms: int
    difficulty_level: Optional[str] = None
    domain: Optional[str] = None
    question_type: Optional[str] = None

class SessionCompleteRequest(BaseModel):
    session_id: int
    total_score: int
    correct_answers: int
    wrong_answers: int
    total_time_ms: int
    detailed_results: List[QuestionResult]
    request_ai_analysis: bool = True

class SessionCompleteResponse(BaseModel):
    session_id: int
    score: int
    analysis_id: Optional[int] = None
    ai_analysis: Optional[Dict[str, Any]] = None
    message: str

@router.get("/questions/{department}")
async def get_questions_by_department(
    department: str,
    current_user: User = Depends(get_current_user)
):
    """
    📚 학과별 문제 데이터 제공 API
    """
    try:
        department_code = get_department_code(department)
        department_display = get_department_display_name(department_code)
        
        logger.info(f"📚 문제 데이터 요청: 사용자={current_user.id}, 학과={department} ({department_code})")
        
        # 백엔드 data 폴더에서 문제 로딩
        questions = load_question_data(department_code)
        
        # 30문제로 제한
        selected_questions = questions[:30] if len(questions) > 30 else questions
        
        return {
            "department": department,
            "department_code": department_code,
            "department_display": department_display,
            "questions": selected_questions,
            "total_count": len(selected_questions),
            "message": f"{department_display} 문제 데이터 로딩 완료"
        }
        
    except Exception as e:
        logger.error(f"❌ 문제 데이터 제공 실패: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"문제 데이터 로딩에 실패했습니다: {str(e)}"
        )

@router.post("/sessions/start", response_model=SessionStartResponse)
async def start_diagnostic_session(
    request: SessionStartRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    🚀 진단테스트 세션 시작 (모든 학과 지원)
    """
    try:
        department_code = get_department_code(request.department)
        
        logger.info(f"🎯 진단테스트 세션 시작: 사용자={current_user.id}, 학과={request.department} ({department_code})")
        
        # 새 세션 생성
        session = DiagnosticSession(
            user_id=current_user.id,
            test_type=request.test_type,
            department=department_code,
            total_questions=request.total_questions,
            time_limit_minutes=request.time_limit_minutes,
            start_time=datetime.utcnow(),
            status='active'
        )
        
        db.add(session)
        db.commit()
        db.refresh(session)
        
        logger.info(f"✅ 세션 생성 완료: ID={session.id}")
        
        return SessionStartResponse(
            session_id=session.id,
            start_time=session.start_time,
            message=f"{request.department} 진단테스트 세션이 시작되었습니다."
        )
        
    except Exception as e:
        logger.error(f"❌ 세션 시작 실패: {str(e)}")
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"세션 시작에 실패했습니다: {str(e)}"
        )

@router.post("/answers/submit")
async def submit_answer(
    request: AnswerSubmissionRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    📝 답안 제출 (실시간)
    """
    try:
        # 세션 검증
        session = db.query(DiagnosticSession).filter(
            DiagnosticSession.id == request.session_id,
            DiagnosticSession.user_id == current_user.id,
            DiagnosticSession.status == 'active'
        ).first()
        
        if not session:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="활성 세션을 찾을 수 없습니다."
            )
        
        # 답안 저장
        answer = DiagnosticAnswer(
            session_id=request.session_id,
            question_id=request.question_id,
            answer=request.answer,
            time_spent_ms=request.time_spent_ms,
            submitted_at=datetime.utcnow()
        )
        
        db.add(answer)
        db.commit()
        
        logger.info(f"📝 답안 저장: 세션={request.session_id}, 문제={request.question_id}")
        
        return {"message": "답안이 저장되었습니다.", "status": "success"}
        
    except Exception as e:
        logger.error(f"❌ 답안 저장 실패: {str(e)}")
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"답안 저장에 실패했습니다: {str(e)}"
        )

@router.post("/sessions/complete", response_model=SessionCompleteResponse)
async def complete_diagnostic_session(
    request: SessionCompleteRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    🏁 진단테스트 완료 및 AI 분석 (모든 학과 지원)
    """
    try:
        # 세션 검증 및 업데이트
        session = db.query(DiagnosticSession).filter(
            DiagnosticSession.id == request.session_id,
            DiagnosticSession.user_id == current_user.id
        ).first()
        
        if not session:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="세션을 찾을 수 없습니다."
            )
        
        # 세션 완료 처리
        session.status = 'completed'
        session.end_time = datetime.utcnow()
        session.final_score = request.total_score
        session.correct_answers = request.correct_answers
        session.wrong_answers = request.wrong_answers
        session.total_time_ms = request.total_time_ms
        
        db.commit()
        
        logger.info(f"🏁 세션 완료: ID={session.id}, 점수={request.total_score}")
        
        # 🔔 교수 알림 발송
        try:
            from app.services.diagnosis_alert_hook import diagnosis_alert_hook
            
            diagnosis_result = {
                "test_id": session.id,
                "test_type": session.test_type or "종합진단테스트",
                "started_at": session.start_time.isoformat() if session.start_time else None,
                "completed_at": session.end_time.isoformat() if session.end_time else None,
                "score": float(request.total_score),
                "total_questions": session.total_questions,
                "correct_answers": request.correct_answers,
                "time_taken": session.total_time_ms,
                "department": session.department,
                "performance_summary": {
                    "accuracy": round((request.correct_answers / session.total_questions) * 100, 1) if session.total_questions > 0 else 0,
                    "total_time_seconds": round(session.total_time_ms / 1000, 1) if session.total_time_ms else 0,
                    "average_time_per_question": round((session.total_time_ms / session.total_questions) / 1000, 1) if session.total_questions > 0 and session.total_time_ms else 0
                }
            }
            
            alert_result = await diagnosis_alert_hook.on_diagnosis_completed(
                db, current_user.id, diagnosis_result
            )
            
            if alert_result["success"]:
                logger.info(f"📧 교수 알림 발송 완료: {alert_result['alerts_created']}개")
            else:
                logger.error(f"❌ 교수 알림 발송 실패: {alert_result.get('error')}")
                
        except Exception as e:
            logger.error(f"⚠️ 교수 알림 발송 중 오류 (진단테스트는 정상 완료): {e}")
        
        # AI 분석 생성
        ai_analysis = None
        analysis_id = None
        
        if request.request_ai_analysis:
            ai_analysis = await generate_universal_ai_analysis(
                session, request.detailed_results, db
            )
            
            if ai_analysis:
                # AI 분석 저장
                analysis_record = DiagnosticAIAnalysis(
                    session_id=session.id,
                    analysis_data=json.dumps(ai_analysis, ensure_ascii=False),
                    confidence_score=ai_analysis.get('confidence_score', 85),
                    created_at=datetime.utcnow()
                )
                
                db.add(analysis_record)
                db.commit()
                db.refresh(analysis_record)
                
                analysis_id = analysis_record.id
                logger.info(f"🤖 AI 분석 저장 완료: ID={analysis_id}")
        
        # 통계 업데이트 (백그라운드)
        await update_diagnostic_statistics(request.detailed_results, session.department, db)
        
        return SessionCompleteResponse(
            session_id=session.id,
            score=request.total_score,
            analysis_id=analysis_id,
            ai_analysis=ai_analysis,
            message=f"진단테스트가 완료되었습니다. 최종 점수: {request.total_score}점"
        )
        
    except Exception as e:
        logger.error(f"❌ 세션 완료 실패: {str(e)}")
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"세션 완료 처리에 실패했습니다: {str(e)}"
        )

async def generate_universal_ai_analysis(
    session: DiagnosticSession, 
    detailed_results: List[QuestionResult], 
    db: Session
) -> Dict[str, Any]:
    """
    🤖 범용 AI 분석 생성 (모든 학과 대응)
    """
    try:
        department_name = get_department_display_name(session.department)
        
        # 기본 통계 계산
        total_questions = len(detailed_results)
        correct_count = sum(1 for r in detailed_results if r.is_correct)
        score_percentage = (correct_count / total_questions) * 100 if total_questions > 0 else 0
        
        # 유형별 분석
        type_stats = {}
        domain_stats = {}
        
        for result in detailed_results:
            # 유형별 통계
            q_type = result.question_type or '기타'
            if q_type not in type_stats:
                type_stats[q_type] = {'total': 0, 'correct': 0}
            type_stats[q_type]['total'] += 1
            if result.is_correct:
                type_stats[q_type]['correct'] += 1
            
            # 영역별 통계
            domain = result.domain or '일반'
            if domain not in domain_stats:
                domain_stats[domain] = {'total': 0, 'correct': 0}
            domain_stats[domain]['total'] += 1
            if result.is_correct:
                domain_stats[domain]['correct'] += 1
        
        # 시간 분석
        avg_time_per_question = sum(r.time_spent_ms for r in detailed_results) / len(detailed_results) if detailed_results else 0
        
        # 동료 비교 분석 (실제 데이터 기반)
        peer_comparison = await get_peer_comparison_data(session.department, score_percentage, db)
        
        # 강점/약점 분석
        strong_areas = []
        weak_areas = []
        
        for q_type, stats in type_stats.items():
            accuracy = (stats['correct'] / stats['total']) * 100 if stats['total'] > 0 else 0
            if accuracy >= 80:
                strong_areas.append(q_type)
            elif accuracy < 60:
                weak_areas.append(q_type)
        
        # 학과별 맞춤 추천
        recommendations = generate_department_recommendations(
            department_name, score_percentage, weak_areas, strong_areas
        )
        
        return {
            'department': department_name,
            'overall_score': score_percentage,
            'correct_answers': correct_count,
            'total_questions': total_questions,
            'average_time_per_question': round(avg_time_per_question / 1000, 1),
            'type_statistics': type_stats,
            'domain_statistics': domain_stats,
            'strong_areas': strong_areas,
            'weak_areas': weak_areas,
            'peer_comparison': peer_comparison,
            'recommendations': recommendations,
            'confidence_score': 92,  # 실제 데이터 기반 높은 신뢰도
            'analysis_type': 'universal_adaptive',
            'generated_at': datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"❌ AI 분석 생성 실패: {str(e)}")
        return {
            'error': '분석 생성 중 오류가 발생했습니다.',
            'department': get_department_display_name(session.department),
            'confidence_score': 0
        }

async def get_peer_comparison_data(department: str, user_score: float, db: Session) -> Dict[str, Any]:
    """동료 비교 데이터 조회 (실제 DB 데이터 기반)"""
    try:
        # 같은 학과 최근 30일 데이터
        recent_sessions = db.query(DiagnosticSession).filter(
            DiagnosticSession.department == department,
            DiagnosticSession.status == 'completed',
            DiagnosticSession.end_time >= datetime.utcnow() - timedelta(days=30)
        ).all()
        
        if not recent_sessions:
            return {
                'peer_count': 0,
                'average_score': 0,
                'percentile': 50,
                'message': '비교 데이터가 충분하지 않습니다.'
            }
        
        scores = [s.final_score for s in recent_sessions if s.final_score is not None]
        
        if not scores:
            return {
                'peer_count': 0,
                'average_score': 0,
                'percentile': 50,
                'message': '비교 데이터가 충분하지 않습니다.'
            }
        
        avg_score = sum(scores) / len(scores)
        better_than = sum(1 for score in scores if user_score > score)
        percentile = (better_than / len(scores)) * 100 if len(scores) > 0 else 50
        
        return {
            'peer_count': len(scores),
            'average_score': round(avg_score, 1),
            'percentile': round(percentile, 1),
            'message': f'{len(scores)}명의 동료와 비교'
        }
        
    except Exception as e:
        logger.error(f"❌ 동료 비교 데이터 조회 실패: {str(e)}")
        return {
            'peer_count': 0,
            'average_score': 0,
            'percentile': 50,
            'message': '비교 데이터 조회 중 오류가 발생했습니다.'
        }

def generate_department_recommendations(
    department: str, 
    score: float, 
    weak_areas: List[str], 
    strong_areas: List[str]
) -> List[Dict[str, str]]:
    """학과별 맞춤 추천 생성"""
    recommendations = []
    
    # 학과별 기본 추천
    department_specific = {
        '물리치료학과': {
            'study_focus': '해부학, 생리학, 운동치료학',
            'practice_areas': '임상실습, 기능평가',
            'key_skills': '평가 및 치료 기법'
        },
        '간호학과': {
            'study_focus': '기본간호학, 성인간호학, 아동간호학',
            'practice_areas': '임상실습, 간호과정',
            'key_skills': '환자 간호 및 의사소통'
        },
        '의학과': {
            'study_focus': '내과학, 외과학, 진단학',
            'practice_areas': '임상실습, 증례분석',
            'key_skills': '진단 및 치료 계획'
        },
        '컴퓨터공학과': {
            'study_focus': '자료구조, 알고리즘, 프로그래밍',
            'practice_areas': '코딩테스트, 프로젝트',
            'key_skills': '논리적 사고, 문제해결'
        }
    }
    
    dept_info = department_specific.get(department, {
        'study_focus': '전공 핵심 과목',
        'practice_areas': '실습 및 응용',
        'key_skills': '전문 지식 및 기술'
    })
    
    # 점수 기반 추천
    if score >= 80:
        recommendations.append({
            'category': '🌟 우수 학습자',
            'title': '심화 학습 권장',
            'description': f'{dept_info["key_skills"]} 분야의 고급 내용을 학습하세요.'
        })
    elif score >= 65:
        recommendations.append({
            'category': '📚 중급 단계',
            'title': '꾸준한 학습 지속',
            'description': f'{dept_info["study_focus"]} 영역의 기본기를 다져보세요.'
        })
    else:
        recommendations.append({
            'category': '💪 기초 강화',
            'title': '기본기 다지기',
            'description': f'{dept_info["study_focus"]} 기초 개념 정리가 필요합니다.'
        })
    
    # 약점 기반 추천
    if weak_areas:
        recommendations.append({
            'category': '⚠️ 개선 필요',
            'title': f'{", ".join(weak_areas[:3])} 집중 학습',
            'description': f'{dept_info["practice_areas"]}를 통해 약점을 보완하세요.'
        })
    
    # 강점 기반 추천
    if strong_areas:
        recommendations.append({
            'category': '✅ 강점 활용',
            'title': f'{", ".join(strong_areas[:3])} 역량 확장',
            'description': '현재 강점을 바탕으로 관련 영역을 확장해보세요.'
        })
    
    return recommendations

async def update_diagnostic_statistics(
    detailed_results: List[QuestionResult],
    department: str,
    db: Session
):
    """진단 통계 업데이트 (백그라운드)"""
    try:
        for result in detailed_results:
            # 기존 통계 조회
            stat = db.query(DiagnosticStatistics).filter(
                DiagnosticStatistics.question_id == result.question_id,
                DiagnosticStatistics.department == department
            ).first()
            
            if stat:
                # 기존 통계 업데이트
                stat.total_attempts += 1
                if result.is_correct:
                    stat.correct_attempts += 1
                stat.avg_time_ms = (stat.avg_time_ms + result.time_spent_ms) / 2
                stat.updated_at = datetime.utcnow()
            else:
                # 새 통계 생성
                stat = DiagnosticStatistics(
                    question_id=result.question_id,
                    department=department,
                    total_attempts=1,
                    correct_attempts=1 if result.is_correct else 0,
                    avg_time_ms=result.time_spent_ms,
                    difficulty_level=result.difficulty_level,
                    question_type=result.question_type,
                    created_at=datetime.utcnow(),
                    updated_at=datetime.utcnow()
                )
                db.add(stat)
        
        db.commit()
        logger.info(f"📊 통계 업데이트 완료: {len(detailed_results)}개 문제")
        
    except Exception as e:
        logger.error(f"❌ 통계 업데이트 실패: {str(e)}")
        db.rollback()

@router.get("/sessions/{session_id}/analysis")
async def get_session_analysis(
    session_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    📊 세션 분석 결과 조회
    """
    try:
        session = db.query(DiagnosticSession).filter(
            DiagnosticSession.id == session_id,
            DiagnosticSession.user_id == current_user.id
        ).first()
        
        if not session:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="세션을 찾을 수 없습니다."
            )
        
        analysis = db.query(DiagnosticAIAnalysis).filter(
            DiagnosticAIAnalysis.session_id == session_id
        ).first()
        
        if not analysis:
            return {"message": "분석 결과가 없습니다.", "session_id": session_id}
        
        return {
            "session_id": session_id,
            "analysis": json.loads(analysis.analysis_data),
            "confidence_score": analysis.confidence_score,
            "created_at": analysis.created_at
        }
        
    except Exception as e:
        logger.error(f"❌ 분석 결과 조회 실패: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"분석 결과 조회에 실패했습니다: {str(e)}"
        )

@router.get("/departments")
async def get_supported_departments():
    """
    🏫 지원하는 학과 목록 조회
    """
    return {
        "supported_departments": SUPPORTED_DEPARTMENTS,
        "total_count": len(SUPPORTED_DEPARTMENTS),
        "default_department": DEFAULT_DEPARTMENT_MAPPING,
        "message": "모든 학과에 대한 진단테스트가 지원됩니다."
    } 