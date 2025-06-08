#!/usr/bin/env python3
"""
로컬 DeepSeek 마이그레이션 플랜
OpenAI + Gemini → 로컬 DeepSeek (Ollama 기반)
"""
import os
import subprocess
import json
import logging
from pathlib import Path

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class DeepSeekMigrationPlan:
    """로컬 DeepSeek 마이그레이션 계획"""
    
    def __init__(self):
        self.backend_dir = Path(__file__).parent
        self.requirements_file = self.backend_dir / "requirements_deepseek.txt"
        
    def step1_install_ollama(self):
        """1단계: Ollama 설치"""
        logger.info("🚀 1단계: Ollama 설치")
        
        print("""
=== Ollama 설치 방법 ===

Windows (PowerShell 관리자 권한으로 실행):
1. 방법1: 설치 파일 다운로드
   - https://ollama.com/download/windows 에서 설치 파일 다운로드
   - 실행하여 설치

2. 방법2: winget 사용
   winget install Ollama.Ollama

3. 방법3: 수동 설치
   - GitHub에서 ollama-windows-amd64.zip 다운로드
   - 압축 해제 후 PATH에 추가

설치 후 확인:
   ollama --version

=== DeepSeek 모델 다운로드 ===
설치 완료 후 다음 명령어 실행:

# DeepSeek R1 7B (추천)
ollama pull deepseek-r1:7b

# 또는 더 작은 모델
ollama pull deepseek-r1:1.5b

# 임베딩 모델
ollama pull nomic-embed-text

서버 시작:
ollama serve
        """)
        
        # Ollama 상태 확인
        try:
            result = subprocess.run(["ollama", "--version"], 
                                    capture_output=True, text=True, timeout=10)
            if result.returncode == 0:
                logger.info(f"✅ Ollama 설치 확인됨: {result.stdout.strip()}")
                return True
            else:
                logger.warning("❌ Ollama가 설치되지 않았습니다.")
                return False
        except Exception as e:
            logger.warning(f"❌ Ollama 확인 실패: {e}")
            return False
    
    def step2_check_models(self):
        """2단계: 모델 설치 확인"""
        logger.info("🔍 2단계: DeepSeek 모델 확인")
        
        try:
            result = subprocess.run(["ollama", "list"], 
                                    capture_output=True, text=True, timeout=30)
            
            if result.returncode == 0:
                models = result.stdout
                logger.info(f"설치된 모델 목록:\n{models}")
                
                # 필수 모델 확인
                required_models = ["deepseek-r1", "nomic-embed-text"]
                missing_models = []
                
                for model in required_models:
                    if model not in models:
                        missing_models.append(model)
                
                if missing_models:
                    logger.warning(f"❌ 누락된 모델: {missing_models}")
                    print("\n다음 명령어로 설치하세요:")
                    for model in missing_models:
                        if "deepseek" in model:
                            print(f"ollama pull deepseek-r1:7b")
                        else:
                            print(f"ollama pull {model}")
                    return False
                else:
                    logger.info("✅ 모든 필수 모델 설치 완료")
                    return True
            else:
                logger.error("❌ Ollama 서버가 실행되지 않았습니다. 'ollama serve' 실행하세요.")
                return False
                
        except Exception as e:
            logger.error(f"❌ 모델 확인 실패: {e}")
            return False
    
    def step3_update_dependencies(self):
        """3단계: 종속성 업데이트"""
        logger.info("📦 3단계: 추가 종속성 설치")
        
        # DeepSeek용 추가 패키지
        deepseek_requirements = [
            "# 로컬 DeepSeek 마이그레이션용",
            "httpx>=0.24.0",
            "pytesseract>=0.3.10",  # OCR
            "pdf2image>=1.16.3",   # PDF to image
            "Pillow>=10.0.0",      # 이미지 처리
        ]
        
        try:
            with open(self.requirements_file, 'w', encoding='utf-8') as f:
                f.write('\n'.join(deepseek_requirements))
            
            logger.info(f"✅ requirements_deepseek.txt 생성 완료")
            
            print(f"""
다음 명령어로 추가 패키지를 설치하세요:
pip install -r {self.requirements_file}

OCR 기능을 위해 Tesseract도 설치가 필요합니다:
Windows: https://github.com/UB-Mannheim/tesseract/wiki
설치 후 PATH에 추가하거나 환경변수 TESSERACT_CMD 설정
            """)
            
            return True
            
        except Exception as e:
            logger.error(f"❌ 종속성 파일 생성 실패: {e}")
            return False
    
    def step4_update_env_config(self):
        """4단계: 환경 설정 업데이트"""
        logger.info("⚙️ 4단계: 환경 설정 업데이트")
        
        env_file = self.backend_dir / "env.ini"
        
        # DeepSeek 설정 추가
        deepseek_config = """

# 로컬 DeepSeek 설정 (마이그레이션)
OLLAMA_HOST=http://localhost:11434
DEEPSEEK_MODEL_NAME=deepseek-r1:7b
DEEPSEEK_EMBEDDING_MODEL=nomic-embed-text

# 마이그레이션 모드 (점진적 전환)
USE_LOCAL_DEEPSEEK=true
FALLBACK_TO_OPENAI=true
FALLBACK_TO_GEMINI=true

# OCR 설정 (선택사항)
TESSERACT_CMD=tesseract
"""
        
        try:
            with open(env_file, 'a', encoding='utf-8') as f:
                f.write(deepseek_config)
            
            logger.info("✅ env.ini에 DeepSeek 설정 추가 완료")
            return True
            
        except Exception as e:
            logger.error(f"❌ 환경 설정 업데이트 실패: {e}")
            return False
    
    def run_full_migration(self):
        """전체 마이그레이션 실행"""
        logger.info("🚀 로컬 DeepSeek 마이그레이션 시작")
        
        steps = [
            ("Ollama 설치", self.step1_install_ollama),
            ("모델 확인", self.step2_check_models),
            ("종속성 업데이트", self.step3_update_dependencies),
            ("환경 설정", self.step4_update_env_config),
        ]
        
        results = []
        
        for step_name, step_func in steps:
            print(f"\n{'='*50}")
            print(f"🔄 {step_name} 실행 중...")
            print(f"{'='*50}")
            
            try:
                success = step_func()
                results.append((step_name, success))
                
                if success:
                    print(f"✅ {step_name} 완료")
                else:
                    print(f"❌ {step_name} 실패")
                    
            except Exception as e:
                logger.error(f"❌ {step_name} 오류: {e}")
                results.append((step_name, False))
        
        # 결과 요약
        print(f"\n{'='*50}")
        print("📊 마이그레이션 결과 요약")
        print(f"{'='*50}")
        
        success_count = sum(1 for _, success in results if success)
        total_count = len(results)
        
        for step_name, success in results:
            status = "✅" if success else "❌"
            print(f"{status} {step_name}")
        
        print(f"\n완료율: {success_count}/{total_count} ({success_count/total_count*100:.1f}%)")
        
        if success_count == total_count:
            print("\n🎉 로컬 DeepSeek 마이그레이션 준비 완료!")
            print("\n다음 단계:")
            print("1. ollama serve 실행")
            print("2. python -m app.services.deepseek_service 테스트")
            print("3. USE_LOCAL_DEEPSEEK=true 설정으로 서버 재시작")
        else:
            print("\n⚠️ 일부 단계가 실패했습니다. 위의 지시사항을 따라 수동으로 완료해주세요.")

if __name__ == "__main__":
    migrator = DeepSeekMigrationPlan()
    migrator.run_full_migration() 