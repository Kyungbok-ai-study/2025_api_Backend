# 🚀 CampusON API 빠른 배포 가이드

## 🎯 가장 쉬운 방법: Railway (추천!)

### 1단계: GitHub에 업로드 (2분)
```bash
git init
git add .
git commit -m "CampusON API ready for deployment"
git branch -M main
git remote add origin https://github.com/YOUR_USERNAME/campuson-backend.git
git push -u origin main
```

### 2단계: Railway 배포 (3분)
1. 🌐 **https://railway.app** 접속
2. 🔑 **"Login with GitHub"** 클릭
3. ➕ **"New Project"** → **"Deploy from GitHub repo"**
4. 📁 방금 만든 **리포지토리 선택**
5. 🗄️ **"Add PostgreSQL"** 클릭 (데이터베이스 자동 생성)

### 3단계: 환경 변수 설정 (1분)
Railway 대시보드에서 **Variables** 탭에 추가:
```
SECRET_KEY=your_secret_here
JWT_SECRET_KEY=your_jwt_secret_here
ENVIRONMENT=production
DEBUG=false
```

### 4단계: 도메인 연결 (2분)
1. Railway 대시보드 → **"Settings"** → **"Domains"**
2. **"Custom Domain"** → `kbu-ai-team.kro.kr` 입력
3. kro.kr DNS 설정에서 CNAME 추가:
   ```
   kbu-ai-team → [Railway에서 제공된 도메인]
   ```

### ✅ 완료!
- 📱 **API**: `https://kbu-ai-team.kro.kr`
- 📚 **문서**: `https://kbu-ai-team.kro.kr/docs`
- 🔄 **자동 재배포**: GitHub 푸시할 때마다!

---

## 🎯 대안: Render (무료, 간단)

### 1단계: GitHub 업로드 (동일)

### 2단계: Render 배포
1. 🌐 **https://render.com** 접속
2. 🔑 **GitHub 연결**
3. ➕ **"New Web Service"** → 리포지토리 선택
4. 설정:
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `gunicorn -c gunicorn.conf.py app.main:app`

### 3단계: PostgreSQL 추가
1. **"New PostgreSQL"** 클릭
2. Web Service의 환경 변수에 DATABASE_URL 자동 연결

---

## 📊 서비스 비교

| 서비스 | 설정 시간 | 무료 한도 | 자동 HTTPS | 추천도 |
|--------|-----------|-----------|------------|---------|
| 🚄 **Railway** | 5분 | $5/월 크레딧 | ✅ | ⭐⭐⭐⭐⭐ |
| 🎨 **Render** | 7분 | 750시간/월 | ✅ | ⭐⭐⭐⭐ |
| ✈️ **Fly.io** | 10분 | 매우 관대 | ✅ | ⭐⭐⭐ |

## 🆘 문제 해결

### Railway 배포 실패시:
```bash
# 로그 확인
railway logs

# 다시 배포
railway redeploy
```

### Render 배포 실패시:
1. Render 대시보드에서 **"Logs"** 확인
2. **"Manual Deploy"** 클릭

### 공통 해결책:
- `requirements.txt` 확인
- `gunicorn.conf.py` 파일 존재 확인
- 환경 변수 설정 확인

## 🎯 한 줄 요약
**GitHub 업로드 → Railway 연결 → PostgreSQL 추가 → 도메인 설정 = 끝!** 🚀 