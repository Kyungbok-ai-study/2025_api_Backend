from app.db.database import SessionLocal
from app.models.user import User

db = SessionLocal()
try:
    user = db.query(User).filter(User.user_id == 'hgd123').first()
    if user:
        print(f'사용자 ID: {user.user_id}')
        print(f'이름: {user.name}')
        print(f'역할: {user.role}')
        print(f'활성화 상태: {user.is_active}')
        print(f'모든 필수 약관 동의 상태:')
        print(f'  - terms_agreed: {user.terms_agreed}')
        print(f'  - privacy_agreed: {user.privacy_agreed}')
        print(f'  - identity_verified: {user.identity_verified}')
        print(f'  - age_verified: {user.age_verified}')
    else:
        print('사용자를 찾을 수 없습니다.')
finally:
    db.close() 