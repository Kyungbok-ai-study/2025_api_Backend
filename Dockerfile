# 우분투 22.04.1 LTS 기반 Python 3.9 이미지 사용
FROM ubuntu:22.04

# 환경 변수 설정
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    DEBIAN_FRONTEND=noninteractive \
    TZ=Asia/Seoul

# 시스템 패키지 업데이트 및 필수 패키지 설치
RUN apt-get update && apt-get install -y \
    python3.9 \
    python3.9-dev \
    python3.9-distutils \
    python3-pip \
    build-essential \
    curl \
    wget \
    git \
    # PDF 처리를 위한 poppler-utils
    poppler-utils \
    # 이미지 처리를 위한 라이브러리
    libjpeg-dev \
    libpng-dev \
    libtiff-dev \
    libfreetype6-dev \
    # PostgreSQL 클라이언트
    postgresql-client \
    libpq-dev \
    # 기타 유틸리티
    vim \
    htop \
    && rm -rf /var/lib/apt/lists/*

# Python 심볼릭 링크 생성
RUN ln -sf /usr/bin/python3.9 /usr/bin/python && \
    ln -sf /usr/bin/pip3 /usr/bin/pip

# pip 업그레이드
RUN pip install --upgrade pip setuptools wheel

# 작업 디렉토리 설정
WORKDIR /app

# Python 의존성 파일 복사 및 설치
COPY requirements.txt requirements_parser.txt requirements_deepseek.txt ./
RUN pip install --no-cache-dir -r requirements.txt && \
    pip install --no-cache-dir -r requirements_parser.txt && \
    pip install --no-cache-dir -r requirements_deepseek.txt

# 애플리케이션 코드 복사
COPY . .

# 업로드 디렉토리 생성
RUN mkdir -p uploads data/deepseek_learning exports

# 포트 노출
EXPOSE 8000

# 헬스체크 추가
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# 애플리케이션 실행
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "4"] 