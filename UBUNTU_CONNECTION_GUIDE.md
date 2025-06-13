# 🖥️ 우분투 서버 ↔ 우분투 데스크탑 연결 가이드

## 📋 개요

우분투 서버(백엔드)와 우분투 데스크탑(프론트엔드/개발환경) 간의 다양한 연결 방법을 설명합니다.

## 🔗 연결 방법 종류

### 1. SSH 연결 (기본)
### 2. 원격 데스크탑 연결 (GUI)
### 3. 파일 전송 (SFTP/SCP)
### 4. 네트워크 공유 (NFS/Samba)
### 5. 개발 환경 연결 (VS Code Remote)

---

## 🔐 1. SSH 연결 (명령줄 접속)

### 서버 측 설정

```bash
# SSH 서버 설치 및 활성화
sudo apt update
sudo apt install openssh-server -y

# SSH 서비스 시작
sudo systemctl start ssh
sudo systemctl enable ssh

# SSH 상태 확인
sudo systemctl status ssh

# 방화벽 설정
sudo ufw allow ssh
sudo ufw allow 22/tcp
```

### 데스크탑 측 연결

```bash
# 기본 SSH 연결
ssh username@server-ip

# 예시
ssh ubuntu@192.168.1.100
ssh root@123.456.789.012

# 포트 지정 연결
ssh -p 2222 username@server-ip

# SSH 키 사용 연결
ssh -i ~/.ssh/private_key username@server-ip
```

### SSH 키 설정 (보안 강화)

```bash
# 데스크탑에서 SSH 키 생성
ssh-keygen -t rsa -b 4096 -C "your-email@example.com"

# 공개키를 서버로 복사
ssh-copy-id username@server-ip

# 또는 수동으로 복사
cat ~/.ssh/id_rsa.pub | ssh username@server-ip "mkdir -p ~/.ssh && cat >> ~/.ssh/authorized_keys"

# 서버에서 권한 설정
chmod 700 ~/.ssh
chmod 600 ~/.ssh/authorized_keys
```

---

## 🖥️ 2. 원격 데스크탑 연결 (GUI 접속)

### 방법 A: XRDP 사용

#### 서버 측 설정

```bash
# 데스크탑 환경 설치 (경량화)
sudo apt install ubuntu-desktop-minimal -y

# 또는 XFCE (더 가벼움)
sudo apt install xfce4 xfce4-goodies -y

# XRDP 설치
sudo apt install xrdp -y

# XRDP 서비스 시작
sudo systemctl start xrdp
sudo systemctl enable xrdp

# 방화벽 설정
sudo ufw allow 3389/tcp

# XRDP 사용자 추가
sudo adduser xrdp ssl-cert

# 세션 설정
echo "xfce4-session" > ~/.xsession
```

#### 데스크탑 측 연결

```bash
# Remmina 설치 (원격 데스크탑 클라이언트)
sudo apt install remmina remmina-plugin-rdp -y

# 연결 정보
# 프로토콜: RDP
# 서버: server-ip:3389
# 사용자명: username
# 비밀번호: password
```

### 방법 B: VNC 사용

#### 서버 측 설정

```bash
# VNC 서버 설치
sudo apt install tightvncserver -y

# VNC 서버 시작 (처음 실행 시 비밀번호 설정)
vncserver :1

# VNC 서버 중지
vncserver -kill :1

# VNC 설정 파일 편집
nano ~/.vnc/xstartup
```

```bash
# ~/.vnc/xstartup 내용
#!/bin/bash
xrdb $HOME/.Xresources
startxfce4 &
```

```bash
# 실행 권한 부여
chmod +x ~/.vnc/xstartup

# VNC 서버 재시작
vncserver :1

# 방화벽 설정
sudo ufw allow 5901/tcp
```

#### 데스크탑 측 연결

```bash
# VNC 클라이언트 설치
sudo apt install vinagre -y

# 또는 Remmina 사용
# 프로토콜: VNC
# 서버: server-ip:5901
# 비밀번호: VNC 비밀번호
```

---

## 📁 3. 파일 전송 (SFTP/SCP)

### SFTP 사용

```bash
# SFTP 연결
sftp username@server-ip

# SFTP 명령어
sftp> ls                    # 서버 파일 목록
sftp> lls                   # 로컬 파일 목록
sftp> cd /path/to/directory # 서버 디렉토리 이동
sftp> lcd /local/path       # 로컬 디렉토리 이동
sftp> get filename          # 서버에서 로컬로 다운로드
sftp> put filename          # 로컬에서 서버로 업로드
sftp> get -r directory      # 디렉토리 전체 다운로드
sftp> put -r directory      # 디렉토리 전체 업로드
sftp> quit                  # 종료
```

### SCP 사용

```bash
# 파일 업로드 (로컬 → 서버)
scp /local/file username@server-ip:/remote/path/

# 파일 다운로드 (서버 → 로컬)
scp username@server-ip:/remote/file /local/path/

# 디렉토리 전체 업로드
scp -r /local/directory username@server-ip:/remote/path/

# 디렉토리 전체 다운로드
scp -r username@server-ip:/remote/directory /local/path/

# 포트 지정
scp -P 2222 file username@server-ip:/path/
```

### GUI 파일 관리자 사용

```bash
# Nautilus (파일 관리자)에서 SFTP 연결
# 주소창에 입력: sftp://username@server-ip

# 또는 FileZilla 설치
sudo apt install filezilla -y
```

---

## 🗂️ 4. 네트워크 공유 (NFS/Samba)

### 방법 A: NFS 공유

#### 서버 측 설정

```bash
# NFS 서버 설치
sudo apt install nfs-kernel-server -y

# 공유할 디렉토리 생성
sudo mkdir -p /srv/nfs/share
sudo chown nobody:nogroup /srv/nfs/share
sudo chmod 755 /srv/nfs/share

# NFS 설정
sudo nano /etc/exports

# /etc/exports 내용 추가
/srv/nfs/share    192.168.1.0/24(rw,sync,no_subtree_check,no_root_squash)

# NFS 설정 적용
sudo exportfs -a
sudo systemctl restart nfs-kernel-server

# 방화벽 설정
sudo ufw allow from 192.168.1.0/24 to any port nfs
```

#### 데스크탑 측 마운트

```bash
# NFS 클라이언트 설치
sudo apt install nfs-common -y

# 마운트 포인트 생성
sudo mkdir -p /mnt/nfs/share

# NFS 마운트
sudo mount -t nfs server-ip:/srv/nfs/share /mnt/nfs/share

# 자동 마운트 설정
sudo nano /etc/fstab

# /etc/fstab에 추가
server-ip:/srv/nfs/share /mnt/nfs/share nfs defaults 0 0
```

### 방법 B: Samba 공유

#### 서버 측 설정

```bash
# Samba 설치
sudo apt install samba -y

# 공유할 디렉토리 생성
sudo mkdir -p /srv/samba/share
sudo chmod 777 /srv/samba/share

# Samba 설정
sudo nano /etc/samba/smb.conf

# smb.conf에 추가
[share]
    path = /srv/samba/share
    browseable = yes
    writable = yes
    guest ok = yes
    read only = no
    create mask = 0755

# Samba 사용자 추가
sudo smbpasswd -a username

# Samba 서비스 재시작
sudo systemctl restart smbd
sudo systemctl restart nmbd

# 방화벽 설정
sudo ufw allow samba
```

#### 데스크탑 측 연결

```bash
# Samba 클라이언트 설치
sudo apt install cifs-utils -y

# 마운트 포인트 생성
sudo mkdir -p /mnt/samba/share

# Samba 마운트
sudo mount -t cifs //server-ip/share /mnt/samba/share -o username=username

# GUI에서 연결
# 파일 관리자 주소창: smb://server-ip/share
```

---

## 💻 5. 개발 환경 연결 (VS Code Remote)

### VS Code Remote SSH 설정

#### 데스크탑에서 VS Code 설정

```bash
# VS Code 설치
sudo snap install --classic code

# Remote SSH 확장 설치
# Ctrl+Shift+X → "Remote - SSH" 검색 후 설치
```

#### SSH 설정 파일 생성

```bash
# SSH 설정 파일 편집
nano ~/.ssh/config

# 설정 내용
Host campuson-server
    HostName server-ip
    User username
    Port 22
    IdentityFile ~/.ssh/id_rsa
    ServerAliveInterval 60
    ServerAliveCountMax 3
```

#### VS Code에서 원격 연결

```
1. Ctrl+Shift+P
2. "Remote-SSH: Connect to Host" 선택
3. "campuson-server" 선택
4. 새 VS Code 창에서 서버 파일 시스템 접근 가능
```

---

## 🌐 6. 웹 기반 연결

### 방법 A: Cockpit (웹 관리 인터페이스)

#### 서버 측 설정

```bash
# Cockpit 설치
sudo apt install cockpit -y

# Cockpit 서비스 시작
sudo systemctl start cockpit
sudo systemctl enable cockpit

# 방화벽 설정
sudo ufw allow 9090/tcp

# 웹 브라우저에서 접속
# https://server-ip:9090
```

### 방법 B: Webmin (웹 관리 도구)

#### 서버 측 설치

```bash
# Webmin 저장소 추가
curl -o setup-repos.sh https://raw.githubusercontent.com/webmin/webmin/master/setup-repos.sh
sudo sh setup-repos.sh

# Webmin 설치
sudo apt install webmin -y

# 방화벽 설정
sudo ufw allow 10000/tcp

# 웹 브라우저에서 접속
# https://server-ip:10000
```

---

## 🔧 7. 네트워크 설정 및 문제 해결

### 네트워크 정보 확인

```bash
# IP 주소 확인
ip addr show
hostname -I
curl ifconfig.me  # 공인 IP

# 네트워크 연결 테스트
ping server-ip
telnet server-ip 22  # SSH 포트 테스트
nmap -p 22,80,443,3389,5901 server-ip  # 포트 스캔
```

### 방화벽 설정

```bash
# UFW 상태 확인
sudo ufw status

# 포트 허용
sudo ufw allow 22/tcp     # SSH
sudo ufw allow 80/tcp     # HTTP
sudo ufw allow 443/tcp    # HTTPS
sudo ufw allow 3389/tcp   # RDP
sudo ufw allow 5901/tcp   # VNC

# 특정 IP에서만 허용
sudo ufw allow from 192.168.1.100 to any port 22

# 방화벽 활성화
sudo ufw enable
```

### SSH 문제 해결

```bash
# SSH 서비스 상태 확인
sudo systemctl status ssh

# SSH 로그 확인
sudo journalctl -u ssh

# SSH 설정 테스트
sudo sshd -t

# SSH 키 권한 확인
chmod 600 ~/.ssh/id_rsa
chmod 644 ~/.ssh/id_rsa.pub
chmod 700 ~/.ssh
chmod 600 ~/.ssh/authorized_keys
```

---

## 🚀 8. CampusON 백엔드 특화 연결

### 개발 환경 연결

```bash
# 서버에서 개발 서버 실행
cd /opt/campuson
source venv/bin/activate
uvicorn main:app --host 0.0.0.0 --port 8000 --reload

# 데스크탑에서 API 접속
curl http://server-ip:8000/health
curl http://server-ip:8000/api/docs
```

### 데이터베이스 연결

```bash
# PostgreSQL 원격 접속 허용 (서버)
sudo nano /etc/postgresql/14/main/postgresql.conf
# listen_addresses = '*'

sudo nano /etc/postgresql/14/main/pg_hba.conf
# host all all 0.0.0.0/0 md5

sudo systemctl restart postgresql

# 데스크탑에서 DB 접속
psql -h server-ip -U admin -d kb_learning_db
```

### 로그 모니터링

```bash
# 실시간 로그 확인
ssh username@server-ip "tail -f /opt/campuson/logs/campuson.log"

# 또는 VS Code Remote로 로그 파일 열기
```

---

## 📊 9. 성능 최적화

### SSH 연결 최적화

```bash
# ~/.ssh/config 최적화 설정
Host *
    ServerAliveInterval 60
    ServerAliveCountMax 3
    Compression yes
    ControlMaster auto
    ControlPath ~/.ssh/master-%r@%h:%p
    ControlPersist 10m
```

### 네트워크 대역폭 최적화

```bash
# SSH 압축 사용
ssh -C username@server-ip

# SCP 압축 사용
scp -C file username@server-ip:/path/

# rsync 사용 (효율적인 파일 동기화)
rsync -avz -e ssh /local/path/ username@server-ip:/remote/path/
```

---

## 🔒 10. 보안 강화

### SSH 보안 설정

```bash
# SSH 설정 파일 편집
sudo nano /etc/ssh/sshd_config

# 보안 설정
Port 2222                    # 기본 포트 변경
PermitRootLogin no          # root 로그인 금지
PasswordAuthentication no   # 비밀번호 인증 금지
PubkeyAuthentication yes    # 키 인증만 허용
MaxAuthTries 3              # 인증 시도 제한
ClientAliveInterval 300     # 세션 타임아웃
ClientAliveCountMax 2

# SSH 서비스 재시작
sudo systemctl restart ssh
```

### Fail2Ban 설치 (무차별 대입 공격 방지)

```bash
# Fail2Ban 설치
sudo apt install fail2ban -y

# 설정 파일 생성
sudo cp /etc/fail2ban/jail.conf /etc/fail2ban/jail.local

# SSH 보호 설정
sudo nano /etc/fail2ban/jail.local

# [sshd] 섹션 수정
[sshd]
enabled = true
port = 2222
filter = sshd
logpath = /var/log/auth.log
maxretry = 3
bantime = 3600

# Fail2Ban 시작
sudo systemctl start fail2ban
sudo systemctl enable fail2ban
```

---

## 🎯 연결 방법 선택 가이드

| 용도 | 추천 방법 | 장점 | 단점 |
|------|-----------|------|------|
| 서버 관리 | SSH | 빠름, 안전 | 명령줄만 |
| 파일 전송 | SFTP/SCP | 안전, 간단 | GUI 없음 |
| GUI 작업 | XRDP/VNC | 완전한 데스크탑 | 느림, 대역폭 |
| 개발 작업 | VS Code Remote | 최적화됨 | VS Code 전용 |
| 파일 공유 | NFS/Samba | 투명한 접근 | 설정 복잡 |
| 웹 관리 | Cockpit | 브라우저 기반 | 기능 제한 |

---

## 🚨 문제 해결 체크리스트

### 연결이 안 될 때

- [ ] 서버 IP 주소 확인
- [ ] 네트워크 연결 상태 확인
- [ ] 방화벽 설정 확인
- [ ] SSH 서비스 상태 확인
- [ ] 포트 번호 확인
- [ ] 사용자 계정 및 권한 확인

### 속도가 느릴 때

- [ ] 네트워크 대역폭 확인
- [ ] SSH 압축 사용
- [ ] 불필요한 서비스 중지
- [ ] 경량 데스크탑 환경 사용

### 보안 경고가 뜰 때

- [ ] SSH 키 재생성
- [ ] known_hosts 파일 정리
- [ ] 서버 인증서 확인

---

**🎉 이제 우분투 서버와 데스크탑을 자유롭게 연결할 수 있습니다!**

각 방법의 특성을 이해하고 용도에 맞게 선택하여 사용하세요. 