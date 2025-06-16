"""
진단테스트 API 엔드포인트
물리치료학과 학생 수준 진단을 위한 30문제 시스템
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import and_, func
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
import logging

from app.db.database import get_db
from app.models.user import User
from app.models.diagnostic_test import (
    DiagnosticTest, DiagnosticQuestion, DiagnosticSubmission, DiagnosticResponse
)
from app.auth.dependencies import get_current_user
from app.schemas.diagnostic_test import (
    DiagnosticTestInfo, DiagnosticQuestionResponse, 
    DiagnosticSubmissionCreate, DiagnosticSubmissionResponse,
    DiagnosticTestStart, DiagnosticAnswerSubmit
)

logger = logging.getLogger(__name__)
router = APIRouter()

@router.get("/test")
async def test_diagnostic_router():
    """진단테스트 라우터 테스트"""
    return {"message": "진단테스트 라우터가 정상 작동합니다!", "status": "ok"}

@router.get("/check-required/{department}", response_model=Dict[str, Any])
async def check_diagnostic_test_required(
    department: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    해당 학과 학생의 진단테스트 필요 여부 확인
    물리치료학과 학생은 반드시 진단테스트를 완료해야 서비스 이용 가능
    """
    try:
        # 해당 학과의 활성 진단테스트 조회
        diagnostic_test = db.query(DiagnosticTest).filter(
            and_(
                DiagnosticTest.department == department,
                DiagnosticTest.is_active == True
            )
        ).first()
        
        if not diagnostic_test:
            return {
                "required": False,
                "message": f"{department}는 진단테스트가 필요하지 않습니다.",
                "test_available": False
            }
        
        # 현재 사용자의 진단테스트 완료 여부 확인
        completed_submission = db.query(DiagnosticSubmission).filter(
            and_(
                DiagnosticSubmission.test_id == diagnostic_test.id,
                DiagnosticSubmission.user_id == current_user.id,
                DiagnosticSubmission.status == "completed"
            )
        ).first()
        
        if completed_submission:
            return {
                "required": False,
                "message": "진단테스트를 이미 완료했습니다.",
                "test_available": True,
                "completed": True,
                "completion_date": completed_submission.end_time,
                "level_classification": completed_submission.level_classification,
                "total_score": completed_submission.total_score
            }
        
        # 진행 중인 테스트 확인
        in_progress_submission = db.query(DiagnosticSubmission).filter(
            and_(
                DiagnosticSubmission.test_id == diagnostic_test.id,
                DiagnosticSubmission.user_id == current_user.id,
                DiagnosticSubmission.status == "in_progress"
            )
        ).first()
        
        return {
            "required": True,
            "message": f"{department} 학생은 진단테스트 완료가 필요합니다.",
            "test_available": True,
            "test_info": {
                "id": diagnostic_test.id,
                "title": diagnostic_test.title,
                "description": diagnostic_test.description,
                "total_questions": diagnostic_test.total_questions,
                "time_limit": diagnostic_test.time_limit
            },
            "in_progress": in_progress_submission is not None,
            "submission_id": in_progress_submission.id if in_progress_submission else None
        }
        
    except Exception as e:
        logger.error(f"진단테스트 필요 여부 확인 오류: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="진단테스트 확인 중 오류가 발생했습니다."
        )

@router.get("/start/{department}", response_model=DiagnosticTestStart)
async def start_diagnostic_test(
    department: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    진단테스트 시작
    새로운 세션 생성 또는 기존 진행 중인 세션 반환
    """
    try:
        # 해당 학과의 활성 진단테스트 조회
        diagnostic_test = db.query(DiagnosticTest).filter(
            and_(
                DiagnosticTest.department == department,
                DiagnosticTest.is_active == True
            )
        ).first()
        
        if not diagnostic_test:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"{department}에 대한 진단테스트가 없습니다."
            )
        
        # 이미 완료한 테스트인지 확인
        completed_submission = db.query(DiagnosticSubmission).filter(
            and_(
                DiagnosticSubmission.test_id == diagnostic_test.id,
                DiagnosticSubmission.user_id == current_user.id,
                DiagnosticSubmission.status == "completed"
            )
        ).first()
        
        if completed_submission:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="이미 진단테스트를 완료했습니다."
            )
        
        # 진행 중인 테스트 확인
        in_progress_submission = db.query(DiagnosticSubmission).filter(
            and_(
                DiagnosticSubmission.test_id == diagnostic_test.id,
                DiagnosticSubmission.user_id == current_user.id,
                DiagnosticSubmission.status == "in_progress"
            )
        ).first()
        
        if in_progress_submission:
            # 시간 만료 확인
            elapsed_time = datetime.utcnow() - in_progress_submission.start_time
            if elapsed_time.total_seconds() > diagnostic_test.time_limit * 60:
                # 시간 만료로 자동 제출
                in_progress_submission.status = "expired"
                in_progress_submission.end_time = datetime.utcnow()
                db.commit()
                
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="이전 진단테스트가 시간 만료되었습니다. 새로 시작해주세요."
                )
            
            submission = in_progress_submission
        else:
            # 새로운 제출 세션 생성
            submission = DiagnosticSubmission(
                test_id=diagnostic_test.id,
                user_id=current_user.id,
                status="in_progress",
                unanswered_count=diagnostic_test.total_questions
            )
            db.add(submission)
            db.commit()
            db.refresh(submission)
        
        # 문제들 조회 (번호 순으로 정렬)
        questions = db.query(DiagnosticQuestion).filter(
            DiagnosticQuestion.test_id == diagnostic_test.id
        ).order_by(DiagnosticQuestion.question_number).all()
        
        # 이미 답변한 문제들 조회
        answered_questions = {}
        if in_progress_submission:
            responses = db.query(DiagnosticResponse).filter(
                DiagnosticResponse.submission_id == submission.id
            ).all()
            
            for response in responses:
                answered_questions[response.question_id] = {
                    "user_answer": response.user_answer,
                    "is_correct": response.is_correct,
                    "answered_at": response.answered_at
                }
        
        # 응답 데이터 구성
        question_list = []
        for question in questions:
            question_data = {
                "id": question.id,
                "question_id": question.question_id,
                "question_number": question.question_number,
                "content": question.content,
                "options": question.options,
                "difficulty_level": question.difficulty_level,
                "domain": question.domain,
                "points": question.points
            }
            
            # 이미 답변한 문제라면 답변 정보 추가
            if question.id in answered_questions:
                question_data["answered"] = True
                question_data["user_answer"] = answered_questions[question.id]["user_answer"]
            else:
                question_data["answered"] = False
            
            question_list.append(question_data)
        
        # 남은 시간 계산
        elapsed_time = datetime.utcnow() - submission.start_time
        remaining_time = max(0, diagnostic_test.time_limit * 60 - elapsed_time.total_seconds())
        
        return {
            "submission_id": submission.id,
            "test_info": {
                "id": diagnostic_test.id,
                "title": diagnostic_test.title,
                "description": diagnostic_test.description,
                "total_questions": diagnostic_test.total_questions,
                "time_limit": diagnostic_test.time_limit
            },
            "questions": question_list,
            "remaining_time": int(remaining_time),
            "start_time": submission.start_time,
            "progress": {
                "answered": len(answered_questions),
                "unanswered": diagnostic_test.total_questions - len(answered_questions)
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"진단테스트 시작 오류: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="진단테스트 시작 중 오류가 발생했습니다."
        )

@router.post("/submit-answer", response_model=Dict[str, Any])
async def submit_answer(
    answer_data: DiagnosticAnswerSubmit,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    진단테스트 문제별 답안 제출
    """
    try:
        # 제출 세션 확인
        submission = db.query(DiagnosticSubmission).filter(
            and_(
                DiagnosticSubmission.id == answer_data.submission_id,
                DiagnosticSubmission.user_id == current_user.id,
                DiagnosticSubmission.status == "in_progress"
            )
        ).first()
        
        if not submission:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="유효하지 않은 제출 세션입니다."
            )
        
        # 시간 만료 확인
        diagnostic_test = submission.test
        elapsed_time = datetime.utcnow() - submission.start_time
        if elapsed_time.total_seconds() > diagnostic_test.time_limit * 60:
            submission.status = "expired"
            submission.end_time = datetime.utcnow()
            db.commit()
            
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="시간이 만료되었습니다."
            )
        
        # 문제 조회
        question = db.query(DiagnosticQuestion).filter(
            DiagnosticQuestion.id == answer_data.question_id
        ).first()
        
        if not question:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="문제를 찾을 수 없습니다."
            )
        
        # 기존 응답 확인
        existing_response = db.query(DiagnosticResponse).filter(
            and_(
                DiagnosticResponse.submission_id == submission.id,
                DiagnosticResponse.question_id == question.id
            )
        ).first()
        
        is_correct = answer_data.user_answer == question.correct_answer
        
        if existing_response:
            # 기존 응답 업데이트
            existing_response.user_answer = answer_data.user_answer
            existing_response.is_correct = is_correct
            existing_response.response_time = answer_data.response_time
            existing_response.answered_at = datetime.utcnow()
        else:
            # 새로운 응답 생성
            new_response = DiagnosticResponse(
                submission_id=submission.id,
                question_id=question.id,
                user_answer=answer_data.user_answer,
                is_correct=is_correct,
                response_time=answer_data.response_time
            )
            db.add(new_response)
        
        db.commit()
        
        return {
            "success": True,
            "is_correct": is_correct,
            "correct_answer": question.correct_answer,
            "message": "답안이 저장되었습니다."
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"답안 제출 오류: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="답안 제출 중 오류가 발생했습니다."
        )

@router.post("/complete", response_model=DiagnosticSubmissionResponse)
async def complete_diagnostic_test(
    submission_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    진단테스트 완료 및 결과 계산
    BKT/DKT 분석을 위한 기본 데이터 수집
    """
    try:
        # 제출 세션 확인
        submission = db.query(DiagnosticSubmission).filter(
            and_(
                DiagnosticSubmission.id == submission_id,
                DiagnosticSubmission.user_id == current_user.id,
                DiagnosticSubmission.status == "in_progress"
            )
        ).first()
        
        if not submission:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="유효하지 않은 제출 세션입니다."
            )
        
        diagnostic_test = submission.test
        
        # 모든 응답 조회
        responses = db.query(DiagnosticResponse).filter(
            DiagnosticResponse.submission_id == submission.id
        ).all()
        
        # 점수 계산
        total_score = 0.0
        correct_count = 0
        wrong_count = 0
        unanswered_count = diagnostic_test.total_questions - len(responses)
        
        for response in responses:
            question = response.question
            if response.is_correct:
                correct_count += 1
                total_score += question.points
            else:
                wrong_count += 1
        
        # 레벨 분류
        score_percentage = (total_score / 100) * 100  # 총점 100점 기준
        level_classification = _classify_level(score_percentage, diagnostic_test.scoring_criteria)
        
        # 진단 결과 구성
        diagnostic_result = {
            "score_percentage": score_percentage,
            "correct_rate": (correct_count / diagnostic_test.total_questions) * 100,
            "domain_analysis": _analyze_by_domain(responses, db),
            "difficulty_analysis": _analyze_by_difficulty(responses, db),
            "recommendations": _generate_recommendations(level_classification, responses, db)
        }
        
        # 제출 정보 업데이트
        submission.status = "completed"
        submission.end_time = datetime.utcnow()
        submission.total_score = total_score
        submission.correct_count = correct_count
        submission.wrong_count = wrong_count
        submission.unanswered_count = unanswered_count
        submission.level_classification = level_classification
        submission.diagnostic_result = diagnostic_result
        
        # TODO: BKT/DKT 분석 (향후 구현)
        submission.bkt_analysis = {"status": "pending"}
        submission.dkt_analysis = {"status": "pending"}
        submission.rnn_analysis = {"status": "pending"}
        
        db.commit()
        
        # 🔔 교수 알림 발송
        try:
            from app.services.diagnosis_alert_hook import diagnosis_alert_hook
            
            diagnosis_result_data = {
                "test_id": submission.id,
                "test_type": diagnostic_test.title or "진단테스트",
                "started_at": submission.start_time.isoformat() if submission.start_time else None,
                "completed_at": submission.end_time.isoformat() if submission.end_time else None,
                "score": float(score_percentage),
                "total_questions": diagnostic_test.total_questions,
                "correct_answers": correct_count,
                "time_taken": int((submission.end_time - submission.start_time).total_seconds() * 1000) if submission.end_time and submission.start_time else 0,
                "department": diagnostic_test.department,
                "level_classification": level_classification,
                "performance_summary": {
                    "accuracy": round((correct_count / diagnostic_test.total_questions) * 100, 1) if diagnostic_test.total_questions > 0 else 0,
                    "level": level_classification,
                    "total_time_seconds": int((submission.end_time - submission.start_time).total_seconds()) if submission.end_time and submission.start_time else 0
                }
            }
            
            alert_result = await diagnosis_alert_hook.on_diagnosis_completed(
                db, current_user.id, diagnosis_result_data
            )
            
            if alert_result["success"]:
                print(f"📧 교수 알림 발송 완료: {alert_result['alerts_created']}개")
            else:
                print(f"❌ 교수 알림 발송 실패: {alert_result.get('error')}")
                
        except Exception as e:
            print(f"⚠️ 교수 알림 발송 중 오류 (진단테스트는 정상 완료): {e}")
        
        return {
            "submission_id": submission.id,
            "total_score": total_score,
            "score_percentage": score_percentage,
            "correct_count": correct_count,
            "wrong_count": wrong_count,
            "unanswered_count": unanswered_count,
            "level_classification": level_classification,
            "diagnostic_result": diagnostic_result,
            "completion_time": submission.end_time,
            "can_access_service": True  # 진단테스트 완료로 서비스 이용 가능
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"진단테스트 완료 오류: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="진단테스트 완료 중 오류가 발생했습니다."
        )

def _classify_level(score_percentage: float, scoring_criteria: Dict[str, Any]) -> str:
    """점수에 따른 레벨 분류"""
    levels = scoring_criteria.get("level_classification", {})
    
    for level, criteria in levels.items():
        if score_percentage >= criteria.get("min_score", 0):
            return level
    
    return "미흡"

def _analyze_by_domain(responses: List[DiagnosticResponse], db: Session) -> Dict[str, Any]:
    """분야별 성과 분석"""
    domain_stats = {}
    
    for response in responses:
        question = response.question
        domain = question.domain or "기타"
        
        if domain not in domain_stats:
            domain_stats[domain] = {"correct": 0, "total": 0}
        
        domain_stats[domain]["total"] += 1
        if response.is_correct:
            domain_stats[domain]["correct"] += 1
    
    # 정확률 계산
    for domain, stats in domain_stats.items():
        stats["accuracy"] = (stats["correct"] / stats["total"]) * 100 if stats["total"] > 0 else 0
    
    return domain_stats

def _analyze_by_difficulty(responses: List[DiagnosticResponse], db: Session) -> Dict[str, Any]:
    """난이도별 성과 분석"""
    difficulty_stats = {}
    
    for response in responses:
        question = response.question
        difficulty = question.difficulty_level or "보통"
        
        if difficulty not in difficulty_stats:
            difficulty_stats[difficulty] = {"correct": 0, "total": 0}
        
        difficulty_stats[difficulty]["total"] += 1
        if response.is_correct:
            difficulty_stats[difficulty]["correct"] += 1
    
    # 정확률 계산
    for difficulty, stats in difficulty_stats.items():
        stats["accuracy"] = (stats["correct"] / stats["total"]) * 100 if stats["total"] > 0 else 0
    
    return difficulty_stats

def _generate_recommendations(level: str, responses: List[DiagnosticResponse], db: Session) -> List[str]:
    """레벨별 학습 권장사항 생성"""
    recommendations = []
    
    if level == "상급":
        recommendations.extend([
            "우수한 실력을 유지하기 위해 최신 연구 동향을 학습하세요.",
            "실무 중심의 고급 사례 연구를 권장합니다.",
            "후배들을 위한 멘토링 활동을 고려해보세요."
        ])
    elif level == "중급":
        recommendations.extend([
            "기본 개념을 응용하는 연습을 늘려보세요.",
            "실무 사례를 통한 문제 해결 능력을 키우세요.",
            "부족한 분야를 집중적으로 학습하세요."
        ])
    elif level == "하급":
        recommendations.extend([
            "기초 개념부터 체계적으로 다시 학습하세요.",
            "기본 문제부터 단계적으로 풀어보세요.",
            "교수님이나 선배에게 도움을 요청하세요."
        ])
    else:  # 미흡
        recommendations.extend([
            "전면적인 재학습이 필요합니다.",
            "기초 이론서부터 차근차근 공부하세요.",
            "학습 계획을 세워 꾸준히 노력하세요.",
            "스터디 그룹 참여를 권장합니다."
        ])
    
    return recommendations 