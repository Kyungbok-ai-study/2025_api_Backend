# 학과별 진단테스트 시스템

## 개요

학과별 진단테스트 시스템은 각 학과의 특성에 맞는 진단테스트를 JSON 파일 형태로 관리하고, 이를 통해 학생들의 학과별 수준을 진단하는 시스템입니다.

## 폴더 구조

```
data/departments/
├── computer_science/     # 컴퓨터공학 관련 (AI, 소프트웨어융합, 빅데이터 등 포함)
├── medical/             # 의학 관련
├── nursing/             # 간호학과
├── physical_therapy/    # 물리치료학과
├── business/            # 경영/상경 관련
├── engineering/         # 공학 관련
├── natural_science/     # 자연과학 관련
├── social_science/      # 사회과학 관련
├── law/                 # 법학과
├── education/           # 교육학과
└── arts/                # 예술 관련
```

## JSON 파일 구조

각 학과별 진단테스트 JSON 파일은 다음과 같은 구조를 가집니다:

```json
{
  "test_info": {
    "title": "학과명 수준 진단테스트",
    "description": "해당 학과의 전반적인 지식 진단",
    "total_questions": 30,
    "time_limit": 60,
    "created_at": "2025-06-15T13:30:00.000Z",
    "version": "1.0",
    "source": "관련 시험 기출문제 및 교재 기반"
  },
  "scoring_criteria": {
    "total_score": 100,
    "score_per_question": 3.3,
    "difficulty_weights": {
      "쉬움": 1.0,
      "보통": 1.2,
      "어려움": 1.5
    },
    "level_classification": {
      "상급": {
        "min_score": 80,
        "description": "상급 수준"
      },
      "중급": {
        "min_score": 65,
        "description": "중급 수준"
      },
      "하급": {
        "min_score": 50,
        "description": "하급 수준"
      },
      "미흡": {
        "min_score": 0,
        "description": "미흡 수준"
      }
    }
  },
  "questions": [
    {
      "question_id": "DEPT_001",
      "question_number": 1,
      "content": "문제 내용",
      "options": {
        "1": "선택지 1",
        "2": "선택지 2",
        "3": "선택지 3",
        "4": "선택지 4",
        "5": "선택지 5"
      },
      "correct_answer": "1",
      "subject": "학과명",
      "area_name": "영역명",
      "year": 2024,
      "original_question_number": 1,
      "difficulty": 5,
      "difficulty_level": "보통",
      "question_type": "기본개념",
      "domain": "도메인",
      "diagnostic_suitability": 8,
      "discrimination_power": 7,
      "points": 3.5,
      "source_info": {
        "file": "source_file.json",
        "unique_id": "DEPT_001"
      }
    }
  ],
  "statistics": {
    "difficulty_distribution": {
      "쉬움": 10,
      "보통": 15,
      "어려움": 5
    },
    "domain_distribution": {
      "domain1": 10,
      "domain2": 8,
      "domain3": 6
    },
    "type_distribution": {
      "기본개념": 20,
      "종합판단": 8,
      "응용문제": 2
    },
    "average_difficulty": 5.0,
    "average_discrimination": 7.5,
    "total_questions": 30
  }
}
```

## 학과별 매핑

### 컴퓨터공학 통합 (computer_science)
- 컴퓨터공학과
- 소프트웨어공학과
- 인공지능학과
- 데이터사이언스학과
- 정보시스템학과
- 빅데이터학과
- IT융합학과

### 의료 관련 (medical)
- 의학과
- 치의학과
- 약학과
- 작업치료학과

### 독립 학과
- 간호학과 (nursing)
- 물리치료학과 (physical_therapy)
- 경영학과 (business)
- 법학과 (law)
- 교육학과 (education)

## API 엔드포인트

### 관리자 API (`/admin/diagnosis-files`)

1. **파일 유효성 검사**
   ```
   GET /admin/diagnosis-files/validation-report
   ```

2. **사용 가능한 과목 목록**
   ```
   GET /admin/diagnosis-files/available-subjects
   ```

3. **특정 과목 정보 조회**
   ```
   GET /admin/diagnosis-files/test-info/{subject}
   ```

4. **문제 목록 조회**
   ```
   GET /admin/diagnosis-files/questions/{subject}?limit=10
   ```

5. **캐시 재로드**
   ```
   POST /admin/diagnosis-files/reload-cache
   ```

6. **특정 과목 데이터 재로드**
   ```
   POST /admin/diagnosis-files/reload-subject/{subject}
   ```

7. **JSON 파일을 데이터베이스로 동기화**
   ```
   POST /admin/diagnosis-files/sync-to-database/{subject}
   ```

8. **파일 구조 정보**
   ```
   GET /admin/diagnosis-files/file-structure
   ```

### 사용자 API (`/diagnosis/department-tests`)

1. **학과별 사용 가능한 테스트**
   ```
   GET /diagnosis/department-tests/my-tests
   ```

2. **추천 테스트**
   ```
   GET /diagnosis/department-tests/recommended
   ```

3. **진단 기록**
   ```
   GET /diagnosis/department-tests/my-history
   ```

4. **성과 분석**
   ```
   GET /diagnosis/department-tests/my-performance
   ```

## 사용 방법

### 1. 새로운 학과 추가

1. **enum 업데이트**: `app/models/enums.py`에서 `DiagnosisSubject` enum에 새 학과 추가
2. **파일 매핑 추가**: `DEPARTMENT_TEST_FILE_MAPPING`에 JSON 파일 경로 매핑
3. **카테고리 그룹핑**: `DEPARTMENT_CATEGORIES`에 적절한 카테고리에 추가
4. **JSON 파일 생성**: 해당 학과 폴더에 진단테스트 JSON 파일 생성

### 2. 문제 추가/수정

1. 해당 학과의 JSON 파일 편집
2. 관리자 API를 통해 캐시 재로드
3. 필요시 데이터베이스와 동기화

### 3. 데이터베이스 마이그레이션

```bash
# 마이그레이션 실행
alembic upgrade head

# 새로운 마이그레이션 생성 (필요시)
alembic revision --autogenerate -m "description"
```

## 특징

### 1. 유연한 학과 통합
- 유사한 학과들을 하나의 진단테스트로 통합 (예: 컴퓨터 관련 학과)
- 각 학과의 특성을 반영한 카테고리화

### 2. 파일 기반 관리
- JSON 형태로 문제 관리
- 버전 관리 용이
- 백업 및 복원 간편

### 3. 캐싱 시스템
- 성능 향상을 위한 파일 캐싱
- 필요시 실시간 재로드 가능

### 4. 동기화 기능
- JSON 파일과 데이터베이스 간 동기화
- 상태 추적 및 오류 관리

### 5. 유효성 검증
- 파일 구조 검증
- 누락된 파일 감지
- 오류 보고서 생성

## 확장 가능성

1. **새로운 학과 추가**: enum과 매핑만 추가하면 자동으로 시스템에 통합
2. **문제 형식 확장**: JSON 구조 확장을 통해 새로운 문제 유형 지원
3. **난이도 조절**: 동적 난이도 조절 알고리즘 적용 가능
4. **다국어 지원**: JSON 파일에 다국어 버전 추가 가능

## 주의사항

1. **파일 인코딩**: 모든 JSON 파일은 UTF-8로 저장
2. **JSON 형식**: 유효한 JSON 형식 준수 필수
3. **백업**: 정기적인 파일 백업 권장
4. **권한 관리**: 관리자만 파일 수정 가능
5. **캐시 무효화**: 파일 수정 후 반드시 캐시 재로드

## 문제 해결

### 파일 로드 실패
- 파일 경로 확인
- JSON 형식 유효성 검사
- 파일 권한 확인

### 동기화 실패
- 데이터베이스 연결 상태 확인
- 트랜잭션 롤백 로그 확인
- 데이터 무결성 검증

### 성능 이슈
- 캐시 활용 확인
- 파일 크기 최적화
- 불필요한 데이터 정리 