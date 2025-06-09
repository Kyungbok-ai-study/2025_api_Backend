#!/usr/bin/env python3
"""
API 키 로드 테스트 스크립트
"""
import os
import sys
from pathlib import Path

# 프로젝트 루트를 Python 경로에 추가
sys.path.append(str(Path(__file__).parent))

from app.core.config import settings

def test_api_key_loading():
    """API 키 로드 상태 확인"""
    print("API 키 로드 테스트 시작")
    print("="*50)
    
    # 1. 환경변수에서 직접 확인
    env_key = os.getenv("GEMINI_API_KEY")
    print(f"1. 환경변수에서 API 키: {'설정됨' if env_key else '설정안됨'}")
    if env_key:
        print(f"   값: {env_key[:10]}...{env_key[-5:] if len(env_key) > 15 else env_key}")
    
    # 2. settings에서 확인
    settings_key = settings.GEMINI_API_KEY
    print(f"2. settings에서 API 키: {'설정됨' if settings_key else '설정안됨'}")
    if settings_key:
        print(f"   값: {settings_key[:10]}...{settings_key[-5:] if len(settings_key) > 15 else settings_key}")
    
    # 3. Gemini 모델 초기화 테스트
    print("\n3. Gemini 모델 초기화 테스트:")
    try:
        import google.generativeai as genai
        
        # API 키 설정
        api_key = settings_key or env_key
        if api_key:
            genai.configure(api_key=api_key)
            model = genai.GenerativeModel('gemini-1.5-flash-latest')
            print("   Gemini 모델 초기화 성공")
            
            # 간단한 테스트 요청
            try:
                response = model.generate_content("안녕하세요. 간단한 테스트입니다.")
                print("   API 호출 테스트: 성공")
                print(f"   응답: {response.text[:100]}...")
            except Exception as e:
                print(f"   API 호출 테스트: 실패 - {e}")
        else:
            print("   API 키가 없어서 모델 초기화 불가")
            
    except ImportError:
        print("   google.generativeai 라이브러리 없음")
    except Exception as e:
        print(f"   Gemini 초기화 실패: {e}")

if __name__ == "__main__":
    test_api_key_loading() 