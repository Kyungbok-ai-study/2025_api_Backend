# 🏠 CampusON API 로컬 개발 가이드

## 🚀 빠른 시작

### 1. 환경 설정
```bash
# 가상환경 생성
python -m venv venv

# 가상환경 활성화 (Windows)
venv\Scripts\activate

# 가상환경 활성화 (Mac/Linux)
source venv/bin/activate

# 의존성 설치
pip install -r requirements.txt
```

### 2. 데이터베이스 설정
```bash
# PostgreSQL 실행 (Docker 사용시)
docker run --name campuson-db -e POSTGRES_PASSWORD=campuson123 -e POSTGRES_DB=campuson_dev -p 5432:5432 -d postgres:15

# 또는 SQLite 사용 (간단 테스트용)
# .env 파일에서 DATABASE_URL을 sqlite:///./campuson.db로 변경
```

### 3. 환경 변수 설정
`.env` 파일 생성:
```env
# 데이터베이스
DATABASE_URL=postgresql://postgres:campuson123@localhost:5432/campuson_dev

# 보안
SECRET_KEY=local-development-secret-key
JWT_SECRET_KEY=local-jwt-secret-key
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30

# 환경
ENVIRONMENT=development
DEBUG=True

# AI 설정
AI_MODEL_NAME=exaone-3.0
AI_MAX_TOKENS=2048
AI_TEMPERATURE=0.7
```

### 4. 데이터베이스 초기화
```bash
# 마이그레이션 실행
alembic upgrade head

# 샘플 데이터 추가
python add_sample_questions.py
```

### 5. 서버 실행
```bash
# 개발 서버 실행 (자동 리로드)
uvicorn main:app --reload

# 또는 포트 지정
uvicorn main:app --reload --port 8000
```

## 🔗 로컬 URL
- **API**: http://localhost:8000
- **API 문서**: http://localhost:8000/docs
- **Health Check**: http://localhost:8000/health

## 🧪 API 테스트
```bash
# 전체 API 테스트
python test_all_apis.py

# 개별 엔드포인트 테스트
curl http://localhost:8000/health
curl http://localhost:8000/api/auth/login-direct -X POST -H "Content-Type: application/json" -d '{"student_id":"test123","password":"testpass123"}'
```

## 📁 프로젝트 구조
```
📁 2025_api_Backend/
├── 🐍 main.py                 # FastAPI 메인 앱
├── 📦 requirements.txt        # Python 의존성
├── 🗄️ .env                   # 환경 변수 (로컬용)
├── 🧪 test_all_apis.py       # API 테스트
├── 📊 add_sample_questions.py # 샘플 데이터
├── 🚫 .gitignore             # Git 무시 파일
├── 📁 app/                    # FastAPI 앱 모듈들
│   ├── 📁 api/               # API 라우터들
│   ├── 📁 models/            # 데이터베이스 모델
│   ├── 📁 schemas/           # Pydantic 스키마
│   ├── 📁 services/          # 비즈니스 로직
│   └── 📁 db/                # 데이터베이스 설정
└── 📁 alembic/                # 데이터베이스 마이그레이션
```

## 🛠️ 개발 팁

### 코드 변경 감지
`uvicorn main:app --reload` 사용시 파일 변경을 자동으로 감지하고 서버를 재시작합니다.

### API 문서 확인
http://localhost:8000/docs 에서 Swagger UI로 API를 테스트할 수 있습니다.

### 데이터베이스 변경
```bash
# 새 마이그레이션 생성
alembic revision --autogenerate -m "변경사항 설명"

# 마이그레이션 적용
alembic upgrade head
```

### 로그 확인
FastAPI는 기본적으로 콘솔에 로그를 출력합니다. 추가 로그는 `app/core/logging.py`에서 설정할 수 있습니다.

## 🚨 문제 해결

### PostgreSQL 연결 오류
1. PostgreSQL이 실행 중인지 확인
2. 포트 5432가 사용 가능한지 확인
3. 데이터베이스 이름과 비밀번호 확인

### 모듈 import 오류
```bash
# Python 경로에 현재 디렉토리 추가
export PYTHONPATH="${PYTHONPATH}:."

# Windows에서는
set PYTHONPATH=%PYTHONPATH%;.
```

### 의존성 오류
```bash
# 의존성 재설치
pip install -r requirements.txt --force-reinstall

# 또는 가상환경 재생성
deactivate
rm -rf venv
python -m venv venv
```

## 👥 팀 개발

### Git 워크플로우
1. 새 기능 브랜치 생성: `git checkout -b feature/새기능`
2. 변경사항 커밋: `git commit -m "feat: 새 기능 추가"`
3. 브랜치 푸시: `git push origin feature/새기능`
4. Pull Request 생성

### 환경 동기화
팀원이 새로 참여시:
1. 리포지토리 클론
2. 가상환경 생성 및 의존성 설치
3. `.env` 파일 설정
4. 데이터베이스 초기화
5. 서버 실행 테스트

**이제 로컬에서 완벽하게 개발할 수 있습니다!** 🏠✨ 