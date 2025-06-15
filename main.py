#!/usr/bin/env python3
"""
CampusON 백엔드 메인 서버
Exaone 로컬 AI 통합 서버
"""

import uvicorn
import threading
import subprocess
import time
import logging
import sys
import os
from pathlib import Path

# 환경 변수 설정
os.environ["PYTHONPATH"] = str(Path(__file__).parent)

from app.main import app

logger = logging.getLogger(__name__)

def start_ollama_exaone():
    """
    Ollama Exaone 모델 자동 시작
    """
    try:
        logger.info("🚀 Ollama Exaone 서비스 시작 중...")
        
        # Ollama 서비스 상태 확인
        try:
            result = subprocess.run(["ollama", "list"], capture_output=True, text=True)
            if result.returncode != 0:
                logger.warning("⚠️ Ollama 서비스가 실행되지 않음. 자동 시작 시도...")
                # Ollama 서비스 시작 (백그라운드)
                subprocess.Popen(["ollama", "serve"], 
                               stdout=subprocess.DEVNULL, 
                               stderr=subprocess.DEVNULL)
                time.sleep(5)  # 서비스 시작 대기
        except FileNotFoundError:
            logger.error("❌ Ollama가 설치되지 않았습니다. https://ollama.ai 에서 설치하세요.")
            return
        
        # Exaone 모델 다운로드 및 설정
        logger.info("📥 Exaone 모델 다운로드 중...")
        
        # exaone-deep:7.8b 모델 풀
        pull_result = subprocess.run(
            ["ollama", "pull", "exaone-deep:7.8b"],
            capture_output=True,
            text=True,
            timeout=1800  # 30분 타임아웃
        )
        
        if pull_result.returncode == 0:
            logger.info("✅ Exaone 모델 다운로드 완료")
        else:
            logger.warning(f"⚠️ Exaone 모델 다운로드 실패: {pull_result.stderr}")
        
        # 임베딩 모델도 다운로드
        logger.info("📥 임베딩 모델 다운로드 중...")
        embed_result = subprocess.run(
            ["ollama", "pull", "mxbai-embed-large"],
            capture_output=True,
            text=True,
            timeout=600  # 10분 타임아웃
        )
        
        if embed_result.returncode == 0:
            logger.info("✅ 임베딩 모델 다운로드 완료")
        
        # 모델 테스트
        logger.info("🧪 Exaone 모델 테스트 중...")
        test_result = subprocess.run([
            "ollama", "run", "exaone-deep:7.8b", "--"
        ], input="안녕하세요, 테스트입니다.", 
           capture_output=True, 
           text=True, 
           timeout=30)
        
        if test_result.returncode == 0:
            logger.info("✅ Exaone 모델 정상 작동 확인")
        else:
            logger.warning("⚠️ Exaone 모델 테스트 실패")
        
        # Modelfile 생성 (한국어 최적화)
        modelfile_content = '''
FROM exaone-deep:7.8b

PARAMETER temperature 0.7
PARAMETER top_k 40
PARAMETER top_p 0.9
PARAMETER num_predict 2048

SYSTEM """
당신은 한국의 교육 전문 AI 어시스턴트입니다.
- 정확하고 교육적인 답변을 제공합니다
- 한국어로 자연스럽게 대화합니다  
- 전문적이면서도 이해하기 쉽게 설명합니다
- 교육 현장에 적합한 내용을 생성합니다
"""
'''
        
        # 커스텀 모델 생성
        with open("Modelfile", "w", encoding="utf-8") as f:
            f.write(modelfile_content)
        
        logger.info("🔧 Exaone 커스텀 모델 생성 중...")
        create_result = subprocess.run([
            "ollama", "create", "exaone-edu", "-f", "Modelfile"
        ], capture_output=True, text=True)
        
        if create_result.returncode == 0:
            logger.info("✅ Exaone 교육용 모델 생성 완료")
        
        # 설정 파일 정리
        if os.path.exists("Modelfile"):
            os.remove("Modelfile")
        
        logger.info("🎉 Exaone 서비스 초기화 완료!")
        
    except subprocess.TimeoutExpired:
        logger.error("❌ Exaone 모델 다운로드 시간 초과")
    except Exception as e:
        logger.error(f"❌ Exaone 초기화 실패: {e}")

def check_requirements():
    """필수 요구사항 확인"""
    logger.info("🔍 시스템 요구사항 확인 중...")
    
    # Python 버전 확인
    if sys.version_info < (3, 8):
        logger.error("❌ Python 3.8 이상이 필요합니다.")
        return False
    
    # 필수 디렉토리 생성
    required_dirs = [
        "uploads",
        "data", 
        "logs",
        "temp",
        "uploads/rag_documents",
        "data/exaone_training"
    ]
    
    for dir_path in required_dirs:
        Path(dir_path).mkdir(parents=True, exist_ok=True)
    
    logger.info("✅ 시스템 요구사항 확인 완료")
    return True

if __name__ == "__main__":
    # 로깅 설정
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler("logs/main.log", encoding='utf-8'),
            logging.StreamHandler(sys.stdout)
        ]
    )
    
    logger.info("🚀 CampusON 백엔드 서버 시작")
    logger.info("🤖 Exaone 로컬 AI 통합 모드")
    
    # 요구사항 확인
    if not check_requirements():
        sys.exit(1)
    
    # Ollama Exaone 서비스 시작 (백그라운드)
    threading.Thread(target=start_ollama_exaone, daemon=True).start()
    
    # FastAPI 서버 시작
    logger.info("🌐 FastAPI 서버 시작 중...")
    logger.info("📡 서버 주소: http://localhost:8000")
    logger.info("📚 API 문서: http://localhost:8000/docs")
    logger.info("🔧 관리자 대시보드: http://localhost:8000/admin")
    
    try:
        uvicorn.run(
            "app.main:app",
            host="0.0.0.0", 
            port=8000,
            reload=True,
            reload_dirs=["app"],
            log_config={
                "version": 1,
                "disable_existing_loggers": False,
                "formatters": {
                    "default": {
                        "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
                    },
                },
                "handlers": {
                    "default": {
                        "formatter": "default",
                        "class": "logging.StreamHandler",
                        "stream": "ext://sys.stdout",
                    },
                    "file": {
                        "formatter": "default", 
                        "class": "logging.FileHandler",
                        "filename": "logs/server.log",
                        "encoding": "utf-8",
                    },
                },
                "root": {
                    "level": "INFO",
                    "handlers": ["default", "file"],
                },
            }
        )
    except KeyboardInterrupt:
        logger.info("🛑 서버 종료 중...")
    except Exception as e:
        logger.error(f"❌ 서버 실행 오류: {e}")
        sys.exit(1) 