# ☁️ 네이버 클라우드 플랫폼(Ncloud) 배포 가이드

## 📋 개요

네이버 클라우드 플랫폼의 우분투 22.04 서버에 CampusON 백엔드를 배포하는 완전 가이드입니다.

## 🚀 Ncloud 서버 생성

### 1단계: 서버 인스턴스 생성

#### 권장 사양
```
- OS: Ubuntu Server 22.04 LTS
- CPU: 2vCPU (Standard-2 이상)
- RAM: 4GB 이상 (8GB 권장)
- Storage: 50GB SSD
- 네트워크: 공인 IP 할당
```

#### Ncloud 콘솔에서 설정
```
1. Ncloud 콘솔 로그인 (https://console.ncloud.com)
2. Server → Server 생성
3. 설정:
   - 서버 이미지: Ubuntu Server 22.04 LTS
   - 서버 타입: Standard (s-2vcpu-4gb 이상)
   - 스토리지: SSD 50GB
   - 네트워크: VPC 또는 Classic
   - 공인 IP: 신규 생성
   - 포트 포워딩: 22(SSH), 80(HTTP), 443(HTTPS), 8000(API)
```

### 2단계: 방화벽(ACG) 설정

```
인바운드 규칙 추가:
- SSH: 22/tcp (0.0.0.0/0 또는 특정 IP)
- HTTP: 80/tcp (0.0.0.0/0)
- HTTPS: 443/tcp (0.0.0.0/0)
- API: 8000/tcp (0.0.0.0/0) - 개발용
- PostgreSQL: 5432/tcp (서버 내부만)
- Redis: 6379/tcp (서버 내부만)
- Qdrant: 6333/tcp (서버 내부만)
```

### 3단계: SSH 접속

```bash
# Ncloud에서 제공하는 SSH 키 사용
ssh -i your-private-key.pem root@your-server-ip

# 또는 비밀번호 방식 (설정한 경우)
ssh root@your-server-ip
```

## 🔧 서버 초기 설정

### 1. 사용자 계정 생성 (보안)

```bash
# 새 사용자 생성
adduser ubuntu
usermod -aG sudo ubuntu

# SSH 키 복사 (키 방식 사용 시)
mkdir -p /home/ubuntu/.ssh
cp /root/.ssh/authorized_keys /home/ubuntu/.ssh/
chown -R ubuntu:ubuntu /home/ubuntu/.ssh
chmod 700 /home/ubuntu/.ssh
chmod 600 /home/ubuntu/.ssh/authorized_keys

# ubuntu 사용자로 전환
su - ubuntu
```

### 2. 시스템 업데이트

```bash
sudo apt update && sudo apt upgrade -y
sudo reboot  # 재부팅 후 다시 접속
```

## 🚀 CampusON 백엔드 배포

### 방법 1: 자동 배포 스크립트 (권장)

```bash
# 프로젝트 다운로드
git clone https://github.com/your-repo/campuson-backend.git
cd campuson-backend

# 또는 파일 업로드 (scp 사용)
scp -i your-key.pem -r ./2025_api_Backend ubuntu@your-server-ip:~/

# 배포 스크립트 실행
chmod +x deploy_ubuntu.sh
./deploy_ubuntu.sh
```

### 방법 2: Docker Compose 사용

```bash
# Docker 설치 (스크립트에 포함되어 있음)
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
sudo usermod -aG docker ubuntu

# 로그아웃 후 다시 로그인
exit
ssh ubuntu@your-server-ip

# 프로젝트 디렉토리로 이동
cd campuson-backend

# 환경 변수 설정
cp env.ubuntu.example .env
nano .env  # API 키 등 설정

# Docker Compose로 배포
docker-compose up -d
```

## 🌐 Ncloud 도메인 연결

### 1. Ncloud DNS 사용

```bash
# Ncloud 콘솔에서
1. Global DNS → DNS Zone 생성
2. 도메인 추가 (예: campuson.com)
3. 레코드 설정:
   - A 레코드: @ → 서버 공인 IP
   - CNAME 레코드: www → campuson.com
```

### 2. 외부 도메인 사용

```bash
# 도메인 제공업체에서 네임서버 변경
네임서버 1: ns1-1.ns-ncloud.com
네임서버 2: ns1-2.ns-ncloud.com

# 또는 A 레코드 직접 설정
A 레코드: @ → Ncloud 서버 공인 IP
```

### 3. Nginx 도메인 설정

```bash
# 도메인 설정
sudo nano /etc/nginx/sites-available/campuson

# server_name 변경
server_name your-domain.com www.your-domain.com;

# 설정 적용
sudo nginx -t && sudo systemctl reload nginx
```

## 🔒 SSL 인증서 설정

### Let's Encrypt 무료 SSL

```bash
# Certbot 설치
sudo apt install certbot python3-certbot-nginx

# SSL 인증서 발급
sudo certbot --nginx -d your-domain.com -d www.your-domain.com

# 자동 갱신 설정
sudo crontab -e
# 추가: 0 12 * * * /usr/bin/certbot renew --quiet
```

## 📊 Ncloud 모니터링 연동

### 1. Cloud Insight 연동

```bash
# Ncloud Cloud Insight 에이전트 설치
wget https://cloud-insight.ncloud.com/agent/linux/cloud-insight-agent-latest.tar.gz
tar -xzf cloud-insight-agent-latest.tar.gz
sudo ./install.sh YOUR_LICENSE_KEY
```

### 2. 로그 모니터링 설정

```bash
# 로그 파일 위치 설정
sudo nano /etc/cloud-insight-agent/agent.conf

# 모니터링할 로그 추가
[log]
/opt/campuson/logs/campuson.log
/var/log/nginx/access.log
/var/log/nginx/error.log
```

## 🔧 Ncloud 특화 최적화

### 1. 네트워크 최적화

```bash
# Ncloud 내부 네트워크 최적화
echo 'net.core.rmem_max = 134217728' | sudo tee -a /etc/sysctl.conf
echo 'net.core.wmem_max = 134217728' | sudo tee -a /etc/sysctl.conf
echo 'net.ipv4.tcp_rmem = 4096 87380 134217728' | sudo tee -a /etc/sysctl.conf
echo 'net.ipv4.tcp_wmem = 4096 65536 134217728' | sudo tee -a /etc/sysctl.conf
sudo sysctl -p
```

### 2. 스토리지 최적화

```bash
# SSD 최적화 설정
echo 'deadline' | sudo tee /sys/block/xvda/queue/scheduler
echo 'echo deadline > /sys/block/xvda/queue/scheduler' | sudo tee -a /etc/rc.local
```

### 3. 메모리 최적화

```bash
# 스왑 설정 (4GB RAM 기준)
sudo fallocate -l 2G /swapfile
sudo chmod 600 /swapfile
sudo mkswap /swapfile
sudo swapon /swapfile
echo '/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab
```

## 🔄 Ncloud Object Storage 연동 (선택사항)

### 파일 업로드를 Object Storage로 이동

```python
# requirements.txt에 추가
boto3==1.34.0

# .env 파일에 추가
NCLOUD_ACCESS_KEY=your-access-key
NCLOUD_SECRET_KEY=your-secret-key
NCLOUD_REGION=kr-standard
NCLOUD_BUCKET_NAME=campuson-uploads
```

```python
# app/services/ncloud_storage.py (신규 파일)
import boto3
from botocore.config import Config

class NcloudObjectStorage:
    def __init__(self):
        self.client = boto3.client(
            's3',
            endpoint_url='https://kr.object.ncloudstorage.com',
            aws_access_key_id=settings.NCLOUD_ACCESS_KEY,
            aws_secret_access_key=settings.NCLOUD_SECRET_KEY,
            config=Config(region_name='kr-standard')
        )
        self.bucket_name = settings.NCLOUD_BUCKET_NAME
    
    def upload_file(self, file_path, object_name):
        try:
            self.client.upload_file(file_path, self.bucket_name, object_name)
            return f"https://kr.object.ncloudstorage.com/{self.bucket_name}/{object_name}"
        except Exception as e:
            logger.error(f"Object Storage 업로드 실패: {e}")
            return None
```

## 🚨 Ncloud 특화 문제 해결

### 1. 포트 접속 문제

```bash
# ACG(방화벽) 확인
# Ncloud 콘솔 → Server → ACG 설정 확인

# 서버 내부 방화벽 확인
sudo ufw status
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw allow 8000/tcp
```

### 2. 공인 IP 접속 문제

```bash
# 공인 IP 확인
curl ifconfig.me

# 포트 포워딩 확인 (Classic 환경)
# Ncloud 콘솔 → Server → 포트 포워딩 설정 확인
```

### 3. 성능 이슈

```bash
# CPU/메모리 사용률 확인
htop
free -h
df -h

# 네트워크 상태 확인
netstat -tulpn
ss -tulpn
```

## 📈 Ncloud 비용 최적화

### 1. 서버 사양 조정

```bash
# 사용량 모니터링 후 적절한 사양으로 조정
# 개발 환경: s-1vcpu-2gb (월 약 15,000원)
# 운영 환경: s-2vcpu-4gb (월 약 30,000원)
# 고성능: s-4vcpu-8gb (월 약 60,000원)
```

### 2. 스토리지 최적화

```bash
# 불필요한 파일 정리
sudo apt autoremove
sudo apt autoclean
docker system prune -f

# 로그 로테이션 설정
sudo nano /etc/logrotate.d/campuson
```

### 3. 트래픽 최적화

```bash
# Nginx 압축 설정
sudo nano /etc/nginx/nginx.conf

# gzip 압축 활성화
gzip on;
gzip_vary on;
gzip_min_length 1024;
gzip_types text/plain text/css application/json application/javascript text/xml application/xml;
```

## 🔄 백업 및 복구

### 1. 자동 백업 스크립트

```bash
# 백업 스크립트 생성
sudo nano /opt/campuson/backup.sh
```

```bash
#!/bin/bash
BACKUP_DIR="/opt/campuson/backups"
DATE=$(date +%Y%m%d_%H%M%S)

# 데이터베이스 백업
pg_dump -h localhost -U admin -d kb_learning_db > $BACKUP_DIR/db_$DATE.sql

# 파일 백업
tar -czf $BACKUP_DIR/files_$DATE.tar.gz /opt/campuson/uploads

# Ncloud Object Storage에 업로드 (선택사항)
# aws s3 cp $BACKUP_DIR/db_$DATE.sql s3://your-backup-bucket/ --endpoint-url=https://kr.object.ncloudstorage.com
```

```bash
# 크론탭 설정
sudo crontab -e
# 매일 새벽 2시 백업: 0 2 * * * /opt/campuson/backup.sh
```

### 2. 서버 이미지 백업

```bash
# Ncloud 콘솔에서
1. Server → 서버 선택
2. 서버 이미지 생성
3. 정기적으로 스냅샷 생성 (주 1회 권장)
```

## 📞 Ncloud 지원 및 문의

### 기술 지원
- Ncloud 고객센터: 1588-3820
- 온라인 문의: https://www.ncloud.com/support/question
- 개발자 포럼: https://medium.com/naver-cloud-platform

### 유용한 링크
- Ncloud 콘솔: https://console.ncloud.com
- API 문서: https://ncloud.apigw.ntruss.com/docs/
- 가격 계산기: https://www.ncloud.com/product/estimate

---

## 🎯 Ncloud 배포 체크리스트

배포 완료 후 확인사항:

- [ ] 서버 인스턴스 정상 생성
- [ ] ACG(방화벽) 규칙 설정
- [ ] 공인 IP 할당 및 접속 확인
- [ ] CampusON 백엔드 배포 완료
- [ ] 도메인 연결 (선택사항)
- [ ] SSL 인증서 설정
- [ ] API 정상 작동 확인 (https://your-domain.com/health)
- [ ] 모니터링 설정
- [ ] 백업 시스템 구성
- [ ] 비용 최적화 설정

**🚀 Ncloud는 한국 서비스라서 속도가 빠르고 지원이 좋습니다!** 