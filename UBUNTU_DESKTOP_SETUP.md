# 🖥️ 우분투 데스크탑 완전 설정 가이드

## 📋 개요

우분투 데스크탑에서 CampusON 프로젝트 개발 및 서버 관리를 위한 필수 프로그램 설치 가이드입니다.

---

## 🚀 1. 시스템 기본 설정

### 시스템 업데이트

```bash
# 패키지 목록 업데이트
sudo apt update && sudo apt upgrade -y

# 스냅 패키지 업데이트
sudo snap refresh

# 불필요한 패키지 정리
sudo apt autoremove -y
sudo apt autoclean
```

### 한국어 설정

```bash
# 한국어 언어팩 설치
sudo apt install language-pack-ko -y

# 한국어 입력기 설치
sudo apt install ibus-hangul -y

# 한국어 폰트 설치
sudo apt install fonts-nanum fonts-nanum-coding fonts-nanum-extra -y

# 시스템 재시작 후 설정 → 지역 및 언어에서 한국어 추가
```

### 필수 시스템 도구

```bash
# 기본 개발 도구
sudo apt install -y \
    curl \
    wget \
    git \
    vim \
    nano \
    htop \
    tree \
    unzip \
    zip \
    build-essential \
    software-properties-common \
    apt-transport-https \
    ca-certificates \
    gnupg \
    lsb-release

# 네트워크 도구
sudo apt install -y \
    net-tools \
    nmap \
    telnet \
    openssh-client \
    openssh-server

# 시스템 모니터링
sudo apt install -y \
    neofetch \
    screenfetch \
    inxi \
    lm-sensors
```

---

## 💻 2. 개발 환경 설치

### Python 개발 환경

```bash
# Python 3.9+ 설치
sudo apt install -y \
    python3 \
    python3-pip \
    python3-venv \
    python3-dev \
    python-is-python3

# pip 업그레이드
python -m pip install --upgrade pip

# 가상환경 도구
pip install virtualenv pipenv

# Python 개발 도구
pip install \
    black \
    flake8 \
    isort \
    mypy \
    pytest \
    jupyter
```

### Node.js 개발 환경

```bash
# Node.js 18.x LTS 설치
curl -fsSL https://deb.nodesource.com/setup_18.x | sudo -E bash -
sudo apt install -y nodejs

# npm 글로벌 패키지
sudo npm install -g \
    yarn \
    pnpm \
    @vue/cli \
    @angular/cli \
    create-react-app \
    typescript \
    ts-node \
    nodemon \
    pm2

# 버전 확인
node --version
npm --version
```

### Git 설정

```bash
# Git 사용자 정보 설정
git config --global user.name "Your Name"
git config --global user.email "your.email@example.com"

# Git 기본 설정
git config --global init.defaultBranch main
git config --global core.editor nano
git config --global pull.rebase false

# Git 별칭 설정
git config --global alias.st status
git config --global alias.co checkout
git config --global alias.br branch
git config --global alias.ci commit
git config --global alias.lg "log --oneline --graph --all"
```

---

## 🛠️ 3. 개발 도구 설치

### Visual Studio Code

```bash
# VS Code 설치 (Snap)
sudo snap install --classic code

# 또는 deb 패키지로 설치
wget -qO- https://packages.microsoft.com/keys/microsoft.asc | gpg --dearmor > packages.microsoft.gpg
sudo install -o root -g root -m 644 packages.microsoft.gpg /etc/apt/trusted.gpg.d/
sudo sh -c 'echo "deb [arch=amd64,arm64,armhf signed-by=/etc/apt/trusted.gpg.d/packages.microsoft.gpg] https://packages.microsoft.com/repos/code stable main" > /etc/apt/sources.list.d/vscode.list'
sudo apt update
sudo apt install code -y
```

#### VS Code 필수 확장 프로그램

```bash
# 명령줄에서 확장 프로그램 설치
code --install-extension ms-python.python
code --install-extension ms-vscode-remote.remote-ssh
code --install-extension ms-vscode-remote.remote-containers
code --install-extension ms-vscode.vscode-typescript-next
code --install-extension esbenp.prettier-vscode
code --install-extension ms-vscode.vscode-json
code --install-extension redhat.vscode-yaml
code --install-extension ms-python.black-formatter
code --install-extension ms-python.flake8
code --install-extension ms-python.isort
code --install-extension bradlc.vscode-tailwindcss
code --install-extension Vue.volar
code --install-extension ms-vscode.hexeditor
code --install-extension GitLens.gitlens
code --install-extension ms-azuretools.vscode-docker
code --install-extension hashicorp.terraform
```

### 터미널 도구

```bash
# Zsh 및 Oh My Zsh 설치
sudo apt install zsh -y
sh -c "$(curl -fsSL https://raw.github.com/ohmyzsh/ohmyzsh/master/tools/install.sh)"

# Zsh 플러그인
git clone https://github.com/zsh-users/zsh-autosuggestions ${ZSH_CUSTOM:-~/.oh-my-zsh/custom}/plugins/zsh-autosuggestions
git clone https://github.com/zsh-users/zsh-syntax-highlighting.git ${ZSH_CUSTOM:-~/.oh-my-zsh/custom}/plugins/zsh-syntax-highlighting

# Terminator (고급 터미널)
sudo apt install terminator -y

# Tilix (타일링 터미널)
sudo apt install tilix -y
```

---

## 🐳 4. 컨테이너 및 가상화

### Docker 설치

```bash
# Docker 공식 설치
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh

# 사용자를 docker 그룹에 추가
sudo usermod -aG docker $USER

# Docker Compose 설치
sudo curl -L "https://github.com/docker/compose/releases/download/v2.20.0/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose

# Docker 서비스 시작
sudo systemctl start docker
sudo systemctl enable docker

# 로그아웃 후 다시 로그인하여 docker 명령어 사용 가능
```

### VirtualBox (선택사항)

```bash
# VirtualBox 설치
sudo apt install virtualbox virtualbox-ext-pack -y

# Vagrant 설치 (VM 관리 도구)
wget -O- https://apt.releases.hashicorp.com/gpg | gpg --dearmor | sudo tee /usr/share/keyrings/hashicorp-archive-keyring.gpg
echo "deb [signed-by=/usr/share/keyrings/hashicorp-archive-keyring.gpg] https://apt.releases.hashicorp.com $(lsb_release -cs) main" | sudo tee /etc/apt/sources.list.d/hashicorp.list
sudo apt update && sudo apt install vagrant -y
```

---

## 🗄️ 5. 데이터베이스 도구

### PostgreSQL 클라이언트

```bash
# PostgreSQL 클라이언트 설치
sudo apt install postgresql-client -y

# pgAdmin4 설치 (웹 기반 관리 도구)
curl https://www.pgadmin.org/static/packages_pgadmin_org.pub | sudo apt-key add
sudo sh -c 'echo "deb https://ftp.postgresql.org/pub/pgadmin/pgadmin4/apt/$(lsb_release -cs) pgadmin4 main" > /etc/apt/sources.list.d/pgadmin4.list'
sudo apt update
sudo apt install pgadmin4-desktop -y

# DBeaver (범용 DB 클라이언트)
sudo snap install dbeaver-ce
```

### Redis 클라이언트

```bash
# Redis CLI 설치
sudo apt install redis-tools -y

# Redis Desktop Manager (GUI)
sudo snap install redis-desktop-manager
```

---

## 🌐 6. 웹 브라우저 및 네트워크 도구

### 웹 브라우저

```bash
# Google Chrome
wget -q -O - https://dl.google.com/linux/linux_signing_key.pub | sudo apt-key add -
sudo sh -c 'echo "deb [arch=amd64] http://dl.google.com/linux/chrome/deb/ stable main" >> /etc/apt/sources.list.d/google-chrome.list'
sudo apt update
sudo apt install google-chrome-stable -y

# Firefox Developer Edition
sudo snap install firefox --channel=beta

# Microsoft Edge
curl https://packages.microsoft.com/keys/microsoft.asc | gpg --dearmor > microsoft.gpg
sudo install -o root -g root -m 644 microsoft.gpg /etc/apt/trusted.gpg.d/
sudo sh -c 'echo "deb [arch=amd64] https://packages.microsoft.com/repos/edge stable main" > /etc/apt/sources.list.d/microsoft-edge-dev.list'
sudo apt update
sudo apt install microsoft-edge-stable -y
```

### API 테스트 도구

```bash
# Postman
sudo snap install postman

# Insomnia
sudo snap install insomnia

# HTTPie (명령줄 HTTP 클라이언트)
sudo apt install httpie -y

# curl 고급 사용을 위한 jq
sudo apt install jq -y
```

---

## 📁 7. 파일 관리 및 FTP 도구

### 파일 관리자

```bash
# Nautilus 확장
sudo apt install nautilus-admin nautilus-image-converter -y

# Nemo (Cinnamon 파일 관리자)
sudo apt install nemo -y

# Thunar (XFCE 파일 관리자)
sudo apt install thunar -y
```

### FTP/SFTP 클라이언트

```bash
# FileZilla
sudo apt install filezilla -y

# WinSCP 대안 - Remmina
sudo apt install remmina remmina-plugin-rdp remmina-plugin-vnc -y

# 명령줄 SFTP 도구
sudo apt install lftp -y
```

---

## 🎨 8. 디자인 및 미디어 도구

### 이미지 편집

```bash
# GIMP
sudo apt install gimp -y

# Inkscape (벡터 그래픽)
sudo apt install inkscape -y

# ImageMagick (명령줄 이미지 처리)
sudo apt install imagemagick -y
```

### 스크린샷 도구

```bash
# Flameshot (고급 스크린샷)
sudo apt install flameshot -y

# Shutter (스크린샷 + 편집)
sudo apt install shutter -y

# Kazam (화면 녹화)
sudo apt install kazam -y
```

---

## 📚 9. 문서 및 오피스 도구

### 오피스 스위트

```bash
# LibreOffice (최신 버전)
sudo snap install libreoffice

# OnlyOffice
sudo snap install onlyoffice-desktopeditors
```

### 마크다운 에디터

```bash
# Typora
wget -qO - https://typora.io/linux/public-key.asc | sudo apt-key add -
sudo add-apt-repository 'deb https://typora.io/linux ./'
sudo apt update
sudo apt install typora -y

# Mark Text
sudo snap install marktext

# Obsidian (노트 앱)
sudo snap install obsidian --classic
```

---

## 🔧 10. 시스템 유틸리티

### 시스템 모니터링

```bash
# System Monitor 도구
sudo apt install -y \
    htop \
    iotop \
    nethogs \
    iftop \
    glances \
    bashtop

# GPU 모니터링 (NVIDIA)
sudo apt install nvidia-smi -y

# 디스크 사용량 분석
sudo apt install -y \
    ncdu \
    baobab
```

### 압축 도구

```bash
# 압축 관련 도구
sudo apt install -y \
    p7zip-full \
    p7zip-rar \
    unrar \
    zip \
    unzip \
    tar \
    gzip \
    bzip2

# GUI 압축 도구
sudo apt install file-roller -y
```

### 시스템 정리 도구

```bash
# BleachBit (시스템 정리)
sudo apt install bleachbit -y

# Stacer (시스템 최적화)
sudo apt install stacer -y
```

---

## 🎵 11. 멀티미디어

### 미디어 플레이어

```bash
# VLC Media Player
sudo apt install vlc -y

# MPV (경량 플레이어)
sudo apt install mpv -y

# Audacity (오디오 편집)
sudo apt install audacity -y

# OBS Studio (방송/녹화)
sudo snap install obs-studio
```

### 코덱 및 미디어 라이브러리

```bash
# 멀티미디어 코덱
sudo apt install -y \
    ubuntu-restricted-extras \
    ffmpeg \
    gstreamer1.0-plugins-bad \
    gstreamer1.0-plugins-ugly \
    gstreamer1.0-libav
```

---

## 🔐 12. 보안 도구

### VPN 클라이언트

```bash
# OpenVPN
sudo apt install openvpn network-manager-openvpn-gnome -y

# WireGuard
sudo apt install wireguard -y
```

### 방화벽 및 보안

```bash
# UFW (방화벽)
sudo apt install ufw -y
sudo ufw enable

# ClamAV (안티바이러스)
sudo apt install clamav clamav-daemon -y
sudo freshclam

# Fail2Ban (침입 방지)
sudo apt install fail2ban -y
```

---

## 🚀 13. CampusON 프로젝트 특화 설정

### 프론트엔드 개발 환경

```bash
# Vue.js 개발 도구
npm install -g @vue/cli @vue/cli-service-global

# Vite (빠른 빌드 도구)
npm install -g vite

# Tailwind CSS CLI
npm install -g tailwindcss

# ESLint & Prettier
npm install -g eslint prettier
```

### 백엔드 연결 도구

```bash
# SSH 키 생성 (서버 연결용)
ssh-keygen -t rsa -b 4096 -C "campuson-desktop"

# PostgreSQL 클라이언트 설정
echo "alias pgconnect='psql -h SERVER_IP -U admin -d kb_learning_db'" >> ~/.bashrc

# API 테스트 스크립트
cat > ~/api-test.sh << 'EOF'
#!/bin/bash
SERVER_IP=${1:-localhost}
echo "Testing CampusON API on $SERVER_IP"
curl -s http://$SERVER_IP:8000/health | jq .
curl -s http://$SERVER_IP:8000/api/info | jq .
EOF
chmod +x ~/api-test.sh
```

---

## 📋 14. 설치 완료 체크리스트

### 필수 프로그램 확인

```bash
# 설치 확인 스크립트
cat > ~/check-installation.sh << 'EOF'
#!/bin/bash
echo "=== CampusON 개발 환경 설치 확인 ==="

# 기본 도구
echo "1. 기본 도구"
command -v git >/dev/null 2>&1 && echo "✅ Git" || echo "❌ Git"
command -v curl >/dev/null 2>&1 && echo "✅ Curl" || echo "❌ Curl"
command -v wget >/dev/null 2>&1 && echo "✅ Wget" || echo "❌ Wget"

# 개발 환경
echo -e "\n2. 개발 환경"
command -v python >/dev/null 2>&1 && echo "✅ Python $(python --version)" || echo "❌ Python"
command -v node >/dev/null 2>&1 && echo "✅ Node.js $(node --version)" || echo "❌ Node.js"
command -v npm >/dev/null 2>&1 && echo "✅ NPM $(npm --version)" || echo "❌ NPM"

# 에디터
echo -e "\n3. 에디터"
command -v code >/dev/null 2>&1 && echo "✅ VS Code" || echo "❌ VS Code"

# 컨테이너
echo -e "\n4. 컨테이너"
command -v docker >/dev/null 2>&1 && echo "✅ Docker" || echo "❌ Docker"
command -v docker-compose >/dev/null 2>&1 && echo "✅ Docker Compose" || echo "❌ Docker Compose"

# 데이터베이스
echo -e "\n5. 데이터베이스"
command -v psql >/dev/null 2>&1 && echo "✅ PostgreSQL Client" || echo "❌ PostgreSQL Client"

# 네트워크 도구
echo -e "\n6. 네트워크 도구"
command -v ssh >/dev/null 2>&1 && echo "✅ SSH" || echo "❌ SSH"
command -v http >/dev/null 2>&1 && echo "✅ HTTPie" || echo "❌ HTTPie"

echo -e "\n=== 설치 확인 완료 ==="
EOF

chmod +x ~/check-installation.sh
~/check-installation.sh
```

---

## 🔄 15. 자동 설치 스크립트

### 원클릭 설치 스크립트

```bash
# 전체 설치 스크립트 생성
cat > ~/campuson-desktop-setup.sh << 'EOF'
#!/bin/bash

echo "🚀 CampusON 우분투 데스크탑 설정 시작..."

# 시스템 업데이트
sudo apt update && sudo apt upgrade -y

# 기본 도구 설치
sudo apt install -y curl wget git vim nano htop tree unzip build-essential

# Python 환경
sudo apt install -y python3 python3-pip python3-venv python3-dev
pip install --upgrade pip

# Node.js 설치
curl -fsSL https://deb.nodesource.com/setup_18.x | sudo -E bash -
sudo apt install -y nodejs

# VS Code 설치
sudo snap install --classic code

# Docker 설치
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
sudo usermod -aG docker $USER

# PostgreSQL 클라이언트
sudo apt install -y postgresql-client

# 개발 도구
sudo apt install -y filezilla remmina
sudo snap install postman

# 브라우저
sudo snap install firefox
wget -q -O - https://dl.google.com/linux/linux_signing_key.pub | sudo apt-key add -
sudo sh -c 'echo "deb [arch=amd64] http://dl.google.com/linux/chrome/deb/ stable main" >> /etc/apt/sources.list.d/google-chrome.list'
sudo apt update
sudo apt install -y google-chrome-stable

echo "✅ CampusON 데스크탑 설정 완료!"
echo "⚠️  로그아웃 후 다시 로그인하여 Docker 사용 가능"

EOF

chmod +x ~/campuson-desktop-setup.sh
```

---

## 📞 16. 문제 해결 및 지원

### 일반적인 문제 해결

```bash
# 패키지 의존성 문제
sudo apt install -f
sudo dpkg --configure -a

# 저장소 키 문제
sudo apt-key adv --keyserver keyserver.ubuntu.com --recv-keys [KEY_ID]

# 스냅 패키지 문제
sudo snap refresh
sudo systemctl restart snapd

# 권한 문제
sudo chown -R $USER:$USER ~/.local
sudo chown -R $USER:$USER ~/.config
```

### 유용한 명령어 모음

```bash
# 시스템 정보
neofetch
inxi -Fxz

# 디스크 사용량
df -h
ncdu /

# 메모리 사용량
free -h
htop

# 네트워크 상태
ip addr show
ss -tulpn

# 서비스 상태
systemctl --type=service --state=running
```

---

## 🎯 17. 추천 워크플로우

### 일일 개발 루틴

1. **시스템 체크**
   ```bash
   ~/check-installation.sh
   htop  # 시스템 리소스 확인
   ```

2. **서버 연결**
   ```bash
   ssh campuson-server  # SSH 연결
   code --remote ssh-remote+campuson-server /opt/campuson  # VS Code Remote
   ```

3. **API 테스트**
   ```bash
   ~/api-test.sh SERVER_IP
   ```

4. **개발 작업**
   - VS Code Remote로 백엔드 코딩
   - 로컬에서 프론트엔드 개발
   - Postman으로 API 테스트

### 프로젝트 관리

```bash
# 프로젝트 디렉토리 구조
mkdir -p ~/Projects/CampusON/{frontend,backend,docs,scripts}

# Git 저장소 클론
cd ~/Projects/CampusON
git clone [FRONTEND_REPO] frontend
git clone [BACKEND_REPO] backend

# 개발 환경 스크립트
cat > ~/Projects/CampusON/start-dev.sh << 'EOF'
#!/bin/bash
# 백엔드 서버 연결
code --remote ssh-remote+campuson-server /opt/campuson &

# 프론트엔드 개발 서버
cd ~/Projects/CampusON/frontend
npm run dev &

# API 문서 열기
google-chrome http://SERVER_IP:8000/docs &

echo "개발 환경 시작 완료!"
EOF
chmod +x ~/Projects/CampusON/start-dev.sh
```

---

**🎉 우분투 데스크탑 설정 완료!**

이제 CampusON 프로젝트 개발을 위한 완벽한 환경이 구축되었습니다. 각 도구의 특성을 이해하고 효율적으로 활용하세요! 