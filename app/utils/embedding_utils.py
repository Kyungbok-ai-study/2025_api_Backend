"""
텍스트 임베딩 유틸리티 모듈

이 모듈은 다양한 라이브러리를 사용하여 텍스트 임베딩을 생성하는 기능을 제공합니다.
- OpenAI API
- Sentence Transformers
- 기타 임베딩 모델
"""
import os
import logging
from typing import List, Optional, Dict, Any, Union

# OpenAI 임베딩용
try:
    import openai
    from openai import OpenAI
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False
    logging.warning("OpenAI 모듈이 설치되지 않았습니다. 'pip install openai'로 설치해주세요.")

# Sentence Transformers 임베딩용
try:
    from sentence_transformers import SentenceTransformer
    SENTENCE_TRANSFORMERS_AVAILABLE = True
except ImportError:
    SENTENCE_TRANSFORMERS_AVAILABLE = False
    logging.warning("Sentence Transformers 모듈이 설치되지 않았습니다. 'pip install sentence-transformers'로 설치해주세요.")

# 기본 설정
DEFAULT_OPENAI_MODEL = "text-embedding-ada-002"
DEFAULT_ST_MODEL = "paraphrase-multilingual-MiniLM-L12-v2"  # 다국어 지원 모델

# 싱글톤 패턴으로 모델 인스턴스 관리
_st_model_instances = {}


def create_openai_embedding(
    text: Union[str, List[str]], 
    model: str = DEFAULT_OPENAI_MODEL,
    api_key: Optional[str] = None
) -> List[List[float]]:
    """
    OpenAI API를 사용하여 텍스트 임베딩 생성
    
    Args:
        text (Union[str, List[str]]): 임베딩할 텍스트 또는 텍스트 목록
        model (str): 사용할 OpenAI 임베딩 모델
        api_key (str, optional): OpenAI API 키, None인 경우 환경 변수 사용
        
    Returns:
        List[List[float]]: 임베딩 벡터 목록
    """
    if not OPENAI_AVAILABLE:
        raise ImportError("OpenAI 모듈이 설치되지 않았습니다. 'pip install openai'로 설치해주세요.")
    
    # API 키 설정
    if api_key:
        client = OpenAI(api_key=api_key)
    else:
        client = OpenAI()  # 환경 변수 OPENAI_API_KEY 사용
    
    try:
        # 단일 텍스트를 리스트로 변환
        if isinstance(text, str):
            text = [text]
        
        # 각 텍스트의 길이가 너무 긴 경우 자르기 (OpenAI 제한)
        processed_texts = [t[:8000] for t in text]
        
        # OpenAI API 호출하여 임베딩 생성
        response = client.embeddings.create(
            model=model,
            input=processed_texts
        )
        
        # 응답에서 임베딩 벡터 추출
        embeddings = [item.embedding for item in response.data]
        return embeddings
    
    except Exception as e:
        logging.error(f"OpenAI 임베딩 생성 오류: {str(e)}")
        return [[0.0] * 1536] * len(text) if isinstance(text, list) else [[0.0] * 1536]


def create_sentence_transformer_embedding(
    text: Union[str, List[str]],
    model_name: str = DEFAULT_ST_MODEL
) -> List[List[float]]:
    """
    Sentence Transformers를 사용하여 텍스트 임베딩 생성
    
    Args:
        text (Union[str, List[str]]): 임베딩할 텍스트 또는 텍스트 목록
        model_name (str): 사용할 Sentence Transformer 모델 이름
        
    Returns:
        List[List[float]]: 임베딩 벡터 목록
    """
    if not SENTENCE_TRANSFORMERS_AVAILABLE:
        raise ImportError("Sentence Transformers 모듈이 설치되지 않았습니다. 'pip install sentence-transformers'로 설치해주세요.")
    
    try:
        # 모델 인스턴스가 없으면 새로 생성
        if model_name not in _st_model_instances:
            _st_model_instances[model_name] = SentenceTransformer(model_name)
        
        model = _st_model_instances[model_name]
        
        # 단일 텍스트를 리스트로 변환
        if isinstance(text, str):
            text = [text]
        
        # 임베딩 생성
        embeddings = model.encode(text, convert_to_numpy=True).tolist()
        return embeddings
    
    except Exception as e:
        logging.error(f"Sentence Transformers 임베딩 생성 오류: {str(e)}")
        # 기본 모델의 차원 수를 알 수 없으므로 작은 차원으로 초기화
        return [[0.0] * 384] * len(text) if isinstance(text, list) else [[0.0] * 384]


def create_embedding(
    text: Union[str, List[str]],
    model_type: str = "openai",
    model_name: Optional[str] = None,
    api_key: Optional[str] = None
) -> List[List[float]]:
    """
    여러 임베딩 모델을 지원하는 통합 함수
    
    Args:
        text (Union[str, List[str]]): 임베딩할 텍스트 또는 텍스트 목록
        model_type (str): 사용할 모델 유형 ("openai" 또는 "sentence_transformers")
        model_name (str, optional): 모델 이름, None이면 기본값 사용
        api_key (str, optional): API 키 (필요한 경우)
        
    Returns:
        List[List[float]]: 임베딩 벡터 목록
    """
    if model_type.lower() == "openai":
        return create_openai_embedding(
            text=text,
            model=model_name or DEFAULT_OPENAI_MODEL,
            api_key=api_key
        )
    elif model_type.lower() in ["sentence_transformers", "st"]:
        return create_sentence_transformer_embedding(
            text=text,
            model_name=model_name or DEFAULT_ST_MODEL
        )
    else:
        raise ValueError(f"지원하지 않는 모델 유형: {model_type}") 