"""
모델 패키지 초기화
"""

# 실제로 존재하는 모델들만 import
from .user import User
from .verification import VerificationRequest
from .assignment import Assignment, AssignmentSubmission, ProblemBank
from .analytics import StudentActivity, StudentWarning, LearningAnalytics, ClassStatistics, ProfessorDashboardData
from .question import Question, AnswerOption, CorrectAnswer, Explanation, TestSet, TestQuestion, TestAttempt, UserAnswer
from .diagnosis import TestSession, TestResponse, DiagnosisResult, LearningLevelHistory, MultiChoiceTestSession, MultiChoiceTestResponse
from .deepseek import DeepSeekLearningSession

__all__ = [
    "User",
    "VerificationRequest",
    "Assignment",
    "AssignmentSubmission",
    "ProblemBank",
    "StudentActivity",
    "StudentWarning",
    "LearningAnalytics",
    "ClassStatistics",
    "ProfessorDashboardData",
    "Question",
    "AnswerOption",
    "CorrectAnswer", 
    "Explanation",
    "TestSet",
    "TestQuestion",
    "TestAttempt",
    "UserAnswer",
    "TestSession",
    "TestResponse",
    "DiagnosisResult",
    "LearningLevelHistory",
    "MultiChoiceTestSession",
    "MultiChoiceTestResponse",
    "DeepSeekLearningSession"
] 