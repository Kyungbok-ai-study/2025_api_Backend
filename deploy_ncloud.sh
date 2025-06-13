#!/bin/bash

# 네이버 클라우드 플랫폼(Ncloud) 우분투 서버 CampusON 백엔드 배포 스크립트
# 사용법: chmod +x deploy_ncloud.sh && ./deploy_ncloud.sh

set -e  # 오류 발생 시 스크립트 중단

echo "☁️ Ncloud CampusON 백엔드 배포 시작..."

# 색상 정의
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
NC='\033[0m' # No Color

# 로그 함수
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

log_ncloud() {
    echo -e "${PURPLE}[NCLOUD]${NC} $1"
}

# Ncloud 환경 확인
log_ncloud "Ncloud 환경 확인 중..."

# 메타데이터 서비스로 Ncloud 인스턴스 확인
if curl -s --max-time 3 http://169.254.169.254/latest/meta-data/instance-id > /dev/null 2>&1; then
    INSTANCE_ID=$(curl -s http://169.254.169.254/latest/meta-data/instance-id)
    PUBLIC_IP=$(curl -s http://169.254.169.254/latest/meta-data/public-ipv4)
    log_ncloud "Ncloud 인스턴스 감지됨 - ID: $INSTANCE_ID, IP: $PUBLIC_IP"
else
    log_warning "Ncloud 메타데이터 서비스에 접근할 수 없습니다. 일반 서버로 진행합니다."
fi

# 1. 시스템 업데이트
log_info "시스템 패키지 업데이트 중..."
sudo apt update && sudo apt upgrade -y

# 2. Ncloud 특화 패키지 설치
log_ncloud "Ncloud 최적화 패키지 설치 중..."
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
    iotop \
    nginx \
    supervisor \
    poppler-utils \
    libjpeg-dev \
    libpng-dev \
    libtiff-dev \
    libfreetype6-dev \
    postgresql-client \
    libpq-dev \
    redis-server \
    awscli \
    unzip

# 3. Python 심볼릭 링크 생성
log_info "Python 심볼릭 링크 설정 중..."
sudo ln -sf /usr/bin/python3.9 /usr/bin/python
sudo ln -sf /usr/bin/pip3 /usr/bin/pip

# 4. PostgreSQL 설치 및 설정
log_info "PostgreSQL 설치 및 설정 중..."
sudo apt install -y postgresql postgresql-contrib

# PostgreSQL 서비스 시작
sudo systemctl start postgresql
sudo systemctl enable postgresql

# 데이터베이스 및 사용자 생성
sudo -u postgres psql -c "CREATE DATABASE kb_learning_db;" || log_warning "데이터베이스가 이미 존재합니다."
sudo -u postgres psql -c "CREATE USER admin WITH PASSWORD '1234';" || log_warning "사용자가 이미 존재합니다."
sudo -u postgres psql -c "GRANT ALL PRIVILEGES ON DATABASE kb_learning_db TO admin;" || true
sudo -u postgres psql -c "ALTER USER admin CREATEDB;" || true

# 5. Docker 설치 (Ncloud 최적화)
log_ncloud "Docker 설치 중 (Ncloud 최적화)..."
if ! command -v docker &> /dev/null; then
    curl -fsSL https://get.docker.com -o get-docker.sh
    sudo sh get-docker.sh
    sudo usermod -aG docker $USER
    
    # Ncloud 네트워크 최적화를 위한 Docker 설정
    sudo mkdir -p /etc/docker
    sudo tee /etc/docker/daemon.json > /dev/null <<EOF
{
    "log-driver": "json-file",
    "log-opts": {
        "max-size": "10m",
        "max-file": "3"
    },
    "storage-driver": "overlay2",
    "dns": ["8.8.8.8", "8.8.4.4"]
}
EOF
    sudo systemctl restart docker
    log_warning "Docker 설치 완료. 로그아웃 후 다시 로그인하세요."
fi

# Docker Compose 설치
if ! command -v docker-compose &> /dev/null; then
    sudo curl -L "https://github.com/docker/compose/releases/download/v2.20.0/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
    sudo chmod +x /usr/local/bin/docker-compose
fi

# 6. 프로젝트 디렉토리 설정
PROJECT_DIR="/opt/campuson"
log_info "프로젝트 디렉토리 설정: $PROJECT_DIR"

if [ ! -d "$PROJECT_DIR" ]; then
    sudo mkdir -p $PROJECT_DIR
    sudo chown $USER:$USER $PROJECT_DIR
fi

# 현재 디렉토리의 파일들을 프로젝트 디렉토리로 복사
log_info "프로젝트 파일 복사 중..."
cp -r . $PROJECT_DIR/
cd $PROJECT_DIR

# 7. Python 가상환경 생성
log_info "Python 가상환경 생성 중..."
python3.9 -m venv venv
source venv/bin/activate

# pip 업그레이드
pip install --upgrade pip setuptools wheel

# 8. Python 의존성 설치
log_info "Python 의존성 설치 중..."
pip install -r requirements.txt
pip install -r requirements_parser.txt
pip install -r requirements_deepseek.txt

# Ncloud Object Storage 지원을 위한 boto3 설치
pip install boto3

# 9. 환경 변수 설정
log_info "환경 변수 설정 중..."
if [ ! -f .env ]; then
    cp env.ubuntu.example .env
    
    # Ncloud 특화 설정 추가
    if [ ! -z "$PUBLIC_IP" ]; then
        echo "" >> .env
        echo "# Ncloud 특화 설정" >> .env
        echo "NCLOUD_PUBLIC_IP=$PUBLIC_IP" >> .env
        echo "NCLOUD_INSTANCE_ID=$INSTANCE_ID" >> .env
        echo "ALLOWED_ORIGINS=[\"http://localhost:3000\",\"http://$PUBLIC_IP\",\"https://$PUBLIC_IP\"]" >> .env
    fi
    
    log_warning ".env 파일이 생성되었습니다. API 키와 보안 설정을 수정하세요!"
fi

# 10. 필요한 디렉토리 생성
log_info "필요한 디렉토리 생성 중..."
mkdir -p uploads data/deepseek_learning exports logs backups

# 11. Ncloud 네트워크 최적화
log_ncloud "Ncloud 네트워크 최적화 설정 중..."
sudo tee -a /etc/sysctl.conf > /dev/null <<EOF

# Ncloud 네트워크 최적화
net.core.rmem_max = 134217728
net.core.wmem_max = 134217728
net.ipv4.tcp_rmem = 4096 87380 134217728
net.ipv4.tcp_wmem = 4096 65536 134217728
net.ipv4.tcp_congestion_control = bbr
net.core.default_qdisc = fq
EOF
sudo sysctl -p

# 12. 스토리지 최적화 (Ncloud SSD)
log_ncloud "Ncloud SSD 최적화 설정 중..."
if [ -b /dev/xvda ]; then
    echo 'deadline' | sudo tee /sys/block/xvda/queue/scheduler
    echo 'echo deadline > /sys/block/xvda/queue/scheduler' | sudo tee -a /etc/rc.local
fi

# 13. 메모리 최적화 (스왑 설정)
log_info "메모리 최적화 설정 중..."
if [ ! -f /swapfile ]; then
    sudo fallocate -l 2G /swapfile
    sudo chmod 600 /swapfile
    sudo mkswap /swapfile
    sudo swapon /swapfile
    echo '/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab
fi

# 14. 데이터베이스 마이그레이션
log_info "데이터베이스 마이그레이션 실행 중..."
source venv/bin/activate
alembic upgrade head || log_warning "마이그레이션 실패. 수동으로 확인하세요."

# 15. Qdrant 컨테이너 시작
log_info "Qdrant 벡터 데이터베이스 시작 중..."
docker run -d \
    --name campuson_qdrant \
    -p 6333:6333 \
    -p 6334:6334 \
    -v $(pwd)/qdrant_data:/qdrant/storage \
    --restart unless-stopped \
    --memory="1g" \
    --cpus="1.0" \
    qdrant/qdrant:latest || log_warning "Qdrant 컨테이너가 이미 실행 중입니다."

# 16. Redis 서비스 시작
log_info "Redis 서비스 시작 중..."
sudo systemctl start redis-server
sudo systemctl enable redis-server

# Redis 메모리 최적화
sudo tee -a /etc/redis/redis.conf > /dev/null <<EOF

# Ncloud 메모리 최적화
maxmemory 512mb
maxmemory-policy allkeys-lru
save 900 1
save 300 10
save 60 10000
EOF
sudo systemctl restart redis-server

# 17. Supervisor 설정 (프로세스 관리)
log_info "Supervisor 설정 중..."
sudo tee /etc/supervisor/conf.d/campuson.conf > /dev/null <<EOF
[program:campuson]
command=$PROJECT_DIR/venv/bin/uvicorn main:app --host 0.0.0.0 --port 8000 --workers 2
directory=$PROJECT_DIR
user=$USER
autostart=true
autorestart=true
redirect_stderr=true
stdout_logfile=$PROJECT_DIR/logs/campuson.log
environment=PATH="$PROJECT_DIR/venv/bin"
stopasgroup=true
killasgroup=true
EOF

# Supervisor 재시작
sudo systemctl restart supervisor
sudo systemctl enable supervisor

# 18. Nginx 설정 (Ncloud 최적화)
log_ncloud "Nginx 설정 중 (Ncloud 최적화)..."
sudo tee /etc/nginx/sites-available/campuson > /dev/null <<EOF
server {
    listen 80;
    server_name localhost ${PUBLIC_IP:-_};

    client_max_body_size 50M;
    client_body_timeout 60s;
    client_header_timeout 60s;
    
    # Ncloud 최적화 헤더
    add_header X-Served-By "Ncloud" always;
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-XSS-Protection "1; mode=block" always;
    add_header X-Content-Type-Options "nosniff" always;

    # 압축 설정
    gzip on;
    gzip_vary on;
    gzip_min_length 1024;
    gzip_types text/plain text/css application/json application/javascript text/xml application/xml;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade \$http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        proxy_cache_bypass \$http_upgrade;
        
        # Ncloud 최적화 타임아웃
        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;
        proxy_buffering on;
        proxy_buffer_size 4k;
        proxy_buffers 8 4k;
    }

    location /uploads/ {
        alias $PROJECT_DIR/uploads/;
        expires 1d;
        add_header Cache-Control "public, immutable";
        
        location ~* \.(php|jsp|asp|sh|py)$ {
            deny all;
        }
    }

    location /health {
        proxy_pass http://127.0.0.1:8000/health;
        access_log off;
    }

    location /robots.txt {
        return 200 "User-agent: *\nDisallow: /\n";
        add_header Content-Type text/plain;
    }
}
EOF

# Nginx 사이트 활성화
sudo ln -sf /etc/nginx/sites-available/campuson /etc/nginx/sites-enabled/
sudo rm -f /etc/nginx/sites-enabled/default

# Nginx 전역 최적화 설정
sudo tee -a /etc/nginx/nginx.conf > /dev/null <<EOF

# Ncloud 최적화 설정
worker_rlimit_nofile 65535;
events {
    worker_connections 4096;
    use epoll;
    multi_accept on;
}

http {
    sendfile on;
    tcp_nopush on;
    tcp_nodelay on;
    keepalive_timeout 65;
    keepalive_requests 1000;
    
    # 압축 설정
    gzip on;
    gzip_vary on;
    gzip_min_length 1024;
    gzip_types text/plain text/css application/json application/javascript text/xml application/xml;
}
EOF

# Nginx 설정 테스트 및 재시작
sudo nginx -t && sudo systemctl restart nginx
sudo systemctl enable nginx

# 19. 방화벽 설정 (Ncloud ACG와 연동)
log_ncloud "방화벽 설정 중..."
sudo ufw allow 22/tcp    # SSH
sudo ufw allow 80/tcp    # HTTP
sudo ufw allow 443/tcp   # HTTPS
sudo ufw allow 8000/tcp  # FastAPI (개발용)
sudo ufw --force enable

# 20. Ncloud 백업 스크립트 생성
log_ncloud "Ncloud 백업 스크립트 생성 중..."
sudo tee $PROJECT_DIR/backup_ncloud.sh > /dev/null <<'EOF'
#!/bin/bash
BACKUP_DIR="/opt/campuson/backups"
DATE=$(date +%Y%m%d_%H%M%S)
mkdir -p $BACKUP_DIR

# 데이터베이스 백업
pg_dump -h localhost -U admin -d kb_learning_db > $BACKUP_DIR/db_$DATE.sql

# 파일 백업
tar -czf $BACKUP_DIR/files_$DATE.tar.gz /opt/campuson/uploads

# 설정 파일 백업
tar -czf $BACKUP_DIR/config_$DATE.tar.gz /opt/campuson/.env /etc/nginx/sites-available/campuson

# 7일 이상 된 백업 파일 삭제
find $BACKUP_DIR -name "*.sql" -mtime +7 -delete
find $BACKUP_DIR -name "*.tar.gz" -mtime +7 -delete

echo "백업 완료: $DATE"
EOF

chmod +x $PROJECT_DIR/backup_ncloud.sh

# 크론탭 설정
(crontab -l 2>/dev/null; echo "0 2 * * * $PROJECT_DIR/backup_ncloud.sh") | crontab -

# 21. 서비스 상태 확인
log_info "서비스 상태 확인 중..."
sleep 10

# PostgreSQL 상태 확인
if sudo systemctl is-active --quiet postgresql; then
    log_success "PostgreSQL 서비스 실행 중"
else
    log_error "PostgreSQL 서비스 실행 실패"
fi

# Redis 상태 확인
if sudo systemctl is-active --quiet redis-server; then
    log_success "Redis 서비스 실행 중"
else
    log_error "Redis 서비스 실행 실패"
fi

# Qdrant 상태 확인
if docker ps | grep -q campuson_qdrant; then
    log_success "Qdrant 컨테이너 실행 중"
else
    log_error "Qdrant 컨테이너 실행 실패"
fi

# Nginx 상태 확인
if sudo systemctl is-active --quiet nginx; then
    log_success "Nginx 서비스 실행 중"
else
    log_error "Nginx 서비스 실행 실패"
fi

# Supervisor 상태 확인
if sudo systemctl is-active --quiet supervisor; then
    log_success "Supervisor 서비스 실행 중"
else
    log_error "Supervisor 서비스 실행 실패"
fi

# 22. API 헬스체크
log_info "API 헬스체크 중..."
sleep 15

if curl -f http://localhost:8000/health > /dev/null 2>&1; then
    log_success "API 서버 정상 작동 중"
else
    log_warning "API 서버 응답 없음. 로그를 확인하세요: tail -f $PROJECT_DIR/logs/campuson.log"
fi

# 23. Ncloud 특화 정보 출력
echo ""
log_ncloud "🎉 Ncloud CampusON 백엔드 배포 완료!"
echo ""
echo "📋 Ncloud 배포 정보:"
echo "  - 인스턴스 ID: ${INSTANCE_ID:-'N/A'}"
echo "  - 공인 IP: ${PUBLIC_IP:-'확인 필요'}"
echo "  - 프로젝트 경로: $PROJECT_DIR"
echo "  - API URL: http://${PUBLIC_IP:-localhost}:8000"
echo "  - API 문서: http://${PUBLIC_IP:-localhost}:8000/docs"
echo "  - 헬스체크: http://${PUBLIC_IP:-localhost}:8000/health"
echo ""
echo "📊 Ncloud 서비스 관리 명령어:"
echo "  - 로그 확인: tail -f $PROJECT_DIR/logs/campuson.log"
echo "  - 서비스 재시작: sudo supervisorctl restart campuson"
echo "  - 서비스 상태: sudo supervisorctl status campuson"
echo "  - Nginx 재시작: sudo systemctl restart nginx"
echo "  - 백업 실행: $PROJECT_DIR/backup_ncloud.sh"
echo ""
echo "☁️ Ncloud 특화 기능:"
echo "  - Cloud Insight 모니터링 연동 가능"
echo "  - Object Storage 연동 준비 완료"
echo "  - Global DNS 연동 가능"
echo "  - Load Balancer 연동 가능"
echo ""
echo "⚠️  중요 사항:"
echo "  1. .env 파일에서 API 키와 보안 설정을 수정하세요"
echo "  2. Ncloud ACG(방화벽) 설정을 확인하세요"
echo "  3. 도메인 사용 시 Global DNS 설정을 하세요"
echo "  4. SSL 인증서 설정을 고려하세요 (Let's Encrypt 권장)"
echo "  5. Cloud Insight로 모니터링 설정을 하세요"
echo ""
log_ncloud "Ncloud 배포 스크립트 실행 완료!"
echo ""
echo "🔗 유용한 Ncloud 링크:"
echo "  - Ncloud 콘솔: https://console.ncloud.com"
echo "  - 고객센터: 1588-3820"
echo "  - 개발자 가이드: https://guide.ncloud-docs.com" 