# 🚀 Railway로 GitHub 연동 배포하기

## Railway 배포 (가장 쉬운 방법!)

### 1단계: GitHub 리포지토리 생성
```bash
# 현재 프로젝트를 GitHub에 업로드
git init
git add .
git commit -m "feat: CampusON API 배포 준비 완료 - Railway, Render 설정 파일 추가"
git branch -M main
git remote -v
git remote add origin https://github.com/Kyungbok-ai-study/2025_api_Backend.git
git push -u origin main
```

### 2단계: Railway 설정 파일 생성
Railway는 자동으로 FastAPI를 인식하지만, 설정을 명확히 해줍시다.

**railway.json** (이미 있는 gunicorn.conf.py 사용):
```json
{
  "$schema": "https://railway.app/railway.schema.json",
  "build": {
    "builder": "NIXPACKS"
  },
  "deploy": {
    "startCommand": "gunicorn -c gunicorn.conf.py app.main:app",
    "healthcheckPath": "/health",
    "healthcheckTimeout": 100
  }
}
```

### 3단계: Railway 배포
1. **Railway 가입**: https://railway.app 
2. **GitHub 연결**: "Login with GitHub"
3. **새 프로젝트**: "New Project" → "Deploy from GitHub repo"
4. **리포지토리 선택**: 방금 만든 리포지토리 선택
5. **환경 변수 설정**: 아래 참고

### 4단계: 환경 변수 설정 (Railway 대시보드에서)
```
DATABASE_URL=postgresql://postgres:password@postgres:5432/railway
SECRET_KEY=your_secret_key_here
JWT_SECRET_KEY=your_jwt_secret_key_here
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
ENVIRONMENT=production
DEBUG=False
```

### 5단계: PostgreSQL 추가
Railway 대시보드에서:
1. "Add Service" → "Database" → "PostgreSQL"
2. 자동으로 DATABASE_URL이 설정됨

### 6단계: 커스텀 도메인 연결
1. Railway 대시보드 → "Settings" → "Domains"
2. "Custom Domain" → `kbu-ai-team.kro.kr` 입력
3. DNS 설정에서 CNAME 추가: `kbu-ai-team` → Railway 도메인

### 🎉 완료!
- 자동 HTTPS 적용
- GitHub 푸시할 때마다 자동 재배포
- 무료 티어로 충분히 사용 가능

---

## 대안 서비스들

### 2. **Render** 
```yaml
# render.yaml
services:
  - type: web
    name: campuson-api
    env: python
    buildCommand: pip install -r requirements.txt
    startCommand: gunicorn -c gunicorn.conf.py app.main:app
    envVars:
      - key: DATABASE_URL
        fromDatabase:
          name: campuson-db
          property: connectionString
```

### 3. **Fly.io**
```toml
# fly.toml
app = "campuson-api"

[build]
  builder = "paketobuildpacks/builder:base"

[[services]]
  http_checks = []
  internal_port = 8000
  processes = ["app"]
  protocol = "tcp"
  script_checks = []
```

### 4. **Vercel** (API Routes용)
```json
{
  "builds": [
    {
      "src": "app/main.py",
      "use": "@vercel/python"
    }
  ],
  "routes": [
    {
      "src": "/(.*)",
      "dest": "app/main.py"
    }
  ]
}
```

## 📊 서비스 비교

| 서비스 | 난이도 | 무료 한도 | PostgreSQL | 커스텀 도메인 |
|--------|---------|-----------|------------|---------------|
| Railway | ⭐ | 월 5달러 크레딧 | ✅ | ✅ |
| Render | ⭐⭐ | 750시간/월 | ✅ | ✅ |
| Fly.io | ⭐⭐⭐ | 2340시간/월 | ✅ | ✅ |
| Vercel | ⭐⭐ | Function 제한 | ❌ (별도) | ✅ |

**추천**: Railway가 가장 쉽고 FastAPI + PostgreSQL에 최적화되어 있습니다! 