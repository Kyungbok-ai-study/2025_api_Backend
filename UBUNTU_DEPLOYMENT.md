# 🐧 우분투 22.04.1 LTS 배포 가이드

## 📋 개요

이 문서는 CampusON 백엔드를 우분투 22.04.1 LTS 환경에서 배포하는 방법을 설명합니다.

## 🔧 시스템 요구사항

### 최소 사양
- **OS**: Ubuntu 22.04.1 LTS
- **CPU**: 2 cores
- **RAM**: 4GB
- **Storage**: 20GB
- **Network**: 인터넷 연결

### 권장 사양
- **OS**: Ubuntu 22.04.1 LTS
- **CPU**: 4 cores
- **RAM**: 8GB
- **Storage**: 50GB SSD
- **Network**: 고속 인터넷 연결

## 🚀 자동 배포 (권장)

### 1. 배포 스크립트 실행

```bash
# 스크립트 실행 권한 부여
chmod +x deploy_ubuntu.sh

# 배포 실행
./deploy_ubuntu.sh
```

이 스크립트는 다음 작업을 자동으로 수행합니다:
- 시스템 패키지 업데이트
- 필수 소프트웨어 설치
- PostgreSQL, Redis, Qdrant 설정
- Python 환경 구성
- 서비스 설정 및 시작

### 2. 환경 변수 설정

```bash
# .env 파일 수정
nano /opt/campuson/.env

# 필수 설정 항목
GEMINI_API_KEY=your-gemini-api-key
OPENAI_API_KEY=your-openai-api-key
SECRET_KEY=your-super-secret-key
JWT_SECRET_KEY=your-jwt-secret-key
```

## 🔧 수동 배포

### 1. 시스템 업데이트

```bash
sudo apt update && sudo apt upgrade -y
```

### 2. 필수 패키지 설치

```bash
sudo apt install -y \
    python3.9 \
    python3.9-dev \
    python3.9-venv \
    python3-pip \
    build-essential \
    curl \
    wget \
    git \
    vim \
    htop \
    nginx \
    supervisor \
    poppler-utils \
    libjpeg-dev \
    libpng-dev \
    libtiff-dev \
    libfreetype6-dev \
    postgresql-client \
    libpq-dev \
    redis-server
```

### 3. PostgreSQL 설치 및 설정

```bash
# PostgreSQL 설치
sudo apt install -y postgresql postgresql-contrib

# 서비스 시작
sudo systemctl start postgresql
sudo systemctl enable postgresql

# 데이터베이스 생성
sudo -u postgres psql -c "CREATE DATABASE kb_learning_db;"
sudo -u postgres psql -c "CREATE USER admin WITH PASSWORD '1234';"
sudo -u postgres psql -c "GRANT ALL PRIVILEGES ON DATABASE kb_learning_db TO admin;"
sudo -u postgres psql -c "ALTER USER admin CREATEDB;"
```

### 4. Docker 설치 (Qdrant용)

```bash
# Docker 설치
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
sudo usermod -aG docker $USER

# Docker Compose 설치
sudo curl -L "https://github.com/docker/compose/releases/download/v2.20.0/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose

# 로그아웃 후 다시 로그인
```

### 5. 프로젝트 설정

```bash
# 프로젝트 디렉토리 생성
sudo mkdir -p /opt/campuson
sudo chown $USER:$USER /opt/campuson

# 프로젝트 파일 복사
cp -r . /opt/campuson/
cd /opt/campuson

# Python 가상환경 생성
python3.9 -m venv venv
source venv/bin/activate

# 의존성 설치
pip install --upgrade pip
pip install -r requirements.txt
pip install -r requirements_parser.txt
pip install -r requirements_deepseek.txt
```

### 6. 환경 변수 설정

```bash
# 환경 변수 파일 생성
cp env.ubuntu.example .env

# 환경 변수 수정
nano .env
```

### 7. 데이터베이스 마이그레이션

```bash
source venv/bin/activate
alembic upgrade head
```

### 8. Qdrant 시작

```bash
docker run -d \
    --name campuson_qdrant \
    -p 6333:6333 \
    -p 6334:6334 \
    -v $(pwd)/qdrant_data:/qdrant/storage \
    --restart unless-stopped \
    qdrant/qdrant:latest
```

### 9. Redis 시작

```bash
sudo systemctl start redis-server
sudo systemctl enable redis-server
```

### 10. Supervisor 설정

```bash
# Supervisor 설정 파일 생성
sudo nano /etc/supervisor/conf.d/campuson.conf
```

```ini
[program:campuson]
command=/opt/campuson/venv/bin/uvicorn main:app --host 0.0.0.0 --port 8000 --workers 4
directory=/opt/campuson
user=ubuntu
autostart=true
autorestart=true
redirect_stderr=true
stdout_logfile=/opt/campuson/logs/campuson.log
environment=PATH="/opt/campuson/venv/bin"
```

```bash
# Supervisor 재시작
sudo systemctl restart supervisor
sudo systemctl enable supervisor
```

### 11. Nginx 설정

```bash
# Nginx 설정 파일 생성
sudo nano /etc/nginx/sites-available/campuson
```

```nginx
server {
    listen 80;
    server_name your-domain.com;  # 도메인 변경

    client_max_body_size 50M;

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

    location /uploads/ {
        alias /opt/campuson/uploads/;
        expires 1d;
        add_header Cache-Control "public, immutable";
    }

    location /health {
        proxy_pass http://127.0.0.1:8000/health;
        access_log off;
    }
}
```

```bash
# 사이트 활성화
sudo ln -s /etc/nginx/sites-available/campuson /etc/nginx/sites-enabled/
sudo rm /etc/nginx/sites-enabled/default

# Nginx 테스트 및 재시작
sudo nginx -t
sudo systemctl restart nginx
sudo systemctl enable nginx
```

### 12. 방화벽 설정

```bash
sudo ufw allow 22/tcp    # SSH
sudo ufw allow 80/tcp    # HTTP
sudo ufw allow 443/tcp   # HTTPS
sudo ufw enable
```

## 🔍 서비스 확인

### 서비스 상태 확인

```bash
# PostgreSQL
sudo systemctl status postgresql

# Redis
sudo systemctl status redis-server

# Qdrant
docker ps | grep qdrant

# Supervisor
sudo systemctl status supervisor

# Nginx
sudo systemctl status nginx

# CampusON 애플리케이션
sudo supervisorctl status campuson
```

### API 테스트

```bash
# 헬스체크
curl http://localhost:8000/health

# API 문서 접속
curl http://localhost:8000/docs
```

## 📊 모니터링 및 관리

### 로그 확인

```bash
# 애플리케이션 로그
tail -f /opt/campuson/logs/campuson.log

# Nginx 로그
sudo tail -f /var/log/nginx/access.log
sudo tail -f /var/log/nginx/error.log

# PostgreSQL 로그
sudo tail -f /var/log/postgresql/postgresql-15-main.log

# Redis 로그
sudo tail -f /var/log/redis/redis-server.log
```

### 서비스 관리

```bash
# CampusON 재시작
sudo supervisorctl restart campuson

# 서비스 상태 확인
sudo supervisorctl status

# Nginx 재시작
sudo systemctl restart nginx

# PostgreSQL 재시작
sudo systemctl restart postgresql

# Redis 재시작
sudo systemctl restart redis-server

# Qdrant 재시작
docker restart campuson_qdrant
```

### 백업

```bash
# 데이터베이스 백업
pg_dump -h localhost -U admin -d kb_learning_db > backup_$(date +%Y%m%d).sql

# Qdrant 데이터 백업
tar -czf qdrant_backup_$(date +%Y%m%d).tar.gz /opt/campuson/qdrant_data

# 업로드 파일 백업
tar -czf uploads_backup_$(date +%Y%m%d).tar.gz /opt/campuson/uploads
```

## 🔒 SSL 인증서 설정 (Let's Encrypt)

```bash
# Certbot 설치
sudo apt install certbot python3-certbot-nginx

# SSL 인증서 발급
sudo certbot --nginx -d your-domain.com

# 자동 갱신 설정
sudo crontab -e
# 다음 줄 추가: 0 12 * * * /usr/bin/certbot renew --quiet
```

## 🚨 문제 해결

### 일반적인 문제

1. **포트 충돌**
   ```bash
   sudo netstat -tulpn | grep :8000
   sudo kill -9 <PID>
   ```

2. **권한 문제**
   ```bash
   sudo chown -R $USER:$USER /opt/campuson
   chmod +x /opt/campuson/deploy_ubuntu.sh
   ```

3. **의존성 문제**
   ```bash
   source /opt/campuson/venv/bin/activate
   pip install --upgrade pip
   pip install -r requirements.txt --force-reinstall
   ```

4. **데이터베이스 연결 문제**
   ```bash
   # PostgreSQL 상태 확인
   sudo systemctl status postgresql
   
   # 연결 테스트
   psql -h localhost -U admin -d kb_learning_db
   ```

### 로그 분석

```bash
# 오류 로그 검색
grep -i error /opt/campuson/logs/campuson.log

# 최근 로그 확인
tail -n 100 /opt/campuson/logs/campuson.log
```

## 📈 성능 최적화

### 시스템 튜닝

```bash
# 파일 디스크립터 제한 증가
echo "* soft nofile 65536" | sudo tee -a /etc/security/limits.conf
echo "* hard nofile 65536" | sudo tee -a /etc/security/limits.conf

# 커널 파라미터 최적화
echo "net.core.somaxconn = 65536" | sudo tee -a /etc/sysctl.conf
echo "net.ipv4.tcp_max_syn_backlog = 65536" | sudo tee -a /etc/sysctl.conf
sudo sysctl -p
```

### PostgreSQL 튜닝

```bash
sudo nano /etc/postgresql/15/main/postgresql.conf
```

```ini
# 메모리 설정 (8GB RAM 기준)
shared_buffers = 2GB
effective_cache_size = 6GB
work_mem = 64MB
maintenance_work_mem = 512MB

# 연결 설정
max_connections = 200

# 로깅 설정
log_min_duration_statement = 1000
```

## 🔄 업데이트 및 배포

### 코드 업데이트

```bash
cd /opt/campuson
git pull origin main
source venv/bin/activate
pip install -r requirements.txt
alembic upgrade head
sudo supervisorctl restart campuson
```

### 무중단 배포

```bash
# Blue-Green 배포 스크립트 예시
./scripts/blue_green_deploy.sh
```

## 📞 지원

문제가 발생하면 다음을 확인하세요:

1. 로그 파일 검토
2. 서비스 상태 확인
3. 네트워크 연결 확인
4. 디스크 공간 확인

---

**🎯 배포 완료 후 확인사항:**
- [ ] API 서버 정상 작동 (http://your-domain.com/health)
- [ ] 데이터베이스 연결 확인
- [ ] 벡터 DB (Qdrant) 연결 확인
- [ ] 파일 업로드 기능 테스트
- [ ] SSL 인증서 설정 (프로덕션 환경)
- [ ] 백업 시스템 구성
- [ ] 모니터링 시스템 설정 