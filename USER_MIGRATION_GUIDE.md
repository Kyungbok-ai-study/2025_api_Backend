# 🔄 User 모델 최적화 및 마이그레이션 가이드

## 📊 개요

기존 `users` 테이블의 26개 컬럼을 13개 컬럼으로 최적화 (50% 감소)하여 성능을 향상시키고 유지보수성을 개선했습니다.

## 🔍 최적화 내용

### Before (26개 컬럼)
```sql
users (
    id, school, user_id, student_id, name, email, hashed_password, role,
    is_first_login, is_active, profile_image, department, admission_year, phone_number,
    terms_agreed, privacy_agreed, privacy_optional_agreed, marketing_agreed,
    identity_verified, age_verified, verification_method,
    diagnostic_test_completed, diagnostic_test_completed_at,
    created_at, updated_at, last_login_at
)
```

### After (13개 컬럼)
```sql
users (
    id, school, user_id, name, email, hashed_password, role,
    profile_info,           -- JSONB: student_id, department, admission_year, phone_number, profile_image
    account_status,         -- JSONB: is_active, is_first_login, last_login_at
    agreements_verification, -- JSONB: terms_agreed, privacy_agreed, etc, identity_verified, etc
    diagnosis_info,         -- JSONB: completed, completed_at, latest_score, test_count
    created_at, updated_at
)
```

## 🛠️ 마이그레이션 방법

### 1. 자동 마이그레이션 (권장)

#### API를 통한 마이그레이션
```bash
# 1. 마이그레이션 상태 확인
GET /admin/users/migration-status

# 2. 마이그레이션 실행
POST /admin/users/migrate

# 3. 결과 확인
GET /admin/users/migration-status
```

#### 응답 예시
```json
{
  "status": "success",
  "message": "150명의 사용자가 성공적으로 마이그레이션되었습니다.",
  "migrated_count": 150,
  "total_count": 150,
  "success_rate": "100.0%"
}
```

### 2. 수동 마이그레이션 (고급 사용자)

#### Alembic 마이그레이션
```bash
# 마이그레이션 실행
alembic upgrade head

# 특정 마이그레이션만 실행
alembic upgrade migrate_users_to_optimized
```

## 📋 호환성 보장

### Property 메서드를 통한 하위 호환성
기존 코드 수정 없이 동일하게 사용 가능:

```python
# 기존 방식 (여전히 작동)
user.student_id  # → user.profile_info.get("student_id")
user.is_active   # → user.account_status.get("is_active", True)
user.terms_agreed # → user.agreements_verification.get("terms_agreed", False)

# 새로운 방식 (권장)
user.set_profile_info(student_id="2024001234", department="간호학과")
user.set_account_status(is_active=True, is_first_login=False)
user.set_agreements(terms_agreed=True, privacy_agreed=True)
```

## 🔄 마이그레이션 단계별 가이드

### 1단계: 백업 생성
```sql
-- 자동으로 생성됨
CREATE TABLE users_backup AS SELECT * FROM users;
```

### 2단계: JSONB 컬럼 추가
```sql
ALTER TABLE users ADD COLUMN profile_info JSONB;
ALTER TABLE users ADD COLUMN account_status JSONB;
ALTER TABLE users ADD COLUMN agreements_verification JSONB;
ALTER TABLE users ADD COLUMN diagnosis_info JSONB;
```

### 3단계: 데이터 이전
```sql
UPDATE users SET 
    profile_info = jsonb_build_object(
        'student_id', student_id,
        'department', department,
        'admission_year', admission_year,
        'phone_number', phone_number,
        'profile_image', profile_image
    ),
    account_status = jsonb_build_object(
        'is_active', is_active,
        'is_first_login', is_first_login,
        'last_login_at', last_login_at::text
    ),
    -- ... 기타 필드들
```

### 4단계: 기존 컬럼 제거
```sql
ALTER TABLE users DROP COLUMN student_id;
ALTER TABLE users DROP COLUMN department;
-- ... 기타 불필요한 컬럼들
```

## 🔧 문제 해결

### 마이그레이션 실패 시
```bash
# 1. 롤백 실행
POST /admin/users/rollback-migration

# 2. 상태 확인
GET /admin/users/migration-status

# 3. 재시도
POST /admin/users/migrate
```

### 데이터 검증
```python
# Python 서비스 사용
from app.services.user_migration_service import UserMigrationService

migration_service = UserMigrationService(db)
result = migration_service.validate_migration()
print(result)
```

## ⚠️ 주의사항

1. **백업 필수**: 마이그레이션 전 반드시 데이터베이스 백업
2. **단계적 진행**: 한 번에 모든 사용자를 마이그레이션하지 말고 배치로 처리
3. **롤백 준비**: 문제 발생시 즉시 롤백할 수 있는 방법 준비
4. **서비스 중단**: 마이그레이션 중 서비스 일시 중단 고려

## 📈 성능 개선 효과

### 저장 공간
- **컬럼 수 감소**: 26개 → 13개 (50% 감소)
- **인덱스 최적화**: 필요한 필드에만 인덱스 적용
- **JSON 압축**: PostgreSQL JSONB의 압축 효과

### 쿼리 성능
- **SELECT 성능**: 불필요한 컬럼 스캔 감소
- **INSERT/UPDATE**: 컬럼 수 감소로 인한 성능 향상
- **JOIN 최적화**: 관련 데이터의 논리적 그룹화

### 유지보수성
- **스키마 단순화**: 관련 필드의 논리적 그룹화
- **확장성**: 새로운 필드 추가시 기존 구조 변경 최소화
- **일관성**: JSON 스키마를 통한 데이터 일관성 보장

## 🎯 다음 단계

1. **모니터링**: 마이그레이션 후 성능 모니터링
2. **최적화**: JSONB 인덱스 추가 최적화
3. **정리**: 불필요한 백업 테이블 정리
4. **문서화**: 새로운 스키마에 대한 개발자 문서 업데이트

---

**✅ 마이그레이션 완료 후 확인사항**
- [ ] 모든 사용자 데이터 정상 이전
- [ ] 기존 기능 정상 작동 확인
- [ ] 성능 테스트 완료
- [ ] 백업 테이블 정리 