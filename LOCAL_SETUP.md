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

# 테스트용 데이터베이스 설정
# .env 파일에서 DATABASE_URL을 postgresql://admin:1234@localhost:5432/kb_learning_test_db로 변경
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

---

## 🛠️ 개발 이어서 하기 위한 실무 팁

### 🔥 첫 번째 실행시 체크리스트
```bash
# 1. 환경 확인
python --version  # 3.9+ 인지 확인
pip --version     # pip 최신인지 확인

# 2. 의존성 설치 확인
pip list | grep fastapi  # FastAPI 설치 확인
pip list | grep uvicorn  # Uvicorn 설치 확인

# 3. 데이터베이스 연결 테스트
python -c "from app.db.database import get_db; print('DB 연결 성공!')"

# 4. 서버 시작 테스트
uvicorn main:app --reload --port 8001  # 다른 포트로 테스트
```

### 💻 VS Code 개발 환경 최적화
```json
// .vscode/settings.json (프로젝트 루트에 생성)
{
    "python.defaultInterpreterPath": "./venv/Scripts/python.exe",
    "python.formatting.provider": "black",
    "python.linting.enabled": true,
    "python.linting.pylintEnabled": false,
    "python.linting.flake8Enabled": true,
    "editor.formatOnSave": true,
    "editor.codeActionsOnSave": {
        "source.organizeImports": true
    },
    "files.associations": {
        "*.env": "dotenv"
    }
}
```

```json
// .vscode/launch.json (디버깅용)
{
    "version": "0.2.0",
    "configurations": [
        {
            "name": "FastAPI Debug",
            "type": "python",
            "request": "launch",
            "module": "uvicorn",
            "args": ["main:app", "--reload", "--port", "8000"],
            "console": "integratedTerminal",
            "env": {
                "PYTHONPATH": "${workspaceFolder}"
            }
        }
    ]
}
```

### 📝 코딩 컨벤션 및 스타일 가이드

**1. 함수/클래스 네이밍**
```python
# ✅ 좋은 예
async def get_user_by_id(user_id: int) -> UserResponse:
    """사용자 ID로 사용자 정보 조회"""
    pass

class DiagnosisService:
    """진단 테스트 관련 서비스"""
    pass

# ❌ 나쁜 예
async def getUserById(userId):  # camelCase 사용 X
    pass
```

**2. 파일 구조 규칙**
```
app/
├── api/           # 각 라우터는 도메인별로 분리
│   ├── auth.py    # 인증 관련
│   ├── diagnosis.py  # 진단 관련
│   └── problems.py   # 문제 관련
├── models/        # 데이터베이스 모델
├── schemas/       # Pydantic 스키마 (요청/응답)
├── services/      # 비즈니스 로직 (DB 연동 등)
└── core/          # 설정, 보안, 의존성 등
```

**3. Import 순서**
```python
# 1. 표준 라이브러리
from datetime import datetime
from typing import List, Optional

# 2. 서드파티 라이브러리  
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

# 3. 로컬 모듈
from app.models.user import User
from app.schemas.auth import LoginRequest
from app.services.auth_service import AuthService
```

### 🗄️ 데이터베이스 작업 팁

**1. 새 모델 추가시**
```bash
# 1. app/models/에 새 모델 클래스 생성
# 2. app/models/__init__.py에 import 추가
# 3. 마이그레이션 생성
alembic revision --autogenerate -m "add new model: ModelName"

# 4. 마이그레이션 검토 후 적용
alembic upgrade head
```

**2. 데이터베이스 초기화 (개발용)**
```bash
# 데이터베이스 완전 초기화
alembic downgrade base
alembic upgrade head
python add_sample_questions.py
```

**3. 쿼리 디버깅**
```python
# SQLAlchemy 쿼리 로그 확인
import logging
logging.getLogger('sqlalchemy.engine').setLevel(logging.INFO)

# 쿼리 결과 확인
query = db.query(User).filter(User.id == user_id)
print(f"SQL: {query}")  # 실제 SQL 확인
result = query.first()
```

### 🔍 API 개발 및 테스트 팁

**1. 새 API 엔드포인트 추가 순서**
```python
# Step 1: 스키마 정의 (app/schemas/)
class NewFeatureRequest(BaseModel):
    name: str
    description: Optional[str] = None

class NewFeatureResponse(BaseModel):
    id: int
    name: str
    created_at: datetime

# Step 2: 서비스 로직 (app/services/)
class NewFeatureService:
    async def create_feature(self, db: Session, request: NewFeatureRequest):
        # 비즈니스 로직 구현
        pass

# Step 3: API 라우터 (app/api/)
@router.post("/features", response_model=NewFeatureResponse)
async def create_feature(
    request: NewFeatureRequest,
    db: Session = Depends(get_db)
):
    service = NewFeatureService()
    return await service.create_feature(db, request)

# Step 4: 테스트 추가 (test_all_apis.py에)
def test_create_feature():
    response = requests.post(f"{BASE_URL}/api/features", json={
        "name": "테스트 기능",
        "description": "테스트용 기능입니다"
    })
    assert response.status_code == 200
```

**2. API 테스트 자동화**
```bash
# 개발하면서 지속적으로 테스트
watch -n 2 python test_all_apis.py  # 2초마다 테스트 실행

# 특정 엔드포인트만 테스트
python -c "
import requests
response = requests.get('http://localhost:8000/health')
print(f'Status: {response.status_code}')
print(f'Response: {response.json()}')
"
```

**3. Swagger UI 적극 활용**
```
http://localhost:8000/docs

📌 팁:
- "Try it out" 버튼으로 바로 테스트
- 스키마 정의 확인
- 예제 응답 확인
- 인증이 필요한 API는 "Authorize" 버튼 사용
```

### 🐛 디버깅 및 에러 해결

**1. 일반적인 에러 패턴**
```python
# ImportError 해결
export PYTHONPATH="${PYTHONPATH}:."  # Linux/Mac
set PYTHONPATH=%PYTHONPATH%;.        # Windows

# Port already in use 해결
netstat -ano | findstr :8000         # Windows
lsof -ti:8000 | xargs kill -9        # Mac/Linux

# 데이터베이스 연결 에러
# 1. PostgreSQL 서비스 확인
# 2. .env 파일의 DATABASE_URL 확인
# 3. 방화벽 설정 확인
```

**2. 로그 레벨 조정**
```python
# main.py 또는 app/core/logging.py에 추가
import logging

# 개발시 디버그 로그 활성화
logging.basicConfig(level=logging.DEBUG)

# 특정 모듈만 디버그
logging.getLogger('app.services').setLevel(logging.DEBUG)
logging.getLogger('sqlalchemy.engine').setLevel(logging.INFO)
```

**3. 유용한 디버깅 도구**
```python
# 1. pdb 디버거
import pdb; pdb.set_trace()  # 브레이크포인트 설정

# 2. 변수 상태 확인
print(f"DEBUG: user_id={user_id}, type={type(user_id)}")

# 3. 함수 실행 시간 측정
import time
start = time.time()
# ... 코드 실행 ...
print(f"실행 시간: {time.time() - start:.2f}초")
```

### ⚡ 성능 최적화 팁

**1. 데이터베이스 쿼리 최적화**
```python
# ❌ N+1 쿼리 문제
users = db.query(User).all()
for user in users:
    print(user.profile.name)  # 각 사용자마다 추가 쿼리

# ✅ 조인으로 해결
users = db.query(User).options(joinedload(User.profile)).all()
for user in users:
    print(user.profile.name)  # 한 번의 쿼리로 해결
```

**2. 응답 시간 모니터링**
```python
# 미들웨어로 API 응답 시간 측정
import time
from fastapi import Request

@app.middleware("http")
async def add_process_time_header(request: Request, call_next):
    start_time = time.time()
    response = await call_next(request)
    process_time = time.time() - start_time
    response.headers["X-Process-Time"] = str(process_time)
    print(f"API {request.url.path}: {process_time:.3f}s")
    return response
```

### 🧪 테스트 전략

**1. 단위 테스트 추가**
```python
# test_unit.py 생성
import pytest
from app.services.auth_service import AuthService

@pytest.mark.asyncio
async def test_login_success():
    # Given
    service = AuthService()
    student_id = "test123"
    password = "testpass123"
    
    # When
    result = await service.authenticate(student_id, password)
    
    # Then
    assert result is not None
    assert result.student_id == student_id
```

**2. 테스트 실행**
```bash
# 전체 테스트
pytest

# 특정 테스트만
pytest test_unit.py::test_login_success

# 커버리지 확인
pytest --cov=app
```

### 🎯 개발 워크플로우 Best Practice

**1. 새 기능 개발시**
```bash
# 1. 새 브랜치 생성
git checkout -b feature/user-profile-api

# 2. 개발 진행
# - 스키마 정의
# - 서비스 로직 구현  
# - API 엔드포인트 추가
# - 테스트 코드 작성

# 3. 테스트 실행
python test_all_apis.py

# 4. 커밋 (규칙 준수)
git add .
git commit -m "feat: 사용자 프로필 조회 API 추가"

# 5. 푸시 및 PR
git push origin feature/user-profile-api
```

**2. 코드 리뷰 체크포인트**
- [ ] API 스키마가 명확하게 정의되었는가?
- [ ] 에러 처리가 적절한가?
- [ ] 보안 이슈는 없는가? (SQL Injection, XSS 등)
- [ ] 성능상 문제는 없는가?
- [ ] 테스트 코드가 포함되었는가?
- [ ] 문서가 업데이트되었는가?

### 🔧 유용한 개발 도구

**1. API 테스트 도구**
```bash
# HTTPie (curl 대안)
pip install httpie
http GET localhost:8000/health
http POST localhost:8000/api/auth/login-direct student_id=test123 password=testpass123

# Postman 컬렉션 익스포트
# Swagger UI에서 "Export" → "OpenAPI JSON" → Postman으로 import
```

**2. 데이터베이스 GUI 도구**
- **pgAdmin** (PostgreSQL)
- **DBeaver** (범용)
- **DataGrip** (JetBrains, 유료)

**3. 코드 품질 도구**
```bash
# 설치
pip install black isort flake8

# 코드 포맷팅
black .
isort .

# 린팅 체크
flake8 app/
```

### 🔄 자주 사용하는 명령어 모음

```bash
# 서버 관련
uvicorn main:app --reload                    # 개발 서버 시작
uvicorn main:app --reload --port 8001        # 다른 포트로 시작
pkill -f uvicorn                            # 서버 강제 종료

# 데이터베이스
alembic revision --autogenerate -m "메시지"  # 마이그레이션 생성
alembic upgrade head                         # 마이그레이션 적용
alembic downgrade -1                         # 마지막 마이그레이션 취소
python add_sample_questions.py              # 샘플 데이터 추가

# 테스트
python test_all_apis.py                     # 전체 API 테스트
pytest                                      # 단위 테스트
python -m pytest --cov=app                  # 커버리지 테스트

# Git
git status                                   # 상태 확인
git add .                                    # 모든 변경사항 추가
git commit -m "feat: 새 기능"                # 커밋
git push origin main                         # 푸시
git pull origin main                         # 최신 코드 가져오기

# 의존성 관리
pip freeze > requirements.txt               # 의존성 목록 업데이트
pip install -r requirements.txt             # 의존성 설치
```

### 🆘 응급 상황 대처법

**1. 서버가 안 켜질 때**
```bash
# 포트 충돌 확인
netstat -tulpn | grep :8000

# 프로세스 강제 종료
pkill -f "uvicorn"

# 의존성 문제
pip install -r requirements.txt --force-reinstall

# 환경 변수 확인
cat .env  # 파일 존재하는지 확인
```

**2. 데이터베이스 연결 안 될 때**
```bash
# PostgreSQL 상태 확인
sudo systemctl status postgresql

# Docker 컨테이너 확인
docker ps -a | grep campuson

# 연결 테스트
python -c "
import psycopg2
try:
    conn = psycopg2.connect('postgresql://postgres:campuson123@localhost/campuson_dev')
    print('DB 연결 성공!')
except Exception as e:
    print(f'DB 연결 실패: {e}')
"
```

**3. 마이그레이션 문제**
```bash
# 마이그레이션 상태 확인
alembic current

# 마이그레이션 이력 확인
alembic history

# 강제 리셋 (주의!)
alembic downgrade base
alembic upgrade head
```

### 📚 학습 리소스

**1. FastAPI 관련**
- [FastAPI 공식 문서](https://fastapi.tiangolo.com/)
- [SQLAlchemy 문서](https://docs.sqlalchemy.org/)
- [Pydantic 문서](https://pydantic-docs.helpmanual.io/)

**2. 추천 유튜브 채널**
- FastAPI 튜토리얼 시리즈
- Python 웹 개발 강의

**3. 유용한 블로그/커뮤니티**
- Real Python (FastAPI 섹션)
- FastAPI 한국 사용자 모임

---

## 🎯 개발 완료 체크리스트

새로운 기능을 완성했을 때 확인할 항목들:

- [ ] **API 스키마**: 요청/응답 스키마가 명확히 정의됨
- [ ] **에러 핸들링**: 적절한 HTTP 상태 코드와 에러 메시지
- [ ] **인증/권한**: 필요시 JWT 토큰 검증 추가
- [ ] **데이터 검증**: Pydantic으로 입력 데이터 검증
- [ ] **데이터베이스**: 트랜잭션 처리 및 롤백 고려
- [ ] **테스트 코드**: 최소한 Happy Path 테스트
- [ ] **문서화**: API 문서 자동 생성 확인
- [ ] **성능**: 쿼리 최적화 및 응답 시간 확인
- [ ] **보안**: SQL Injection, XSS 등 보안 취약점 점검
- [ ] **로깅**: 적절한 로그 레벨과 메시지

**이제 팀원 누구나 쉽게 개발을 이어받을 수 있습니다!** 🏠✨

---

## 💡 마지막 팁: 개발자 생산성 향상

**1. IDE 설정 완벽히 하기**
- Python 인터프리터 설정
- 자동 완성 활성화
- 디버거 설정
- Git 통합 활용

**2. 단축키 활용**
- `Ctrl + Shift + P`: 명령 팔레트
- `F5`: 디버깅 시작
- `Ctrl + ` `: 터미널 열기
- `Ctrl + Shift + ` `: 새 터미널

**3. 시간 절약 팁**
```bash
# 별칭(alias) 설정 (.bashrc 또는 .zshrc에 추가)
alias serve="uvicorn main:app --reload"
alias test="python test_all_apis.py"
alias mg="alembic upgrade head"
alias shell="python -i -c 'from app.db.database import get_db; db=next(get_db())'"
```

**4. 지속적인 학습**
- 매주 새로운 FastAPI 기능 하나씩 학습
- 코드 리뷰를 통한 상호 학습
- 성능 측정 및 개선 경험 공유

**Happy Coding! 🚀** 