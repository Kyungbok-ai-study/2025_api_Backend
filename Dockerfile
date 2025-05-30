FROM python:3.9-slim

# 작업 디렉토리 설정
WORKDIR /app

# 시스템 패키지 업데이트 및 필수 도구 설치
RUN apt-get update && apt-get install -y \
    postgresql-client \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Python 의존성 파일 복사
COPY requirements.txt .

# Python 패키지 설치
RUN pip install --no-cache-dir -r requirements.txt

# 애플리케이션 코드 복사
COPY . .

# 로그 디렉토리 생성
RUN mkdir -p /app/logs

# 포트 노출
EXPOSE 8000

# 헬스 체크
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
  CMD curl -f http://localhost:8000/health || exit 1

# Gunicorn으로 애플리케이션 실행
CMD ["gunicorn", "-c", "gunicorn.conf.py", "app.main:app"] 