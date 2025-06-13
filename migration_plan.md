# 🔄 시스템 마이그레이션 계획

## 📋 마이그레이션 개요
- **목표**: API 기반 → 로컬 기반 AI 시스템
- **일정**: 2-3주 예상
- **위험도**: 중간 (단계별 진행으로 리스크 최소화)

## 🎯 변경사항 요약

### 1. LLM 모델 변경
```
현재: OpenAI GPT-3.5/4 + Google Gemini
변경: 로컬 LLM (Ollama + Llama 3.1/3.2)
```

### 2. 벡터 DB 변경  
```
현재: PostgreSQL + Qdrant (pgvector에서 마이그레이션 완료)
변경: Qdrant (고성능 벡터 검색)
```

### 3. 일반 DB 유지
```
유지: PostgreSQL (사용자, 문제, 진단 데이터)
```

## 🔧 1단계: 로컬 LLM 설정

### 추천 로컬 LLM 모델
1. **Llama 3.1 8B** (추천)
   - 크기: ~4.7GB
   - 성능: GPT-3.5 수준
   - 메모리: 8GB RAM 필요

2. **Llama 3.2 3B**
   - 크기: ~2GB  
   - 성능: 경량화 버전
   - 메모리: 4GB RAM 필요

3. **Qwen 2.5 7B**
   - 크기: ~4.1GB
   - 특징: 한국어 성능 우수

### Ollama 설치 및 설정
```bash
# 1. Ollama 설치
curl -fsSL https://ollama.ai/install.sh | sh

# 2. 모델 다운로드
ollama pull llama3.1:8b
ollama pull llama3.2:3b

# 3. 서비스 시작
ollama serve
```

### Python 연동 코드
```python
# requirements.txt 추가
ollama-python==0.1.9

# 로컬 LLM 서비스 클래스
class LocalLLMService:
    def __init__(self):
        self.client = ollama.Client()
        self.model = "llama3.1:8b"
    
    def generate_response(self, prompt: str) -> str:
        response = self.client.chat(
            model=self.model,
            messages=[{"role": "user", "content": prompt}]
        )
        return response['message']['content']
```

## 🗄️ 2단계: Qdrant 벡터 DB 설정

### Qdrant 설치
```bash
# Docker로 설치 (추천)
docker run -p 6333:6333 qdrant/qdrant

# 또는 직접 설치
pip install qdrant-client
```

### Qdrant 연동 코드
```python
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams

class QdrantVectorService:
    def __init__(self):
        self.client = QdrantClient("localhost", port=6333)
        self.collection_name = "questions"
    
    def create_collection(self):
        self.client.create_collection(
            collection_name=self.collection_name,
            vectors_config=VectorParams(
                size=384,  # sentence-transformers 차원
                distance=Distance.COSINE
            )
        )
    
    def add_vector(self, question_id: int, vector: list, metadata: dict):
        self.client.upsert(
            collection_name=self.collection_name,
            points=[{
                "id": question_id,
                "vector": vector,
                "payload": metadata
            }]
        )
```

## 🔄 3단계: 마이그레이션 실행 순서

### Week 1: 로컬 LLM 구축
- [ ] Ollama 설치 및 모델 다운로드
- [ ] 로컬 LLM 서비스 클래스 구현
- [ ] 기존 OpenAI/Gemini 코드와 병렬 테스트
- [ ] 성능 비교 및 튜닝

### Week 2: Qdrant 벡터 DB 마이그레이션  
- [ ] Qdrant 설치 및 설정
- [x] pgvector 데이터 Qdrant로 마이그레이션 (완료)
- [ ] 벡터 검색 성능 테스트
- [ ] RAG 시스템 Qdrant 연동

### Week 3: 통합 및 최적화
- [ ] 전체 시스템 통합 테스트
- [ ] 성능 최적화 및 튜닝
- [ ] 기존 API 코드 제거
- [ ] 문서화 및 배포

## 📊 예상 성능 개선

### 비용 절감
- **현재**: API 요청당 과금 (~월 50-200만원)
- **변경 후**: 전력비만 (~월 5-10만원)
- **절감액**: 월 40-190만원

### 성능 개선
- **응답 속도**: 2-3초 → 0.5-1초
- **가용성**: API 의존성 제거
- **프라이버시**: 완전 로컬 처리

### 확장성  
- **동시 처리**: API 제한 없음
- **커스터마이징**: 모델 파인튜닝 가능
- **데이터 보안**: 외부 전송 없음

## ⚠️ 주의사항

### 하드웨어 요구사항
- **최소**: 16GB RAM, RTX 3060 이상
- **권장**: 32GB RAM, RTX 4070 이상  
- **최적**: 64GB RAM, RTX 4090

### 백업 계획
- 마이그레이션 중 기존 API 시스템 병렬 유지
- 단계별 롤백 포인트 설정
- 성능 문제 시 즉시 복구 가능

## 🎯 다음 단계
1. 하드웨어 사양 확인
2. Ollama + Llama 3.1 테스트 환경 구축
3. 성능 벤치마크 실시
4. 단계별 마이그레이션 실행 