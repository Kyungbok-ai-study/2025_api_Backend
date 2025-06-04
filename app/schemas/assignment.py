from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime
from enum import Enum

class AssignmentType(str, Enum):
    HOMEWORK = "homework"
    PROJECT = "project"
    QUIZ = "quiz"
    EXAM = "exam"

class AssignmentStatus(str, Enum):
    DRAFT = "draft"
    PUBLISHED = "published"
    CLOSED = "closed"
    GRADED = "graded"

class AssignmentCreate(BaseModel):
    title: str
    description: Optional[str] = None
    assignment_type: AssignmentType
    subject_name: str
    due_date: Optional[datetime] = None
    max_score: Optional[int] = 100
    allow_late_submission: Optional[bool] = False
    instructions: Optional[str] = None

class AssignmentResponse(BaseModel):
    id: int
    title: str
    description: Optional[str]
    assignment_type: AssignmentType
    status: AssignmentStatus
    subject_name: str
    due_date: Optional[datetime]
    max_score: int
    allow_late_submission: bool
    instructions: Optional[str]
    created_at: datetime
    published_at: Optional[datetime]

    class Config:
        from_attributes = True

class SubmissionResponse(BaseModel):
    id: int
    student_name: str
    student_id: str
    submitted_at: datetime
    score: Optional[float]
    is_late: bool
    graded_at: Optional[datetime]

class AssignmentDetailResponse(BaseModel):
    assignment: AssignmentResponse
    submissions: List[SubmissionResponse]
    statistics: dict

class AssignmentStatusUpdate(BaseModel):
    status: AssignmentStatus 