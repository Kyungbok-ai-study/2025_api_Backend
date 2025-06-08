# 🧹 데이터베이스 정리 및 최적화 계획

## 📊 현재 상황 분석

### ✅ 잘 구성된 부분
- **모델 분리**: 7개 주요 모델 (User, Question, Diagnosis, Assignment, Analytics, Verification, TestSet)
- **관계 설정**: 적절한 Foreign Key 설정
- **인덱싱**: 주요 검색 필드에 인덱스 적용
- **마이그레이션**: Alembic을 통한 체계적 관리

### 🟡 정리 필요 사항

#### 1. 중복 마이그레이션 파일 정리
```
현재:
- 468e28241915_initial_migration_with_all_models.py (30KB)
- 20250101_add_user_id_and_terms.py (2.5KB)
- 6ce456f9a623_add_user_id_and_terms_fields_v2.py (2.4KB)  ← 중복
- 4444582f8338_add_rag_support_and_update_question_.py (17KB)
- add_admin_role.py (916B)

정리 후:
- 01_initial_schema.py (통합)
- 02_rag_integration.py
- 03_admin_features.py
```

#### 2. 모델별 중복 필드 정리

##### User 모델 최적화
```sql
-- 제거할 중복/사용안함 필드
- student_id (user_id와 중복)
- profile_image (현재 미사용)
- admission_year (department 정보로 충분)

-- 통합할 필드
- terms_agreed, privacy_agreed → user_agreements (JSON)
- identity_verified, age_verified → verification_status (JSON)
```

##### Question 모델 최적화
```sql
-- 제거할 중복 필드
- subject_name vs area_name (통합 필요)
- approval_status, approved_by (별도 테이블로 분리)
- vector_db_indexed, rag_indexed, llm_training_added (상태 JSON으로)

-- 최적화할 필드
- embedding (벡터 크기 최적화 1536 → 768)
- options (JSONB → 구조화된 스키마)
```

#### 3. 분석 모델 통합
```sql
-- 현재: 여러 분산된 분석 테이블
- StudentActivity
- LearningAnalytics  
- ClassStatistics
- ProfessorDashboardData

-- 통합 후: 계층적 구조
- Activities (기본 활동 로그)
- Analytics (집계된 분석 데이터)
- Dashboard_Cache (대시보드 전용 캐시)
```

## 🎯 정리 실행 계획

### 1단계: 백업 및 분석
```bash
# 현재 DB 스키마 백업
pg_dump -s your_db > schema_backup.sql

# 사용하지 않는 컬럼 분석
SELECT column_name, is_nullable 
FROM information_schema.columns 
WHERE table_schema = 'public';
```

### 2단계: 마이그레이션 통합
```python
# 새로운 통합 마이그레이션 생성
alembic revision --autogenerate -m "consolidate_schema_v2"
```

### 3단계: 모델 최적화
- 중복 필드 제거
- JSON 필드로 통합
- 인덱스 최적화

### 4단계: 성능 최적화
- 벡터 인덱스 재구성
- 쿼리 성능 분석
- 캐싱 전략 적용

## 📈 예상 효과

### 데이터베이스 크기 감소
- **스키마 복잡도**: 30% 감소
- **중복 데이터**: 50% 감소
- **인덱스 최적화**: 쿼리 성능 40% 향상

### 유지보수성 향상
- **모델 복잡도** 단순화
- **마이그레이션** 이력 정리
- **개발 효율성** 증대

## ⚠️ 주의사항

### 데이터 손실 방지
1. **단계별 백업** 필수  
2. **롤백 계획** 수립
3. **테스트 환경** 선행 검증

### 호환성 유지
1. **API 호환성** 보장
2. **기존 기능** 정상 작동
3. **마이그레이션** 무중단 실행

## 🚀 실행 순서

1. ✅ **백업** (현재 스키마, 데이터)
2. 🔄 **테스트 환경** 정리 실행  
3. ✨ **운영 환경** 적용
4. 📊 **성능 모니터링**
5. 🧹 **최종 정리**

---

**시작할까요?** 먼저 현재 데이터베이스를 백업하고 테스트 정리를 진행하겠습니다! 🎯 