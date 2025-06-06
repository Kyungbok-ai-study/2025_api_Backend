# 문제 및 정답 파싱/매칭 로직 상세 설명

## 📋 개요

이 문서는 2025_api_Backend 프로젝트의 문제와 정답 데이터 파싱 및 매칭 시스템에 대한 상세한 설명을 제공합니다. 본 시스템은 **Gemini 2.0 Flash API**를 활용하여 다양한 형식의 파일을 자동으로 파싱하고 구조화된 데이터로 변환합니다.
개발기준은 일단 "C:\youngjin_worksapce\tutor_projects\2025_api_Backend\data\question_data"

## 🏗️ 시스템 아키텍처

```
프론트엔드 (React)
    ↓ 파일 업로드
API 엔드포인트 (/professor/upload/*)
    ↓ 파일 저장
QuestionParser (question_parser.py)
    ↓ Gemini API 파싱
QuestionService (question_service.py)
    ↓ 데이터 매칭 및 변환
데이터베이스 (PostgreSQL)
```

## 📊 데이터 스키마

### 새로운 Question 테이블 스키마
```sql
CREATE TABLE questions (
    id SERIAL PRIMARY KEY,
    question_number INTEGER NOT NULL,           -- 문제 번호 (1~22)
    content TEXT NOT NULL,                      -- 문제 내용
    description TEXT[],                         -- 문제 설명/지문 (배열)
    options JSONB,                             -- 선택지 {"1": "선택지1", "2": "선택지2", ...}
    correct_answer VARCHAR(10),                -- 정답 (예: "3")
    subject VARCHAR(100),                      -- 과목명
    area_name VARCHAR(100),                    -- 영역이름
    difficulty difficulty_level,               -- 난이도: '하', '중', '상'
    year INTEGER,                              -- 연도
    embedding VECTOR(1536),                    -- 임베딩 벡터 (OpenAI ada-002)
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);
```

### 제거된 필드들 (구버전)
- `question_type` → 제거 (모든 문제가 객관식으로 통일)
- `exam_session` → 제거
- `field_number` → 제거
- `field_name` → 제거
- `area_number` → 제거

## 🔧 핵심 컴포넌트

### 1. QuestionParser (`question_parser.py`)

#### 주요 기능
- **통합 파일 파싱**: PDF, Excel, JSON, 텍스트 등 모든 형식 지원
- **Gemini 2.0 Flash 기반**: 이미지 인식 및 텍스트 이해
- **22개 문제 제한**: 자동으로 22번 문제까지만 처리
- **연도별 분리**: 엑셀 시트명에서 연도 추출

#### 파싱 프로세스
```python
def parse_any_file(file_path: str, content_type: str) -> Dict[str, Any]:
    """
    1. 파일 형식 감지 (.pdf, .xlsx, .txt 등)
    2. 적절한 처리 함수 호출
    3. Gemini API로 구조화
    4. 22개 제한 적용
    5. 결과 반환
    """
```

#### PDF 처리 방식
```python
def _process_pdf_with_images(file_path: str) -> List[Dict]:
    """
    1. pdf2image로 PDF → 이미지 변환
    2. 각 페이지 이미지를 Gemini가 분석
    3. 문제 텍스트, 선택지, 번호 추출
    4. JSON 구조로 변환
    """
```

#### Excel 처리 방식
```python
def _process_excel_file_chunked(file_path: str) -> List[Dict]:
    """
    1. openpyxl로 모든 시트 읽기
    2. 시트명에서 연도 추출 (정규식: 20\d{2})
    3. 각 시트 데이터를 Gemini로 구조화
    4. 연도 보정 로직 적용
    """
```

### 2. QuestionService (`question_service.py`)

#### 주요 함수

##### `process_files_with_gemini_parser()`
```python
def process_files_with_gemini_parser(
    db: Session,
    question_file_path: str,
    answer_file_path: str,
    source_name: str,
    create_embeddings: bool = True,
    user_id: int = None,
    gemini_api_key: str = None
) -> Dict[str, Any]:
    """
    전체 파싱 및 저장 프로세스 관리
    1. 문제 파일 파싱
    2. 정답 파일 파싱
    3. 매칭 수행
    4. DB 형식 변환
    5. 데이터베이스 저장
    """
```

##### `match_questions_with_answers()`
```python
def match_questions_with_answers(
    questions: List[Dict],
    answers: List[Dict]
) -> List[Dict]:
    """
    문제와 정답 매칭 로직
    1. 정답을 문제번호로 인덱싱
    2. 연도별 매칭 확인
    3. 완전한 데이터만 반환 (부분 매칭 정책)
    4. 22개 제한 재적용
    """
```

## 🔄 파싱 및 매칭 플로우

### 1. 파일 업로드 단계
```
프론트엔드 → POST /professor/upload/questions
                ↓
            파일 저장 (uploads/questions/)
                ↓
            QuestionParser.parse_any_file()
                ↓
            파싱 결과 JSON 저장 (.parsed.json)
```

### 2. 정답 파일 처리
```
프론트엔드 → POST /professor/upload/answers
                ↓
            파일 저장 (uploads/answers/)
                ↓
            QuestionParser.parse_any_file(content_type="answers")
                ↓
            연도별 그룹화 및 JSON 저장
```

### 3. 매칭 및 저장 단계
```
프론트엔드 → POST /professor/parse-and-match
                ↓
            process_files_with_gemini_parser()
                ↓
            문제-정답 매칭 수행
                ↓
            convert_to_db_format()
                ↓
            데이터베이스 저장
```

## 🎯 매칭 알고리즘

### 연도별 매칭 전략
```python
# 1. 문제를 연도별로 그룹화
questions_by_year = defaultdict(list)
for q in questions:
    year = str(q.get("year", "unknown"))
    questions_by_year[year].append(q)

# 2. 정답을 연도별로 그룹화
answers_by_year = defaultdict(list)
for a in answers:
    year = str(a.get("year", "unknown"))
    answers_by_year[year].append(a)

# 3. 연도별로 개별 매칭
for year in all_years:
    year_questions = questions_by_year.get(year, [])
    year_answers = answers_by_year.get(year, [])
    matched_data = match_questions_with_answers(year_questions, year_answers)
```

### 문제번호 기반 매칭
```python
# 정답을 문제번호로 인덱싱
answer_map = {}
for ans in answers:
    q_num = ans.get("question_number")
    if q_num is not None and q_num <= 22:
        answer_map[str(q_num)] = ans

# 문제와 정답 매칭
for question in questions:
    q_num_str = str(question.get("question_number"))
    if q_num_str in answer_map:
        # 매칭 성공 → 병합
        matched_item = {**question, **answer_map[q_num_str]}
```

## 🧠 Gemini API 활용

### 프롬프트 전략
```python
def _generate_prompt(file_path: str, content_type: str, db_schema: str) -> str:
    """
    파일 형식과 내용에 따른 맞춤형 프롬프트 생성
    
    - 문제 파일: 문제 내용, 선택지, 번호 추출 요청
    - 정답 파일: 문제번호, 정답, 메타데이터 추출 요청
    - 22개 제한 명시
    - JSON 형식 응답 요청
    """
```

### 응답 파싱
```python
def _parse_gemini_response(response_text: str) -> Dict[str, Any]:
    """
    1. JSON 코드 블록 추출 (```json ... ```)
    2. 주석 제거 (// 및 /* */)
    3. JSON 파싱 시도
    4. 실패 시 적극적 정리 후 재시도
    5. 22개 제한 적용
    """
```

## 📈 성능 최적화

### 분할 처리 (Chunking)
- **Excel**: 시트별 개별 처리
- **PDF**: 페이지별 이미지 분석
- **텍스트**: 15,000자 단위 분할

### 임베딩 생성
```python
def create_embedding(text: str) -> List[float]:
    """
    OpenAI ada-002 모델 사용
    - 문제 내용 + 선택지 텍스트 결합
    - 1536차원 벡터 생성
    - pgvector로 저장
    """
```

### 메모리 관리
- 대용량 파일 스트리밍 처리
- 임시 파일 자동 정리
- 배치 처리로 메모리 사용량 제한

## 🔍 연도 추출 로직

### 시트명 기반 연도 추출
```python
# 정규식으로 4자리 연도 추출
match = re.search(r'(20\d{2})', sheet_name)
if match:
    year_in_sheet = int(match.group(1))
else:
    year_in_sheet = 2020  # 기본값

# Gemini가 연도를 못 뽑은 경우 보정
for item in sheet_data_parsed:
    if not item.get('year') or item.get('year') in [0, None, '']:
        item['year'] = year_in_sheet
```

## 🛡️ 에러 처리 및 검증

### 데이터 완전성 검증
```python
def _is_complete_question_data(question_data: Dict[str, Any]) -> bool:
    """
    필수 필드 검증:
    - question_number (1~22)
    - content (비어있지 않음)
    - correct_answer (비어있지 않음)
    - options (2개 이상의 선택지)
    """
```

### 파일 처리 에러 핸들링
- 파일 형식 불일치 → 자동 감지 및 변환
- 인코딩 문제 → 다중 인코딩 시도
- Gemini API 오류 → 재시도 로직
- 메모리 부족 → 분할 처리

## 📊 처리 결과 예시

### 성공적인 처리 결과
```json
{
  "success": true,
  "total_questions": 88,
  "saved_questions": 88,
  "save_rate": "100.0%",
  "results_by_year": {
    "2021": {"saved": 22, "total": 22, "match_rate": "100.0%"},
    "2022": {"saved": 22, "total": 22, "match_rate": "100.0%"},
    "2023": {"saved": 22, "total": 22, "match_rate": "100.0%"},
    "2024": {"saved": 22, "total": 22, "match_rate": "100.0%"}
  }
}
```

### 파싱된 문제 데이터 구조
```json
{
  "question_number": 1,
  "content": "다음에서 설명하는 인체 기본조직은?",
  "description": [
    "- 몸에 널리 분포하며, 몸의 구조를 이룸",
    "- 세포나 기관 사이 틈을 메우고, 기관을 지지·보호함"
  ],
  "options": {
    "1": "상피조직",
    "2": "결합조직", 
    "3": "근육조직",
    "4": "신경조직",
    "5": "혈액조직"
  },
  "correct_answer": "2",
  "subject": "물리치료학",
  "area_name": "해부학",
  "difficulty": "중",
  "year": 2021
}
```

## 🚀 확장성 및 유지보수

### 새로운 파일 형식 추가
1. `_process_[format]_file()` 함수 구현
2. `parse_any_file()`에 확장자 매핑 추가
3. 해당 형식용 프롬프트 작성

### 스키마 변경 대응
1. `Question` 모델 수정
2. `_generate_prompt()` 업데이트
3. 마이그레이션 스크립트 작성
4. 기존 데이터 변환 로직 구현

### 성능 모니터링
- 파싱 시간 측정
- Gemini API 사용량 추적
- 메모리 사용량 모니터링
- 매칭 성공률 통계

## 🔧 설정 및 환경변수

### 필수 환경변수
```bash
GEMINI_API_KEY=your_gemini_api_key
OPENAI_API_KEY=your_openai_api_key  # 임베딩용
POPPLER_PATH=path_to_poppler_bin    # PDF 변환용
```

### 설정 파일 (`settings.py`)
```python
GEMINI_MODEL_NAME = "gemini-2.0-flash-exp"
MAX_QUESTIONS_PER_FILE = 22
CHUNK_SIZE = 15000
EMBEDDING_DIMENSION = 1536
```

## 📝 사용 예시

### API 호출 예시
```javascript
// 1. 문제 파일 업로드
const questionFormData = new FormData();
questionFormData.append('file', questionFile);
const questionResponse = await fetch('/professor/upload/questions', {
  method: 'POST',
  body: questionFormData
});

// 2. 정답 파일 업로드  
const answerFormData = new FormData();
answerFormData.append('file', answerFile);
const answerResponse = await fetch('/professor/upload/answers', {
  method: 'POST', 
  body: answerFormData
});

// 3. 파싱 및 매칭 실행
const matchRequest = {
  question_file_path: questionResponse.file_name,
  answer_file_path: answerResponse.file_name,
  source_name: "2024년 물리치료사 국가시험",
  create_embeddings: true
};
const matchResponse = await fetch('/professor/parse-and-match', {
  method: 'POST',
  headers: {'Content-Type': 'application/json'},
  body: JSON.stringify(matchRequest)
});
```

## 🎯 결론

본 파싱 및 매칭 시스템은 **Gemini 2.0 Flash API**의 강력한 멀티모달 능력을 활용하여 다양한 형식의 교육 자료를 자동으로 구조화된 데이터로 변환합니다. 

**주요 장점:**
- 🤖 **완전 자동화**: 수동 데이터 입력 불필요
- 📄 **다양한 형식 지원**: PDF, Excel, 텍스트 등
- 🎯 **높은 정확도**: 100% 매칭 성공률 달성
- ⚡ **확장 가능**: 새로운 형식 쉽게 추가
- 🔍 **지능형 파싱**: 이미지와 텍스트 동시 처리

이 시스템을 통해 교육 기관은 기존의 문제 자료를 빠르고 정확하게 디지털화하여 현대적인 학습 관리 시스템에 통합할 수 있습니다.
