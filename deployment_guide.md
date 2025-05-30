# CampusON API 도메인 배포 가이드

## 🌐 kbu-ai-team.kro.kr 배포 방법

### 1. 서버 환경 준비

#### 1.1 클라우드 서버 옵션
- **AWS EC2** (추천)
- **Google Cloud Platform**
- **Naver Cloud Platform**
- **Vultr, DigitalOcean** 등

#### 1.2 최소 권장 사양
```
- OS: Ubuntu 20.04 LTS 이상
- RAM: 2GB 이상
- Storage: 20GB 이상
- CPU: 2 Core 이상
```

### 2. 서버 초기 설정

#### 2.1 패키지 업데이트
```bash
sudo apt update && sudo apt upgrade -y
```

#### 2.2 필수 패키지 설치
```bash
# Python 3.9+ 설치
sudo apt install python3.9 python3.9-venv python3-pip -y

# PostgreSQL 설치
sudo apt install postgresql postgresql-contrib -y

# Nginx 설치
sudo apt install nginx -y

# 기타 필수 도구
sudo apt install git curl wget ufw -y
```

### 3. 프로젝트 배포

#### 3.1 프로젝트 복사
```bash
# 서버에 프로젝트 디렉토리 생성
sudo mkdir -p /var/www/campuson
sudo chown $USER:$USER /var/www/campuson

# Git으로 프로젝트 클론 (또는 파일 업로드)
cd /var/www/campuson
git clone [your-repository-url] .

# 또는 로컬에서 파일 업로드
# scp -r /path/to/backend/ user@server:/var/www/campuson/
```

#### 3.2 Python 가상환경 설정
```bash
cd /var/www/campuson
python3.9 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 4. 데이터베이스 설정

#### 4.1 PostgreSQL 설정
```bash
# PostgreSQL 서비스 시작
sudo systemctl start postgresql
sudo systemctl enable postgresql

# 데이터베이스 및 사용자 생성
sudo -u postgres psql << EOF
CREATE DATABASE campuson_prod;
CREATE USER campuson_user WITH PASSWORD 'your_secure_password';
GRANT ALL PRIVILEGES ON DATABASE campuson_prod TO campuson_user;
ALTER USER campuson_user CREATEDB;
\q
EOF
```

#### 4.2 환경 변수 설정
```bash
# 프로덕션 환경 설정 파일 생성
cat > /var/www/campuson/.env.prod << EOF
# Database
DATABASE_URL=postgresql://campuson_user:your_secure_password@localhost/campuson_prod

# Security
SECRET_KEY=your_super_secret_key_here
JWT_SECRET_KEY=your_jwt_secret_key_here
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30

# Environment
ENVIRONMENT=production
DEBUG=False

# CORS
ALLOWED_ORIGINS=["https://kbu-ai-team.kro.kr", "https://www.kbu-ai-team.kro.kr"]

# AI Settings
AI_MODEL_NAME=exaone-3.0
AI_MAX_TOKENS=2048
AI_TEMPERATURE=0.7
EOF
```

### 5. 프로덕션용 설정 파일 생성

#### 5.1 Gunicorn 설정
```bash
# gunicorn 설치
pip install gunicorn

# Gunicorn 설정 파일 생성
cat > /var/www/campuson/gunicorn.conf.py << EOF
bind = "127.0.0.1:8000"
workers = 4
worker_class = "uvicorn.workers.UvicornWorker"
worker_connections = 1000
max_requests = 1000
max_requests_jitter = 100
timeout = 30
keepalive = 5
preload_app = True
EOF
```

#### 5.2 systemd 서비스 파일 생성
```bash
sudo cat > /etc/systemd/system/campuson.service << EOF
[Unit]
Description=CampusON FastAPI application
After=network.target

[Service]
Type=notify
User=www-data
Group=www-data
RuntimeDirectory=campuson
WorkingDirectory=/var/www/campuson
Environment=PATH=/var/www/campuson/venv/bin
EnvironmentFile=/var/www/campuson/.env.prod
ExecStart=/var/www/campuson/venv/bin/gunicorn -c gunicorn.conf.py app.main:app
ExecReload=/bin/kill -s HUP \$MAINPID
KillMode=mixed
TimeoutStopSec=5
PrivateTmp=true

[Install]
WantedBy=multi-user.target
EOF

# 서비스 권한 설정
sudo chown -R www-data:www-data /var/www/campuson
sudo systemctl daemon-reload
sudo systemctl enable campuson
sudo systemctl start campuson
```

### 6. Nginx 설정

#### 6.1 Nginx 설정 파일 생성
```bash
sudo cat > /etc/nginx/sites-available/campuson << 'EOF'
server {
    listen 80;
    server_name kbu-ai-team.kro.kr www.kbu-ai-team.kro.kr;
    
    # API 경로
    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;
    }
    
    # 정적 파일 (향후 프론트엔드용)
    location /static/ {
        alias /var/www/campuson/static/;
        expires 30d;
        add_header Cache-Control "public, immutable";
    }
    
    # Health check
    location /health {
        proxy_pass http://127.0.0.1:8000/health;
        access_log off;
    }
}
EOF

# 사이트 활성화
sudo ln -s /etc/nginx/sites-available/campuson /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
```

### 7. SSL 인증서 설정

#### 7.1 Let's Encrypt 설치
```bash
sudo apt install certbot python3-certbot-nginx -y
```

#### 7.2 SSL 인증서 발급
```bash
sudo certbot --nginx -d kbu-ai-team.kro.kr -d www.kbu-ai-team.kro.kr
```

### 8. 방화벽 설정

```bash
# UFW 방화벽 설정
sudo ufw enable
sudo ufw allow ssh
sudo ufw allow 'Nginx Full'
sudo ufw status
```

### 9. 데이터베이스 마이그레이션

```bash
cd /var/www/campuson
source venv/bin/activate

# 환경 변수 로드
export $(cat .env.prod | xargs)

# 마이그레이션 실행
alembic upgrade head

# 샘플 데이터 추가
python add_sample_questions.py
```

### 10. 도메인 DNS 설정

#### 10.1 kro.kr 도메인 관리
1. kro.kr 도메인 관리 페이지 접속
2. DNS 설정에서 A 레코드 추가:
   ```
   @ (또는 kbu-ai-team) -> 서버 IP 주소
   www -> 서버 IP 주소
   ```

### 11. 모니터링 설정

#### 11.1 로그 확인
```bash
# 애플리케이션 로그
sudo journalctl -u campuson -f

# Nginx 로그
sudo tail -f /var/log/nginx/access.log
sudo tail -f /var/log/nginx/error.log
```

#### 11.2 상태 확인
```bash
# 서비스 상태
sudo systemctl status campuson
sudo systemctl status nginx
sudo systemctl status postgresql

# API 테스트
curl https://kbu-ai-team.kro.kr/health
```

### 12. 자동 백업 설정

#### 12.1 데이터베이스 백업 스크립트
```bash
sudo cat > /usr/local/bin/backup_campuson.sh << 'EOF'
#!/bin/bash
BACKUP_DIR="/var/backups/campuson"
DATE=$(date +"%Y%m%d_%H%M%S")
mkdir -p $BACKUP_DIR

# 데이터베이스 백업
pg_dump -h localhost -U campuson_user -d campuson_prod > $BACKUP_DIR/db_backup_$DATE.sql

# 파일 백업 (선택사항)
tar -czf $BACKUP_DIR/files_backup_$DATE.tar.gz /var/www/campuson

# 7일 이상된 백업 삭제
find $BACKUP_DIR -name "*.sql" -mtime +7 -delete
find $BACKUP_DIR -name "*.tar.gz" -mtime +7 -delete
EOF

sudo chmod +x /usr/local/bin/backup_campuson.sh

# 일일 백업 크론 설정
(crontab -l 2>/dev/null; echo "0 2 * * * /usr/local/bin/backup_campuson.sh") | crontab -
```

### 13. 성능 최적화

#### 13.1 PostgreSQL 튜닝
```bash
sudo nano /etc/postgresql/*/main/postgresql.conf
```
```
# 메모리 설정 (RAM의 25% 정도)
shared_buffers = 512MB
effective_cache_size = 1536MB
work_mem = 16MB
maintenance_work_mem = 128MB

# 연결 설정
max_connections = 100
```

#### 13.2 Nginx 캐싱 설정
```nginx
# /etc/nginx/sites-available/campuson에 추가
location ~* \.(jpg|jpeg|png|gif|ico|css|js)$ {
    expires 1y;
    add_header Cache-Control "public, immutable";
}
```

### 🎯 최종 체크리스트

- [ ] 서버 환경 구성 완료
- [ ] 프로젝트 배포 완료
- [ ] 데이터베이스 설정 완료
- [ ] Gunicorn 서비스 실행
- [ ] Nginx 설정 완료
- [ ] SSL 인증서 설정 완료
- [ ] 방화벽 설정 완료
- [ ] DNS 설정 완료
- [ ] API 동작 테스트 완료
- [ ] 모니터링 설정 완료
- [ ] 백업 설정 완료

### 🔍 문제 해결

#### 일반적인 문제들:
1. **502 Bad Gateway**: Gunicorn 서비스 상태 확인
2. **SSL 인증서 오류**: DNS 전파 대기 후 재시도
3. **데이터베이스 연결 오류**: 환경 변수 및 PostgreSQL 설정 확인
4. **CORS 오류**: 환경 변수의 ALLOWED_ORIGINS 설정 확인

### 📞 배포 후 테스트

```bash
# API 기본 테스트
curl https://kbu-ai-team.kro.kr/health
curl https://kbu-ai-team.kro.kr/

# 인증 테스트
curl -X POST https://kbu-ai-team.kro.kr/api/auth/login-direct \
  -H "Content-Type: application/json" \
  -d '{"student_id": "test123", "password": "testpass123"}'
```

이 가이드를 따라하시면 성공적으로 배포할 수 있습니다! 🚀 