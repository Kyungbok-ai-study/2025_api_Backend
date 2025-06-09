# 프론트엔드 API 가이드 - DeepSeek + Qdrant 통합 시스템

## 🏗️ 시스템 아키텍처

```
프론트엔드 (React/Vue) 
    ↓ HTTP/REST API
FastAPI 백엔드 (Python)
    ├── PostgreSQL (일반형 데이터)
    ├── Qdrant (벡터 DB) 
    ├── DeepSeek (로컬 AI)
    └── Gemini API (PDF 파서)
```

## 📡 주요 API 엔드포인트

### 🎯 **DeepSeek + Gemini 워크플로우 API**

#### 1. 문서 업로드 및 처리
```http
POST /api/rag/deepseek-upload
Content-Type: multipart/form-data

Parameters:
- file: PDF 파일
- request_data: JSON 문자열
  {
    "document_title": "문서 제목",
    "department": "간호학과|물리치료학과|작업치료학과",
    "subject": "과목명 (옵션)",
    "auto_classify": true,
    "chunk_size": 1000,
    "overlap": 200,
    "use_deepseek_labeling": true
  }

Response:
{
  "success": true,
  "message": "처리 시작됨",
  "processing_id": "uuid",
  "document_info": {...},
  "processing_steps": {...},
  "statistics": {...}
}
```

#### 2. 처리 상태 확인
```http
GET /api/rag/deepseek-status/{processing_id}

Response:
{
  "processing_id": "uuid",
  "status": "processing|completed|failed",
  "progress_percentage": 75,
  "current_step": "DeepSeek 분류 중...",
  "steps_completed": ["Gemini PDF 파싱", "텍스트 청킹"],
  "results": {...},
  "error_message": null
}
```

#### 3. 지식베이스 통계
```http
GET /api/rag/deepseek-knowledge-base-stats

Response:
{
  "total_documents": 15,
  "total_chunks": 1500,
  "total_vectors": 1500,
  "departments": {"간호학과": 8, "물리치료학과": 4, "작업치료학과": 3},
  "subjects": {"기본간호학": 5, "성인간호학": 3},
  "difficulty_distribution": {"쉬움": 500, "보통": 800, "어려움": 200},
  "last_updated": "2025-01-27T...",
  "embedding_model": "DeepSeek Embedding",
  "vector_dimension": 768
}
```

#### 4. 지식베이스 재인덱싱
```http
POST /api/rag/deepseek-reindex

Response:
{
  "success": true,
  "message": "재인덱싱 완료",
  "processed_documents": 15,
  "vector_count": 1500,
  "reindex_time": "2025-01-27T..."
}
```

### 📋 **교수 승인 워크플로우**

#### 5. 승인 대기 문제 목록
```http
GET /api/professor/pending-questions?page=1&size=20

Response:
{
  "questions": [
    {
      "id": 123,
      "content": "문제 내용",
      "difficulty": "보통",
      "department": "간호학과",
      "parsed_data_path": "data/save_parser/file.json",
      "created_at": "2025-01-27T...",
      "approval_status": "pending"
    }
  ],
  "total": 45,
  "page": 1,
  "size": 20
}
```

#### 6. 문제 승인/거부
```http
POST /api/professor/approve-question/{question_id}
{
  "action": "approve|reject",
  "feedback": "수정 요청 사항 (옵션)",
  "auto_vectorize": true
}

Response:
{
  "success": true,
  "message": "승인 완료",
  "question_id": 123,
  "vectorized": true,
  "qdrant_stored": true
}
```

### 🔍 **RAG 검색 및 질의응답**

#### 7. 유사도 검색
```http
POST /api/rag/similarity-search
{
  "query_text": "간호 과정에 대해 설명하세요",
  "limit": 5,
  "similarity_threshold": 0.7
}

Response:
{
  "success": true,
  "results": [
    {
      "content": "검색된 텍스트",
      "score": 0.85,
      "metadata": {
        "document_title": "기본간호학",
        "department": "간호학과",
        "difficulty": "보통"
      }
    }
  ],
  "total_count": 5
}
```

#### 8. RAG 기반 문제 생성
```http
POST /api/rag/generate-question
{
  "topic": "간호 과정",
  "difficulty": "중",
  "question_type": "multiple_choice",
  "context_limit": 3
}

Response:
{
  "success": true,
  "question": {
    "content": "생성된 문제",
    "options": {"A": "선택지1", "B": "선택지2"},
    "correct_answer": "A",
    "explanation": "해설"
  },
  "contexts_used": [...],
  "sources": ["문서1", "문서2"]
}
```

### 🤖 **DeepSeek AI 서비스**

#### 9. AI 해설 생성
```http
POST /api/ai/generate-explanation
{
  "question": "문제 내용",
  "correct_answer": "정답",
  "options": {"A": "선택지1", "B": "선택지2"},
  "department": "간호학과"
}

Response:
{
  "success": true,
  "explanation": "AI 생성 해설",
  "confidence": 0.9,
  "reasoning": "해설 근거"
}
```

#### 10. 개인맞춤 문제 추천
```http
POST /api/ai/personalized-recommendations
{
  "user_id": 123,
  "department": "간호학과",
  "difficulty_preference": "adaptive",
  "topic_focus": ["기본간호학", "성인간호학"],
  "limit": 10
}

Response:
{
  "success": true,
  "recommendations": [
    {
      "question_id": 456,
      "relevance_score": 0.92,
      "difficulty": "보통",
      "topic": "기본간호학",
      "reasoning": "사용자 성과 분석 결과"
    }
  ]
}
```

## 🔄 워크플로우 단계

### **Phase 1: 문서 업로드** 
```javascript
// 프론트엔드 코드 예시
const uploadDocument = async (file, metadata) => {
  const formData = new FormData();
  formData.append('file', file);
  formData.append('request_data', JSON.stringify(metadata));
  
  const response = await fetch('/api/rag/deepseek-upload', {
    method: 'POST',
    body: formData,
    headers: {
      'Authorization': `Bearer ${token}`
    }
  });
  
  return response.json();
};
```

### **Phase 2: 상태 모니터링**
```javascript
const monitorProcessing = async (processingId) => {
  const pollStatus = async () => {
    const response = await fetch(`/api/rag/deepseek-status/${processingId}`);
    const status = await response.json();
    
    if (status.status === 'completed') {
      return status.results;
    } else if (status.status === 'failed') {
      throw new Error(status.error_message);
    } else {
      // 진행률 업데이트
      updateProgress(status.progress_percentage);
      setTimeout(pollStatus, 2000); // 2초마다 확인
    }
  };
  
  return pollStatus();
};
```

### **Phase 3: 교수 승인**
```javascript
const approveQuestion = async (questionId, action) => {
  const response = await fetch(`/api/professor/approve-question/${questionId}`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${token}`
    },
    body: JSON.stringify({
      action: action, // 'approve' or 'reject'
      auto_vectorize: true
    })
  });
  
  return response.json();
};
```

### **Phase 4: RAG 검색**
```javascript
const searchKnowledgeBase = async (query) => {
  const response = await fetch('/api/rag/similarity-search', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${token}`
    },
    body: JSON.stringify({
      query_text: query,
      limit: 10,
      similarity_threshold: 0.7
    })
  });
  
  return response.json();
};
```

## 🏗️ 데이터 저장 구조

### **PostgreSQL (일반형 데이터)**
```sql
-- questions 테이블
- id: 문제 ID
- content: 문제 내용
- difficulty: 난이도
- department: 학과
- approval_status: 승인 상태
- parsed_data_path: JSON 파일 경로
- vector_db_indexed: Qdrant 저장 여부
- rag_indexed: RAG 인덱싱 여부
```

### **Qdrant (벡터 데이터)**
```python
# 벡터 메타데이터 구조
{
  "document_title": "문서 제목",
  "department": "간호학과", 
  "subject": "기본간호학",
  "difficulty": "보통",
  "content_type": "이론|실무|사례|문제",
  "keywords": ["키워드1", "키워드2"],
  "chunk_index": 0,
  "file_category": "RAG_DEEPSEEK",
  "user_id": 123,
  "created_at": "2025-01-27T..."
}
```

### **JSON 파서 결과 저장** (`data/save_parser/`)
```json
{
  "document_info": {
    "title": "문서 제목",
    "department": "간호학과",
    "processing_id": "uuid"
  },
  "chunks": [
    {
      "content": "텍스트 청크",
      "difficulty": "보통",
      "content_type": "이론",
      "keywords": ["키워드"],
      "chunk_index": 0
    }
  ],
  "statistics": {
    "total_chunks": 50,
    "successful_vectors": 50,
    "failed_vectors": 0
  }
}
```

## 🎯 프론트엔드 연동 포인트

### **1. 파일 업로드 UI**
- 드래그 앤 드롭 업로드
- 진행률 표시
- 실시간 상태 업데이트

### **2. 교수 승인 대시보드**
- 승인 대기 목록
- 문제 미리보기
- 일괄 승인/거부

### **3. RAG 검색 인터페이스**
- 실시간 검색
- 유사도 점수 표시
- 소스 문서 링크

### **4. 지식베이스 관리**
- 통계 대시보드
- 재인덱싱 버튼
- 성능 모니터링

## 🔧 개발 환경 설정

### **필수 환경 변수**
```env
# 백엔드 연결
REACT_APP_API_URL=http://localhost:8000

# 기능 플래그
REACT_APP_USE_DEEPSEEK=true
REACT_APP_USE_RAG=true
REACT_APP_ENABLE_FILE_UPLOAD=true
```

### **API 클라이언트 설정**
```javascript
// api/client.js
const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000';

export const apiClient = {
  baseURL: API_BASE_URL,
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json'
  }
};
```

## ✅ 연결 확인 체크리스트

- [ ] FastAPI 서버 실행: `http://localhost:8000`
- [ ] Swagger UI 접근: `http://localhost:8000/docs`
- [ ] Qdrant 서버 실행: `http://localhost:6333`
- [ ] PostgreSQL 연결 확인
- [ ] Ollama DeepSeek 모델 로드
- [ ] Gemini API 키 설정
- [ ] 프론트엔드 CORS 설정

## 🚀 통합 테스트

전체 워크플로우를 테스트하려면:
1. PDF 파일 업로드
2. 처리 상태 모니터링
3. 교수 승인 처리
4. RAG 검색 테스트
5. AI 문제 생성 테스트

이제 프론트엔드와 완전히 연결된 **PostgreSQL + Qdrant + DeepSeek + Gemini** 통합 시스템이 준비되었습니다! 🎉 