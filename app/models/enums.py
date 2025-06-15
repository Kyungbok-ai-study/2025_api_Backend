"""
공통 Enum 정의
중복 제거를 위해 모든 모델에서 사용하는 Enum들을 통합
"""
import enum

# ==================== 문제 관련 Enum ====================

class QuestionType(str, enum.Enum):
    """문제 유형 - 모든 모델에서 공통 사용"""
    MULTIPLE_CHOICE = "multiple_choice"  # 객관식
    SHORT_ANSWER = "short_answer"        # 주관식
    TRUE_FALSE = "true_false"            # O/X
    MATCHING = "matching"                # 짝 맞추기
    ORDERING = "ordering"                # 순서 맞추기
    FILL_IN_BLANK = "fill_in_blank"      # 빈칸 채우기
    ESSAY = "essay"                      # 서술형
    MULTI_CHOICE_SELECTION = "multi_choice_selection"  # 1문제 30선택지
    OTHER = "other"                      # 기타

class DifficultyLevel(str, enum.Enum):
    """문제 난이도"""
    LOW = "하"
    MEDIUM = "중"
    HIGH = "상"

class QuestionStatus(str, enum.Enum):
    """문제 상태"""
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    ARCHIVED = "archived"

# ==================== 진단 관련 Enum ====================

class DiagnosisStatus(str, enum.Enum):
    """진단 테스트 상태"""
    ACTIVE = "active"
    COMPLETED = "completed"
    EXPIRED = "expired"
    CANCELLED = "cancelled"

class DiagnosisSubject(str, enum.Enum):
    """진단 과목 - 전체 학과 지원"""
    # 컴퓨터공학 관련 (AI, 소프트웨어융합, 빅데이터 등 포함)
    COMPUTER_SCIENCE = "컴퓨터공학"
    SOFTWARE_ENGINEERING = "소프트웨어공학"
    ARTIFICIAL_INTELLIGENCE = "인공지능"
    DATA_SCIENCE = "데이터사이언스"
    INFORMATION_SYSTEMS = "정보시스템"
    
    # 의학 관련
    MEDICINE = "의학"
    NURSING = "간호학"
    PHYSICAL_THERAPY = "물리치료학"
    OCCUPATIONAL_THERAPY = "작업치료학"
    DENTISTRY = "치의학"
    PHARMACY = "약학"
    
    # 공학 관련
    MECHANICAL_ENGINEERING = "기계공학"
    ELECTRICAL_ENGINEERING = "전기공학"
    ELECTRONIC_ENGINEERING = "전자공학"
    CHEMICAL_ENGINEERING = "화학공학"
    CIVIL_ENGINEERING = "토목공학"
    ARCHITECTURE = "건축학"
    
    # 자연과학
    MATHEMATICS = "수학"
    PHYSICS = "물리학"
    CHEMISTRY = "화학"
    BIOLOGY = "생물학"
    STATISTICS = "통계학"
    
    # 사회과학
    ECONOMICS = "경제학"
    PSYCHOLOGY = "심리학"
    SOCIOLOGY = "사회학"
    POLITICAL_SCIENCE = "정치학"
    
    # 경영/상경
    BUSINESS_ADMINISTRATION = "경영학"
    ACCOUNTING = "회계학"
    FINANCE = "금융학"
    MARKETING = "마케팅"
    
    # 법학
    LAW = "법학"
    
    # 교육
    EDUCATION = "교육학"
    ELEMENTARY_EDUCATION = "초등교육"
    
    # 예술
    FINE_ARTS = "미술학"
    MUSIC = "음악학"
    DESIGN = "디자인"

# 학과별 진단테스트 파일 매핑
DEPARTMENT_TEST_FILE_MAPPING = {
    # 컴퓨터공학 관련 (통합)
    DiagnosisSubject.COMPUTER_SCIENCE: "departments/computer_science/diagnostic_test_computer_science.json",
    DiagnosisSubject.SOFTWARE_ENGINEERING: "departments/computer_science/diagnostic_test_computer_science.json",
    DiagnosisSubject.ARTIFICIAL_INTELLIGENCE: "departments/computer_science/diagnostic_test_computer_science.json",
    DiagnosisSubject.DATA_SCIENCE: "departments/computer_science/diagnostic_test_computer_science.json",
    DiagnosisSubject.INFORMATION_SYSTEMS: "departments/computer_science/diagnostic_test_computer_science.json",
    
    # 의학 관련
    DiagnosisSubject.MEDICINE: "departments/medical/diagnostic_test_medical.json",
    DiagnosisSubject.NURSING: "departments/nursing/diagnostic_test_nursing.json",
    DiagnosisSubject.PHYSICAL_THERAPY: "departments/physical_therapy/diagnostic_test_physics_therapy.json",
    DiagnosisSubject.OCCUPATIONAL_THERAPY: "departments/medical/diagnostic_test_occupational_therapy.json",
    DiagnosisSubject.DENTISTRY: "departments/medical/diagnostic_test_dentistry.json",
    DiagnosisSubject.PHARMACY: "departments/medical/diagnostic_test_pharmacy.json",
    
    # 공학 관련
    DiagnosisSubject.MECHANICAL_ENGINEERING: "departments/engineering/diagnostic_test_mechanical.json",
    DiagnosisSubject.ELECTRICAL_ENGINEERING: "departments/engineering/diagnostic_test_electrical.json",
    DiagnosisSubject.ELECTRONIC_ENGINEERING: "departments/engineering/diagnostic_test_electronic.json",
    DiagnosisSubject.CHEMICAL_ENGINEERING: "departments/engineering/diagnostic_test_chemical.json",
    DiagnosisSubject.CIVIL_ENGINEERING: "departments/engineering/diagnostic_test_civil.json",
    DiagnosisSubject.ARCHITECTURE: "departments/engineering/diagnostic_test_architecture.json",
    
    # 자연과학
    DiagnosisSubject.MATHEMATICS: "departments/natural_science/diagnostic_test_mathematics.json",
    DiagnosisSubject.PHYSICS: "departments/natural_science/diagnostic_test_physics.json",
    DiagnosisSubject.CHEMISTRY: "departments/natural_science/diagnostic_test_chemistry.json",
    DiagnosisSubject.BIOLOGY: "departments/natural_science/diagnostic_test_biology.json",
    DiagnosisSubject.STATISTICS: "departments/natural_science/diagnostic_test_statistics.json",
    
    # 사회과학
    DiagnosisSubject.ECONOMICS: "departments/social_science/diagnostic_test_economics.json",
    DiagnosisSubject.PSYCHOLOGY: "departments/social_science/diagnostic_test_psychology.json",
    DiagnosisSubject.SOCIOLOGY: "departments/social_science/diagnostic_test_sociology.json",
    DiagnosisSubject.POLITICAL_SCIENCE: "departments/social_science/diagnostic_test_political_science.json",
    
    # 경영/상경
    DiagnosisSubject.BUSINESS_ADMINISTRATION: "departments/business/diagnostic_test_business.json",
    DiagnosisSubject.ACCOUNTING: "departments/business/diagnostic_test_accounting.json",
    DiagnosisSubject.FINANCE: "departments/business/diagnostic_test_finance.json",
    DiagnosisSubject.MARKETING: "departments/business/diagnostic_test_marketing.json",
    
    # 법학
    DiagnosisSubject.LAW: "departments/law/diagnostic_test_law.json",
    
    # 교육
    DiagnosisSubject.EDUCATION: "departments/education/diagnostic_test_education.json",
    DiagnosisSubject.ELEMENTARY_EDUCATION: "departments/education/diagnostic_test_elementary_education.json",
    
    # 예술
    DiagnosisSubject.FINE_ARTS: "departments/arts/diagnostic_test_fine_arts.json",
    DiagnosisSubject.MUSIC: "departments/arts/diagnostic_test_music.json",
    DiagnosisSubject.DESIGN: "departments/arts/diagnostic_test_design.json",
}

# 학과 카테고리별 그룹핑
DEPARTMENT_CATEGORIES = {
    "computer_science": [
        DiagnosisSubject.COMPUTER_SCIENCE,
        DiagnosisSubject.SOFTWARE_ENGINEERING,
        DiagnosisSubject.ARTIFICIAL_INTELLIGENCE,
        DiagnosisSubject.DATA_SCIENCE,
        DiagnosisSubject.INFORMATION_SYSTEMS,
    ],
    "medical": [
        DiagnosisSubject.MEDICINE,
        DiagnosisSubject.NURSING,
        DiagnosisSubject.PHYSICAL_THERAPY,
        DiagnosisSubject.OCCUPATIONAL_THERAPY,
        DiagnosisSubject.DENTISTRY,
        DiagnosisSubject.PHARMACY,
    ],
    "engineering": [
        DiagnosisSubject.MECHANICAL_ENGINEERING,
        DiagnosisSubject.ELECTRICAL_ENGINEERING,
        DiagnosisSubject.ELECTRONIC_ENGINEERING,
        DiagnosisSubject.CHEMICAL_ENGINEERING,
        DiagnosisSubject.CIVIL_ENGINEERING,
        DiagnosisSubject.ARCHITECTURE,
    ],
    "natural_science": [
        DiagnosisSubject.MATHEMATICS,
        DiagnosisSubject.PHYSICS,
        DiagnosisSubject.CHEMISTRY,
        DiagnosisSubject.BIOLOGY,
        DiagnosisSubject.STATISTICS,
    ],
    "social_science": [
        DiagnosisSubject.ECONOMICS,
        DiagnosisSubject.PSYCHOLOGY,
        DiagnosisSubject.SOCIOLOGY,
        DiagnosisSubject.POLITICAL_SCIENCE,
    ],
    "business": [
        DiagnosisSubject.BUSINESS_ADMINISTRATION,
        DiagnosisSubject.ACCOUNTING,
        DiagnosisSubject.FINANCE,
        DiagnosisSubject.MARKETING,
    ],
    "law": [DiagnosisSubject.LAW],
    "education": [
        DiagnosisSubject.EDUCATION,
        DiagnosisSubject.ELEMENTARY_EDUCATION,
    ],
    "arts": [
        DiagnosisSubject.FINE_ARTS,
        DiagnosisSubject.MUSIC,
        DiagnosisSubject.DESIGN,
    ],
}

class Department(str, enum.Enum):
    """학과 분류"""
    # 컴퓨터 관련
    COMPUTER_ENGINEERING = "컴퓨터공학과"
    SOFTWARE_CONVERGENCE = "소프트웨어융합과"
    
    # 의료 관련 
    PHYSICAL_THERAPY = "물리치료학과"
    NURSING = "간호학과"
    OCCUPATIONAL_THERAPY = "작업치료학과"
    RADIOLOGIC_TECHNOLOGY = "방사선학과"
    MEDICAL_LABORATORY = "임상병리학과"
    
    # 기타
    BUSINESS_ADMINISTRATION = "경영학과"
    ECONOMICS = "경제학과"
    ENGLISH = "영어학과"
    KOREAN = "국어국문학과"
    MATHEMATICS = "수학과"
    STATISTICS = "통계학과"

# ==================== 과제 관련 Enum ====================

class AssignmentStatus(str, enum.Enum):
    """과제 상태"""
    DRAFT = "draft"          # 초안
    PUBLISHED = "published"  # 게시됨
    CLOSED = "closed"        # 마감됨
    GRADED = "graded"        # 채점완료

class AssignmentType(str, enum.Enum):
    """과제 유형"""
    QUIZ = "quiz"           # 퀴즈
    HOMEWORK = "homework"   # 숙제
    PROJECT = "project"     # 프로젝트
    EXAM = "exam"          # 시험
    ESSAY = "essay"        # 레포트

# ==================== 인증 관련 Enum ====================

class VerificationType(str, enum.Enum):
    """인증 요청 유형"""
    STUDENT = "student"
    PROFESSOR = "professor"

class VerificationStatus(str, enum.Enum):
    """인증 상태"""
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    EXPIRED = "expired"

# ==================== 사용자 역할 ====================

class UserRole(str, enum.Enum):
    """사용자 역할"""
    STUDENT = "student"
    PROFESSOR = "professor"
    ADMIN = "admin"

# ==================== 테스트 관련 Enum ====================

class TestStatus(str, enum.Enum):
    """테스트 상태"""
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    ABANDONED = "abandoned"
    EXPIRED = "expired"

class SubmissionStatus(str, enum.Enum):
    """제출 상태"""
    NOT_SUBMITTED = "not_submitted"
    SUBMITTED = "submitted"
    LATE_SUBMITTED = "late_submitted"
    GRADED = "graded"

# ==================== 시스템 상태 ====================

class SystemStatus(str, enum.Enum):
    """시스템 상태"""
    ACTIVE = "active"
    INACTIVE = "inactive"
    MAINTENANCE = "maintenance"
    ERROR = "error" 