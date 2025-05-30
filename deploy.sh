#!/bin/bash

# CampusON API 자동 배포 스크립트
# 사용법: ./deploy.sh [production|staging]

set -e  # 오류 시 스크립트 중단

# 색깔 코드
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 환경 설정
ENVIRONMENT=${1:-production}
PROJECT_NAME="campuson"
DOMAIN="kbu-ai-team.kro.kr"

echo -e "${BLUE}🚀 CampusON API 배포 시작...${NC}"
echo -e "환경: ${YELLOW}$ENVIRONMENT${NC}"
echo -e "도메인: ${YELLOW}$DOMAIN${NC}"

# 현재 사용자가 sudo 권한이 있는지 확인
if ! sudo -n true 2>/dev/null; then
    echo -e "${RED}❌ sudo 권한이 필요합니다.${NC}"
    exit 1
fi

# 1. 시스템 업데이트
echo -e "\n${BLUE}📦 시스템 패키지 업데이트...${NC}"
sudo apt update && sudo apt upgrade -y

# 2. 필수 패키지 설치
echo -e "\n${BLUE}🔧 필수 패키지 설치...${NC}"
sudo apt install -y python3.9 python3.9-venv python3-pip \
    postgresql postgresql-contrib nginx git curl wget ufw \
    certbot python3-certbot-nginx

# 3. 프로젝트 디렉토리 설정
echo -e "\n${BLUE}📁 프로젝트 디렉토리 설정...${NC}"
PROJECT_DIR="/var/www/$PROJECT_NAME"
sudo mkdir -p $PROJECT_DIR
sudo chown $USER:$USER $PROJECT_DIR

# 4. 코드 복사 (현재 디렉토리의 모든 파일)
echo -e "\n${BLUE}📋 코드 복사...${NC}"
cp -r . $PROJECT_DIR/
cd $PROJECT_DIR

# 5. Python 가상환경 설정
echo -e "\n${BLUE}🐍 Python 가상환경 설정...${NC}"
python3.9 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt

# 6. 환경 변수 설정
echo -e "\n${BLUE}⚙️ 환경 변수 설정...${NC}"

# 보안 키 생성
SECRET_KEY=$(python3 -c "import secrets; print(secrets.token_urlsafe(32))")
JWT_SECRET_KEY=$(python3 -c "import secrets; print(secrets.token_urlsafe(32))")
DB_PASSWORD=$(python3 -c "import secrets; print(secrets.token_urlsafe(16))")

cat > .env.prod << EOF
# Database
DATABASE_URL=postgresql://campuson_user:$DB_PASSWORD@localhost/campuson_prod

# Security
SECRET_KEY=$SECRET_KEY
JWT_SECRET_KEY=$JWT_SECRET_KEY
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30

# Environment
ENVIRONMENT=$ENVIRONMENT
DEBUG=False

# CORS
ALLOWED_ORIGINS=["https://$DOMAIN", "https://www.$DOMAIN"]

# AI Settings
AI_MODEL_NAME=exaone-3.0
AI_MAX_TOKENS=2048
AI_TEMPERATURE=0.7
EOF

echo -e "${GREEN}✅ 환경 변수 파일 생성 완료${NC}"

# 7. PostgreSQL 설정
echo -e "\n${BLUE}🗄️ PostgreSQL 설정...${NC}"
sudo systemctl start postgresql
sudo systemctl enable postgresql

# 데이터베이스 및 사용자 생성
sudo -u postgres psql << EOF
DROP DATABASE IF EXISTS campuson_prod;
DROP USER IF EXISTS campuson_user;
CREATE DATABASE campuson_prod;
CREATE USER campuson_user WITH PASSWORD '$DB_PASSWORD';
GRANT ALL PRIVILEGES ON DATABASE campuson_prod TO campuson_user;
ALTER USER campuson_user CREATEDB;
\q
EOF

echo -e "${GREEN}✅ PostgreSQL 설정 완료${NC}"

# 8. 데이터베이스 마이그레이션
echo -e "\n${BLUE}🔄 데이터베이스 마이그레이션...${NC}"
source venv/bin/activate
export $(cat .env.prod | xargs)

# Alembic 초기화 (필요한 경우)
if [ ! -d "alembic" ]; then
    alembic init alembic
fi

# 마이그레이션 실행
alembic upgrade head

# 샘플 데이터 추가
python add_sample_questions.py

echo -e "${GREEN}✅ 데이터베이스 마이그레이션 완료${NC}"

# 9. systemd 서비스 설정
echo -e "\n${BLUE}🔧 systemd 서비스 설정...${NC}"
sudo tee /etc/systemd/system/$PROJECT_NAME.service > /dev/null << EOF
[Unit]
Description=CampusON FastAPI application
After=network.target

[Service]
Type=notify
User=www-data
Group=www-data
RuntimeDirectory=$PROJECT_NAME
WorkingDirectory=$PROJECT_DIR
Environment=PATH=$PROJECT_DIR/venv/bin
EnvironmentFile=$PROJECT_DIR/.env.prod
ExecStart=$PROJECT_DIR/venv/bin/gunicorn -c gunicorn.conf.py app.main:app
ExecReload=/bin/kill -s HUP \$MAINPID
KillMode=mixed
TimeoutStopSec=5
PrivateTmp=true

[Install]
WantedBy=multi-user.target
EOF

# 서비스 권한 설정
sudo chown -R www-data:www-data $PROJECT_DIR
sudo systemctl daemon-reload
sudo systemctl enable $PROJECT_NAME

echo -e "${GREEN}✅ systemd 서비스 설정 완료${NC}"

# 10. Nginx 설정
echo -e "\n${BLUE}🌐 Nginx 설정...${NC}"
sudo tee /etc/nginx/sites-available/$PROJECT_NAME > /dev/null << 'EOF'
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
    
    # Health check
    location /health {
        proxy_pass http://127.0.0.1:8000/health;
        access_log off;
    }
}
EOF

# Nginx 사이트 활성화
sudo ln -sf /etc/nginx/sites-available/$PROJECT_NAME /etc/nginx/sites-enabled/
sudo rm -f /etc/nginx/sites-enabled/default

# Nginx 설정 테스트
sudo nginx -t
sudo systemctl reload nginx

echo -e "${GREEN}✅ Nginx 설정 완료${NC}"

# 11. 방화벽 설정
echo -e "\n${BLUE}🔒 방화벽 설정...${NC}"
sudo ufw --force enable
sudo ufw allow ssh
sudo ufw allow 'Nginx Full'

echo -e "${GREEN}✅ 방화벽 설정 완료${NC}"

# 12. 서비스 시작
echo -e "\n${BLUE}🚀 서비스 시작...${NC}"
sudo systemctl start $PROJECT_NAME
sudo systemctl start nginx

# 13. SSL 인증서 설정 (선택사항)
echo -e "\n${YELLOW}🔐 SSL 인증서 설정을 진행하시겠습니까? (y/N):${NC}"
read -r ssl_setup

if [[ $ssl_setup =~ ^[Yy]$ ]]; then
    echo -e "\n${BLUE}🔐 SSL 인증서 설정...${NC}"
    sudo certbot --nginx -d $DOMAIN -d www.$DOMAIN --non-interactive --agree-tos --email admin@$DOMAIN
    echo -e "${GREEN}✅ SSL 인증서 설정 완료${NC}"
fi

# 14. 로그 디렉토리 생성
echo -e "\n${BLUE}📝 로그 디렉토리 설정...${NC}"
sudo mkdir -p $PROJECT_DIR/logs
sudo chown -R www-data:www-data $PROJECT_DIR/logs

# 15. 백업 스크립트 설정
echo -e "\n${BLUE}💾 백업 스크립트 설정...${NC}"
sudo tee /usr/local/bin/backup_$PROJECT_NAME.sh > /dev/null << EOF
#!/bin/bash
BACKUP_DIR="/var/backups/$PROJECT_NAME"
DATE=\$(date +"%Y%m%d_%H%M%S")
mkdir -p \$BACKUP_DIR

# 데이터베이스 백업
PGPASSWORD='$DB_PASSWORD' pg_dump -h localhost -U campuson_user -d campuson_prod > \$BACKUP_DIR/db_backup_\$DATE.sql

# 파일 백업
tar -czf \$BACKUP_DIR/files_backup_\$DATE.tar.gz $PROJECT_DIR

# 7일 이상된 백업 삭제
find \$BACKUP_DIR -name "*.sql" -mtime +7 -delete
find \$BACKUP_DIR -name "*.tar.gz" -mtime +7 -delete
EOF

sudo chmod +x /usr/local/bin/backup_$PROJECT_NAME.sh

# 일일 백업 크론 설정
(sudo crontab -l 2>/dev/null; echo "0 2 * * * /usr/local/bin/backup_$PROJECT_NAME.sh") | sudo crontab -

echo -e "${GREEN}✅ 백업 설정 완료${NC}"

# 16. 최종 상태 확인
echo -e "\n${BLUE}🔍 서비스 상태 확인...${NC}"

sleep 5  # 서비스 시작 대기

if sudo systemctl is-active --quiet $PROJECT_NAME; then
    echo -e "${GREEN}✅ $PROJECT_NAME 서비스 정상 실행 중${NC}"
else
    echo -e "${RED}❌ $PROJECT_NAME 서비스 실행 실패${NC}"
    sudo systemctl status $PROJECT_NAME
fi

if sudo systemctl is-active --quiet nginx; then
    echo -e "${GREEN}✅ Nginx 서비스 정상 실행 중${NC}"
else
    echo -e "${RED}❌ Nginx 서비스 실행 실패${NC}"
    sudo systemctl status nginx
fi

if sudo systemctl is-active --quiet postgresql; then
    echo -e "${GREEN}✅ PostgreSQL 서비스 정상 실행 중${NC}"
else
    echo -e "${RED}❌ PostgreSQL 서비스 실행 실패${NC}"
    sudo systemctl status postgresql
fi

# 17. API 테스트
echo -e "\n${BLUE}🧪 API 테스트...${NC}"
sleep 2

if curl -f http://localhost:8000/health >/dev/null 2>&1; then
    echo -e "${GREEN}✅ API Health Check 성공${NC}"
else
    echo -e "${RED}❌ API Health Check 실패${NC}"
fi

if curl -f http://localhost:8000/ >/dev/null 2>&1; then
    echo -e "${GREEN}✅ API Root 엔드포인트 성공${NC}"
else
    echo -e "${RED}❌ API Root 엔드포인트 실패${NC}"
fi

# 18. 배포 완료 메시지
echo -e "\n${GREEN}🎉 배포 완료!${NC}"
echo -e "\n${BLUE}📋 배포 정보:${NC}"
echo -e "• 프로젝트: $PROJECT_NAME"
echo -e "• 환경: $ENVIRONMENT"
echo -e "• 도메인: $DOMAIN"
echo -e "• 프로젝트 경로: $PROJECT_DIR"
echo -e "• 로그 경로: $PROJECT_DIR/logs"
echo -e "• 백업 경로: /var/backups/$PROJECT_NAME"

echo -e "\n${BLUE}🔗 접속 URL:${NC}"
echo -e "• HTTP: http://$DOMAIN"
echo -e "• API 문서: http://$DOMAIN/docs"
echo -e "• Health Check: http://$DOMAIN/health"

if [[ $ssl_setup =~ ^[Yy]$ ]]; then
    echo -e "• HTTPS: https://$DOMAIN"
    echo -e "• API 문서 (HTTPS): https://$DOMAIN/docs"
fi

echo -e "\n${BLUE}🛠️ 유용한 명령어:${NC}"
echo -e "• 서비스 상태 확인: sudo systemctl status $PROJECT_NAME"
echo -e "• 서비스 재시작: sudo systemctl restart $PROJECT_NAME"
echo -e "• 로그 확인: sudo journalctl -u $PROJECT_NAME -f"
echo -e "• Nginx 로그: sudo tail -f /var/log/nginx/access.log"

echo -e "\n${YELLOW}⚠️ 다음 단계:${NC}"
echo -e "1. DNS 설정에서 A 레코드를 서버 IP로 설정"
echo -e "2. 도메인 전파 완료 후 SSL 인증서 재설정 (필요시)"
echo -e "3. API 엔드포인트 테스트"
echo -e "4. 모니터링 설정 검토"

echo -e "\n${GREEN}✨ 배포가 성공적으로 완료되었습니다!${NC}" 