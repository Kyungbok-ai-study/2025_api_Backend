# 🌐 도메인 설정 가이드

## 📋 도메인 설정 단계별 가이드

### 1단계: DNS 설정 (도메인 제공업체)

#### 가비아 (gabia.com)
```
1. 가비아 로그인 → My가비아 → 도메인 관리
2. 해당 도메인 선택 → DNS 정보 → DNS 설정
3. 레코드 추가:
   - 타입: A
   - 호스트: @ (또는 공백)
   - 값: 서버 공인 IP 주소
   - TTL: 300

4. www 서브도메인 추가 (선택사항):
   - 타입: CNAME
   - 호스트: www
   - 값: your-domain.com
   - TTL: 300
```

#### Cloudflare
```
1. Cloudflare 대시보드 → DNS → Records
2. Add record:
   - Type: A
   - Name: @ (또는 도메인명)
   - IPv4 address: 서버 공인 IP
   - Proxy status: DNS only (회색 구름)

3. www 레코드 추가:
   - Type: CNAME
   - Name: www
   - Target: your-domain.com
```

#### 후이즈 (whois.co.kr)
```
1. 후이즈 로그인 → 도메인 관리 → DNS 관리
2. A 레코드 추가:
   - 호스트명: @
   - IP 주소: 서버 공인 IP
   - TTL: 300
```

### 2단계: 서버 IP 주소 확인

```bash
# 서버의 공인 IP 주소 확인
curl ifconfig.me
# 또는
curl ipinfo.io/ip
# 또는
wget -qO- http://ipecho.net/plain
```

### 3단계: Nginx 설정 수정

#### 방법 1: 설정 파일 직접 수정
```bash
# Nginx 설정 파일 수정
sudo nano /etc/nginx/sites-available/campuson

# server_name 부분을 실제 도메인으로 변경
server_name your-domain.com www.your-domain.com;
```

#### 방법 2: 예제 파일 사용
```bash
# 예제 파일 복사
sudo cp /opt/campuson/nginx.conf.example /etc/nginx/sites-available/campuson

# 도메인 설정 수정
sudo nano /etc/nginx/sites-available/campuson
# server_name 부분을 실제 도메인으로 변경

# 설정 활성화
sudo ln -sf /etc/nginx/sites-available/campuson /etc/nginx/sites-enabled/
sudo nginx -t && sudo systemctl reload nginx
```

### 4단계: 도메인 형식 예시

#### 일반적인 도메인 형식
```nginx
# 단일 도메인
server_name campuson.com;

# www 포함
server_name campuson.com www.campuson.com;

# 서브도메인
server_name api.campuson.com;

# 학교 도메인
server_name campuson.kyungbok.ac.kr;

# 여러 도메인
server_name campuson.com www.campuson.com api.campuson.com;

# IP 주소 직접 사용
server_name 123.456.789.012;

# 와일드카드 (모든 서브도메인)
server_name *.campuson.com;
```

#### 환경별 도메인 설정
```nginx
# 개발 환경
server_name dev.campuson.com;

# 스테이징 환경
server_name staging.campuson.com;

# 프로덕션 환경
server_name campuson.com www.campuson.com;
```

### 5단계: 환경 변수 업데이트

```bash
# .env 파일에서 CORS 설정 업데이트
nano /opt/campuson/.env

# ALLOWED_ORIGINS에 도메인 추가
ALLOWED_ORIGINS=["http://localhost:3000","https://campuson.com","https://www.campuson.com"]
```

### 6단계: SSL 인증서 설정 (HTTPS)

#### Let's Encrypt 사용 (무료)
```bash
# Certbot 설치
sudo apt install certbot python3-certbot-nginx

# SSL 인증서 발급 (도메인 변경 필요)
sudo certbot --nginx -d campuson.com -d www.campuson.com

# 자동 갱신 설정
sudo crontab -e
# 다음 줄 추가: 0 12 * * * /usr/bin/certbot renew --quiet
```

#### 상용 SSL 인증서 사용
```bash
# 인증서 파일 업로드 후
sudo nano /etc/nginx/sites-available/campuson

# SSL 설정 추가
server {
    listen 443 ssl http2;
    server_name campuson.com www.campuson.com;
    
    ssl_certificate /path/to/your/certificate.crt;
    ssl_certificate_key /path/to/your/private.key;
    
    # 나머지 설정...
}
```

### 7단계: 방화벽 설정 확인

```bash
# 필요한 포트 열기
sudo ufw allow 80/tcp   # HTTP
sudo ufw allow 443/tcp  # HTTPS
sudo ufw status
```

### 8단계: 설정 테스트

```bash
# Nginx 설정 테스트
sudo nginx -t

# Nginx 재시작
sudo systemctl reload nginx

# DNS 전파 확인
nslookup your-domain.com
dig your-domain.com

# 웹사이트 접속 테스트
curl -I http://your-domain.com/health
curl -I https://your-domain.com/health
```

## 🔧 실제 설정 예시

### 경복대학교 도메인 예시
```nginx
server {
    listen 80;
    listen [::]:80;
    server_name campuson.kyungbok.ac.kr api.kyungbok.ac.kr;
    
    # HTTP에서 HTTPS로 리다이렉트
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    listen [::]:443 ssl http2;
    server_name campuson.kyungbok.ac.kr api.kyungbok.ac.kr;
    
    ssl_certificate /etc/letsencrypt/live/campuson.kyungbok.ac.kr/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/campuson.kyungbok.ac.kr/privkey.pem;
    
    # 나머지 설정...
}
```

### 개인 도메인 예시
```nginx
server {
    listen 80;
    listen [::]:80;
    server_name campuson.kr www.campuson.kr api.campuson.kr;
    
    # 나머지 설정...
}
```

## 🚨 문제 해결

### DNS 전파 확인
```bash
# 전 세계 DNS 서버에서 확인
dig @8.8.8.8 your-domain.com
dig @1.1.1.1 your-domain.com
dig @208.67.222.222 your-domain.com

# 온라인 도구 사용
# https://www.whatsmydns.net/
# https://dnschecker.org/
```

### 일반적인 문제들

1. **DNS 전파 지연**
   - 보통 5분~24시간 소요
   - TTL 값을 낮게 설정 (300초)

2. **Nginx 설정 오류**
   ```bash
   sudo nginx -t  # 설정 파일 문법 검사
   sudo systemctl status nginx  # 서비스 상태 확인
   ```

3. **방화벽 차단**
   ```bash
   sudo ufw status
   sudo ufw allow 80/tcp
   sudo ufw allow 443/tcp
   ```

4. **SSL 인증서 문제**
   ```bash
   sudo certbot certificates  # 인증서 목록 확인
   sudo certbot renew --dry-run  # 갱신 테스트
   ```

## 📞 도메인별 설정 명령어

### 도메인이 `campuson.com`인 경우
```bash
# DNS 설정 후
sudo nano /etc/nginx/sites-available/campuson
# server_name을 다음과 같이 변경:
# server_name campuson.com www.campuson.com;

sudo nginx -t && sudo systemctl reload nginx
sudo certbot --nginx -d campuson.com -d www.campuson.com
```

### 도메인이 `api.kyungbok.ac.kr`인 경우
```bash
# DNS 설정 후
sudo nano /etc/nginx/sites-available/campuson
# server_name을 다음과 같이 변경:
# server_name api.kyungbok.ac.kr;

sudo nginx -t && sudo systemctl reload nginx
sudo certbot --nginx -d api.kyungbok.ac.kr
```

---

**💡 팁**: 도메인 설정 후 반드시 `https://your-domain.com/health`로 접속하여 API가 정상 작동하는지 확인하세요! 