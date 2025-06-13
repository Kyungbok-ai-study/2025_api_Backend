"""
국가고시 카테고리별 저장 시스템
PostgreSQL (일반형) + Qdrant (벡터형) 저장
"""
import json
import os
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime
from pathlib import Path

from sqlalchemy.orm import Session
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct

from ..models.question import Question
from ..core.config import settings
import numpy as np

logger = logging.getLogger(__name__)

class CategoryStorageService:
    """카테고리별 저장 서비스"""
    
    def __init__(self):
        self.qdrant_client = None
        self.department_categories = {
            "간호학과": {
                "국가고시": {
                    "collection_name": "nursing_national_exam",
                    "description": "간호사 국가고시",
                    "vector_size": 768
                },
                "임상실습": {
                    "collection_name": "nursing_clinical_practice", 
                    "description": "간호 임상실습",
                    "vector_size": 768
                },
                "일반": {
                    "collection_name": "nursing_general",
                    "description": "간호학과 일반",
                    "vector_size": 768
                }
            },
            "물리치료학과": {
                "국가고시": {
                    "collection_name": "pt_national_exam",
                    "description": "물리치료사 국가고시",
                    "vector_size": 768
                },
                "재활치료": {
                    "collection_name": "pt_rehabilitation",
                    "description": "물리치료 재활",
                    "vector_size": 768
                },
                "일반": {
                    "collection_name": "pt_general",
                    "description": "물리치료학과 일반",
                    "vector_size": 768
                }
            },
            "작업치료학과": {
                "국가고시": {
                    "collection_name": "ot_national_exam",
                    "description": "작업치료사 국가고시",
                    "vector_size": 768
                },
                "인지재활": {
                    "collection_name": "ot_cognitive_rehab",
                    "description": "작업치료 인지재활",
                    "vector_size": 768
                },
                "일반": {
                    "collection_name": "ot_general",
                    "description": "작업치료학과 일반",
                    "vector_size": 768
                }
            }
        }
        
        # 난이도 및 문제유형 매핑
        self.difficulty_mapping = {
            "상": {"level": 3, "description": "고난이도", "score_range": "80-100"},
            "중": {"level": 2, "description": "중간난이도", "score_range": "60-79"},
            "하": {"level": 1, "description": "기초난이도", "score_range": "40-59"}
        }
        
        self.question_type_mapping = {
            "multiple_choice": {"type_id": 1, "description": "객관식", "format": "5지선다"},
            "short_answer": {"type_id": 2, "description": "단답형", "format": "서술형"},
            "essay": {"type_id": 3, "description": "논술형", "format": "장문서술"},
            "true_false": {"type_id": 4, "description": "참/거짓", "format": "O/X"}
        }
        
    def initialize_qdrant_client(self):
        """Qdrant 클라이언트 초기화"""
        try:
            # Docker로 실행 중인 Qdrant 연결
            self.qdrant_client = QdrantClient(
                host="localhost",
                port=6333,
                timeout=30
            )
            logger.info("✅ Qdrant 클라이언트 연결 성공")
            return True
        except Exception as e:
            logger.error(f"❌ Qdrant 클라이언트 연결 실패: {e}")
            return False
    
    def create_collection_if_not_exists(self, department: str, category: str):
        """학과-카테고리별 컬렉션 생성"""
        if not self.qdrant_client:
            if not self.initialize_qdrant_client():
                return False
                
        try:
            # 학과와 카테고리에 맞는 컬렉션 설정 가져오기
            if department not in self.department_categories:
                department = "일반학과"
                
            category_config = self.department_categories.get(department, {}).get(category)
            if not category_config:
                # 기본 일반 카테고리 사용
                category_config = {
                    "collection_name": f"{department.lower()}_general",
                    "description": f"{department} 일반",
                    "vector_size": 768
                }
            
            collection_name = category_config["collection_name"]
            
            # 컬렉션 존재 여부 확인
            try:
                collection_info = self.qdrant_client.get_collection(collection_name)
                logger.info(f"✅ 컬렉션 '{collection_name}' 이미 존재함")
                return True
            except:
                # 컬렉션이 없으면 생성
                self.qdrant_client.create_collection(
                    collection_name=collection_name,
                    vectors_config=VectorParams(
                        size=category_config["vector_size"],
                        distance=Distance.COSINE
                    )
                )
                logger.info(f"✅ 컬렉션 '{collection_name}' 생성 완료")
                return True
                
        except Exception as e:
            logger.error(f"❌ 컬렉션 생성 실패: {e}")
            return False
    
    def store_approved_questions(
        self, 
        db: Session, 
        questions: List[Question], 
        department: str
    ) -> Dict[str, Any]:
        """승인된 문제들을 카테고리별로 저장"""
        results = {
            "total_processed": 0,
            "postgresql_stored": 0,
            "qdrant_stored": 0,
            "errors": []
        }
        
        try:
            for question in questions:
                results["total_processed"] += 1
                
                # PostgreSQL 저장 (이미 저장되어 있음)
                results["postgresql_stored"] += 1
                
                # 카테고리별 Qdrant 저장
                category = question.file_category or "일반"
                
                # 국가고시 카테고리인 경우에만 벡터 저장
                if category == "국가고시":
                    if self.store_to_qdrant(question, department, category):
                        results["qdrant_stored"] += 1
                    else:
                        results["errors"].append(f"문제 {question.id} Qdrant 저장 실패")
                        
        except Exception as e:
            logger.error(f"❌ 승인된 문제 저장 실패: {e}")
            results["errors"].append(str(e))
            
        return results
    
    def store_to_qdrant(self, question: Question, department: str, category: str) -> bool:
        """개별 문제를 Qdrant에 저장"""
        try:
            # 컬렉션 생성 확인
            if not self.create_collection_if_not_exists(department, category):
                return False
                
            # 컬렉션 이름 가져오기
            category_config = self.department_categories.get(department, {}).get(category)
            if not category_config:
                category_config = {
                    "collection_name": f"{department.lower()}_general",
                    "description": f"{department} 일반",
                    "vector_size": 768
                }
            
            collection_name = category_config["collection_name"]
            
            # 문제 텍스트 임베딩 생성 (가상의 벡터 - 실제로는 DeepSeek API 사용)
            question_text = f"{question.content} {question.description or ''}"
            # 임시로 랜덤 벡터 생성 (실제 구현에서는 DeepSeek 임베딩 API 사용)
            vector = np.random.rand(768).tolist()
            
            # 메타데이터 구성
            payload = {
                "question_id": question.id,
                "question_number": question.question_number,
                "content": question.content,
                "description": question.description,
                "correct_answer": question.correct_answer,
                "subject": question.subject,
                "area_name": question.area_name,
                "difficulty": question.difficulty,
                "difficulty_level": self.difficulty_mapping.get(str(question.difficulty), {}).get("level", 2),
                "question_type": question.question_type or "multiple_choice",
                "question_type_id": self.question_type_mapping.get(question.question_type or "multiple_choice", {}).get("type_id", 1),
                "year": question.year,
                "department": department,
                "category": category,
                "file_title": question.file_title,
                "created_at": question.created_at.isoformat() if question.created_at else None,
                "approved_at": question.approved_at.isoformat() if question.approved_at else None
            }
            
            # Qdrant에 저장
            point = PointStruct(
                id=question.id,
                vector=vector,
                payload=payload
            )
            
            self.qdrant_client.upsert(
                collection_name=collection_name,
                points=[point]
            )
            
            logger.info(f"✅ 문제 {question.id} Qdrant 저장 완료 ({collection_name})")
            return True
            
        except Exception as e:
            logger.error(f"❌ 문제 {question.id} Qdrant 저장 실패: {e}")
            return False
    
    def get_collection_stats(self, department: str) -> Dict[str, Any]:
        """학과별 컬렉션 통계 조회"""
        stats = {
            "department": department,
            "collections": {},
            "total_questions": 0
        }
        
        try:
            if not self.qdrant_client:
                if not self.initialize_qdrant_client():
                    return stats
                    
            dept_categories = self.department_categories.get(department, {})
            
            for category, config in dept_categories.items():
                collection_name = config["collection_name"]
                try:
                    collection_info = self.qdrant_client.get_collection(collection_name)
                    point_count = collection_info.points_count
                    
                    stats["collections"][category] = {
                        "collection_name": collection_name,
                        "description": config["description"],
                        "point_count": point_count,
                        "vector_size": config["vector_size"]
                    }
                    stats["total_questions"] += point_count
                    
                except Exception as e:
                    stats["collections"][category] = {
                        "collection_name": collection_name,
                        "description": config["description"],
                        "point_count": 0,
                        "error": str(e)
                    }
                    
        except Exception as e:
            logger.error(f"❌ 컬렉션 통계 조회 실패: {e}")
            stats["error"] = str(e)
            
        return stats
    
    def search_questions_by_vector(
        self, 
        department: str, 
        category: str, 
        query_text: str, 
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """벡터 유사도로 문제 검색"""
        results = []
        
        try:
            if not self.qdrant_client:
                if not self.initialize_qdrant_client():
                    return results
                    
            # 컬렉션 이름 가져오기
            category_config = self.department_categories.get(department, {}).get(category)
            if not category_config:
                return results
                
            collection_name = category_config["collection_name"]
            
            # 쿼리 텍스트를 벡터로 변환 (임시로 랜덤 벡터 사용)
            query_vector = np.random.rand(768).tolist()
            
            # 유사도 검색
            search_results = self.qdrant_client.search(
                collection_name=collection_name,
                query_vector=query_vector,
                limit=limit,
                with_payload=True
            )
            
            for result in search_results:
                results.append({
                    "question_id": result.payload.get("question_id"),
                    "content": result.payload.get("content"),
                    "similarity_score": result.score,
                    "metadata": result.payload
                })
                
        except Exception as e:
            logger.error(f"❌ 벡터 검색 실패: {e}")
            
        return results 