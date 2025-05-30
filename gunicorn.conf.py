# Gunicorn 설정 파일

# 바인드 설정
bind = "0.0.0.0:8000"

# 워커 설정
workers = 4
worker_class = "uvicorn.workers.UvicornWorker"
worker_connections = 1000

# 성능 설정
max_requests = 1000
max_requests_jitter = 100
preload_app = True

# 타임아웃 설정
timeout = 30
keepalive = 5
graceful_timeout = 30

# 로깅 설정
accesslog = "-"  # stdout으로 출력
errorlog = "-"   # stderr로 출력
loglevel = "info"
access_log_format = '%h %l %u %t "%r" %s %b "%{Referer}i" "%{User-Agent}i" %D'

# 프로세스 설정
user = None  # Railway에서 자동 처리
group = None
tmp_upload_dir = None

# 보안 설정
limit_request_line = 4096
limit_request_fields = 100
limit_request_field_size = 8190

# 개발 모드 (프로덕션에서는 False)
reload = False 