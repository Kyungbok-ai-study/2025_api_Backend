from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import and_
from datetime import datetime
from app.auth.dependencies import get_current_user
from app.db.database import get_db
# permission_service 제거됨 - 간단한 권한 체크로 대체

def check_student_permission(user):
    """간단한 학생 권한 체크"""
    if not user:
        raise HTTPException(status_code=401, detail="인증이 필요합니다")
    if user.role not in ["student", "admin"]:
        raise HTTPException(status_code=403, detail="학생 권한이 필요합니다")
    return True
from app.models.question import Question
from app.models.user import User
import logging

logger = logging.getLogger(__name__)

router = APIRouter()

@router.get("/questions/{question_id}/explanation")
async def get_question_explanation(
    question_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    문제의 상세 AI 해설 조회
    - AI 챗봇 스타일의 상세 해설 제공
    - 문제 의도, 정답 해설, 핵심 개념, 실무 적용까지 포함
    """
    check_student_permission(current_user)
    
    # 문제 조회
    question = db.query(Question).filter(
        and_(
            Question.id == question_id,
            Question.approval_status == "approved",
            Question.is_active == True
        )
    ).first()
    
    if not question:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="문제를 찾을 수 없습니다."
        )
    
    try:
        # AI 해설이 이미 생성되어 있는지 확인
        if question.ai_explanation:
            explanation = question.ai_explanation
            confidence = question.explanation_confidence or 0.85
            generated_at = question.integration_completed_at or question.approved_at
        else:
            # AI 해설이 없으면 즉석에서 생성
            from app.services.enhanced_problem_generator import enhanced_generator
            
            # 학과 정보 추출 (문제 업로더 기준)
            uploader = db.query(User).filter(User.id == question.last_modified_by).first()
            department = uploader.department if uploader else "간호학과"
            
            explanation = await enhanced_generator._generate_chatbot_explanation(
                {
                    "question": question.content,
                    "correct_answer": question.correct_answer,
                    "type": question.question_type or "multiple_choice",
                    "difficulty": question.difficulty or "medium",
                    "main_concept": question.subject or "전문 개념",
                    "choices": question.options
                },
                department
            )
            
            # 생성된 해설을 저장 (다음에 빠른 조회 가능)
            question.ai_explanation = explanation
            question.explanation_confidence = 0.85
            question.integration_completed_at = datetime.now()
            db.commit()
            
            confidence = 0.85
            generated_at = datetime.now()
        
        # 학습 통계 업데이트 (해설 조회 기록)
        try:
            # 해설 조회 기록을 위한 간단한 로깅
            logger.info(f"학생 {current_user.id}가 문제 {question_id}의 AI 해설을 조회했습니다.")
            
            # 필요시 별도 테이블에 조회 기록을 저장할 수 있음
            # 예: explanation_views 테이블에 user_id, question_id, viewed_at 저장
            
        except Exception as e:
            logger.warning(f"해설 조회 기록 실패: {e}")
        
        return {
            "success": True,
            "question_info": {
                "id": question.id,
                "subject": question.subject,
                "difficulty": question.difficulty,
                "question_type": question.question_type
            },
            "explanation": {
                "content": explanation,
                "confidence_score": confidence,
                "generated_at": generated_at.isoformat() if generated_at else None,
                "style": "chatbot",
                "department_specialized": True
            },
            "study_guidance": {
                "estimated_study_time": "10-15분",
                "difficulty_level": question.difficulty or "medium",
                "recommended_actions": [
                    "해설을 천천히 읽어보세요",
                    "핵심 개념을 노트에 정리하세요", 
                    "실무 적용 사례를 상상해보세요",
                    "비슷한 문제를 더 풀어보세요"
                ]
            }
        }
        
    except Exception as e:
        logger.error(f"AI 해설 조회 실패 (문제 {question_id}): {e}")
        
        # 해설 생성 실패 시 기본 해설 제공
        basic_explanation = f"""
안녕하세요! 😊

**📋 문제 분석**
이 문제는 {question.subject or '전문 영역'}의 {question.difficulty or '보통'} 난이도 문제입니다.

**✅ 정답 해설**
정답: {question.correct_answer}

이 문제의 핵심은 전문적 지식의 정확한 이해와 적용입니다.

**💪 학습 팁**
기본 개념을 확실히 이해하고, 실제 사례에 적용해보는 연습이 중요합니다!

궁금한 점이 있으시면 교수님께 질문해 주세요! 🎓✨
        """
        
        return {
            "success": True,
            "question_info": {
                "id": question.id,
                "subject": question.subject,
                "difficulty": question.difficulty,
                "question_type": question.question_type
            },
            "explanation": {
                "content": basic_explanation.strip(),
                "confidence_score": 0.6,
                "generated_at": datetime.now().isoformat(),
                "style": "basic",
                "department_specialized": False
            },
            "study_guidance": {
                "estimated_study_time": "5-10분",
                "difficulty_level": question.difficulty or "medium",
                "recommended_actions": [
                    "기본 해설을 참고하세요",
                    "교수님께 추가 질문하세요",
                    "관련 자료를 찾아보세요"
                ]
            }
        }


@router.get("/questions/{question_id}/study-materials")
async def get_question_study_materials(
    question_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    문제 관련 학습 자료 추천
    - 유사한 문제들
    - 관련 개념의 다른 문제들
    - 학습 가이드
    """
    check_student_permission(current_user)
    
    # 문제 조회
    question = db.query(Question).filter(
        and_(
            Question.id == question_id,
            Question.approval_status == "approved",
            Question.is_active == True
        )
    ).first()
    
    if not question:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="문제를 찾을 수 없습니다."
        )
    
    try:
        # 유사한 문제 찾기 (같은 과목, 비슷한 난이도)
        similar_questions = db.query(Question).filter(
            and_(
                Question.id != question_id,
                Question.subject == question.subject,
                Question.approval_status == "approved",
                Question.is_active == True
            )
        ).limit(5).all()
        
        # 같은 영역의 다른 문제들
        related_questions = db.query(Question).filter(
            and_(
                Question.id != question_id,
                Question.area_name == question.area_name,
                Question.approval_status == "approved",
                Question.is_active == True
            )
        ).limit(3).all()
        
        return {
            "success": True,
            "current_question": {
                "id": question.id,
                "subject": question.subject,
                "area_name": question.area_name,
                "difficulty": question.difficulty
            },
            "similar_questions": [
                {
                    "id": q.id,
                    "content": q.content[:100] + "..." if len(q.content) > 100 else q.content,
                    "difficulty": q.difficulty,
                    "subject": q.subject
                } for q in similar_questions
            ],
            "related_questions": [
                {
                    "id": q.id,
                    "content": q.content[:100] + "..." if len(q.content) > 100 else q.content,
                    "area_name": q.area_name,
                    "difficulty": q.difficulty
                } for q in related_questions
            ],
            "study_recommendations": {
                "focus_areas": [question.subject, question.area_name],
                "practice_count": len(similar_questions) + len(related_questions),
                "estimated_time": "30-45분",
                "study_sequence": [
                    "현재 문제의 해설을 완전히 이해하기",
                    "유사한 문제들 풀어보기",
                    "관련 영역 문제들로 확장 학습",
                    "전체적인 개념 정리하기"
                ]
            }
        }
        
    except Exception as e:
        logger.error(f"학습 자료 조회 실패 (문제 {question_id}): {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="학습 자료를 불러올 수 없습니다."
        ) 