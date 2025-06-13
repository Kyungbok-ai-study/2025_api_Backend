#!/bin/bash

# 우분투 22.04.1 LTS 환경 CampusON 백엔드 배포 스크립트
# 사용법: chmod +x deploy_ubuntu.sh && ./deploy_ubuntu.sh

set -e  # 오류 발생 시 스크립트 중단

echo "🚀 CampusON 백엔드 우분투 배포 시작..."

# 색상 정의
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
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

# 1. 시스템 업데이트
log_info "시스템 패키지 업데이트 중..."
sudo apt update && sudo apt upgrade -y

# 2. 필수 시스템 패키지 설치
log_info "필수 시스템 패키지 설치 중..."
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

# 5. Qdrant 설치 (Docker 사용)
log_info "Docker 설치 중..."
if ! command -v docker &> /dev/null; then
    curl -fsSL https://get.docker.com -o get-docker.sh
    sudo sh get-docker.sh
    sudo usermod -aG docker $USER
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

# 9. 환경 변수 설정
log_info "환경 변수 설정 중..."
if [ ! -f .env ]; then
    cp env.ubuntu.example .env
    log_warning ".env 파일이 생성되었습니다. API 키와 보안 설정을 수정하세요!"
fi

# 10. 필요한 디렉토리 생성
log_info "필요한 디렉토리 생성 중..."
mkdir -p uploads data/deepseek_learning exports logs

# 11. 데이터베이스 마이그레이션
log_info "데이터베이스 마이그레이션 실행 중..."
source venv/bin/activate
alembic upgrade head || log_warning "마이그레이션 실패. 수동으로 확인하세요."

# 12. Qdrant 컨테이너 시작
log_info "Qdrant 벡터 데이터베이스 시작 중..."
docker run -d \
    --name campuson_qdrant \
    -p 6333:6333 \
    -p 6334:6334 \
    -v $(pwd)/qdrant_data:/qdrant/storage \
    --restart unless-stopped \
    qdrant/qdrant:latest || log_warning "Qdrant 컨테이너가 이미 실행 중입니다."

# 13. Redis 서비스 시작
log_info "Redis 서비스 시작 중..."
sudo systemctl start redis-server
sudo systemctl enable redis-server

# 14. Supervisor 설정 (프로세스 관리)
log_info "Supervisor 설정 중..."
sudo tee /etc/supervisor/conf.d/campuson.conf > /dev/null <<EOF
[program:campuson]
command=$PROJECT_DIR/venv/bin/uvicorn main:app --host 0.0.0.0 --port 8000 --workers 4
directory=$PROJECT_DIR
user=$USER
autostart=true
autorestart=true
redirect_stderr=true
stdout_logfile=$PROJECT_DIR/logs/campuson.log
environment=PATH="$PROJECT_DIR/venv/bin"
EOF

# Supervisor 재시작
sudo systemctl restart supervisor
sudo systemctl enable supervisor

# 15. Nginx 설정 (리버스 프록시)
log_info "Nginx 설정 중..."
sudo tee /etc/nginx/sites-available/campuson > /dev/null <<EOF
server {
    listen 80;
    server_name localhost;

    client_max_body_size 50M;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;
    }

    location /uploads/ {
        alias $PROJECT_DIR/uploads/;
        expires 1d;
        add_header Cache-Control "public, immutable";
    }

    location /health {
        proxy_pass http://127.0.0.1:8000/health;
        access_log off;
    }
}
EOF

# Nginx 사이트 활성화
sudo ln -sf /etc/nginx/sites-available/campuson /etc/nginx/sites-enabled/
sudo rm -f /etc/nginx/sites-enabled/default

# Nginx 설정 테스트 및 재시작
sudo nginx -t && sudo systemctl restart nginx
sudo systemctl enable nginx

# 16. 방화벽 설정
log_info "방화벽 설정 중..."
sudo ufw allow 22/tcp    # SSH
sudo ufw allow 80/tcp    # HTTP
sudo ufw allow 443/tcp   # HTTPS
sudo ufw allow 8000/tcp  # FastAPI (개발용)
sudo ufw --force enable

# 17. 서비스 상태 확인
log_info "서비스 상태 확인 중..."
sleep 5

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

# 18. 헬스체크
log_info "API 헬스체크 중..."
sleep 10

if curl -f http://localhost:8000/health > /dev/null 2>&1; then
    log_success "API 서버 정상 작동 중"
else
    log_warning "API 서버 응답 없음. 로그를 확인하세요: tail -f $PROJECT_DIR/logs/campuson.log"
fi

# 19. 배포 완료 메시지
echo ""
log_success "🎉 CampusON 백엔드 배포 완료!"
echo ""
echo "📋 배포 정보:"
echo "  - 프로젝트 경로: $PROJECT_DIR"
echo "  - API URL: http://localhost:8000"
echo "  - API 문서: http://localhost:8000/docs"
echo "  - 헬스체크: http://localhost:8000/health"
echo ""
echo "📊 서비스 관리 명령어:"
echo "  - 로그 확인: tail -f $PROJECT_DIR/logs/campuson.log"
echo "  - 서비스 재시작: sudo supervisorctl restart campuson"
echo "  - 서비스 상태: sudo supervisorctl status campuson"
echo "  - Nginx 재시작: sudo systemctl restart nginx"
echo ""
echo "⚠️  중요 사항:"
echo "  1. .env 파일에서 API 키와 보안 설정을 수정하세요"
echo "  2. 도메인 사용 시 Nginx 설정을 수정하세요"
echo "  3. SSL 인증서 설정을 고려하세요 (Let's Encrypt 권장)"
echo "  4. 정기적인 백업 설정을 구성하세요"
echo ""
log_success "배포 스크립트 실행 완료!" 