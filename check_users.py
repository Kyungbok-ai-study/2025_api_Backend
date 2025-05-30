"""
사용자 목록 확인 스크립트
"""
from app.db.database import get_db
from app.models.user import User

def check_users():
    db = next(get_db())
    try:
        users = db.query(User).all()
        print(f"총 사용자 수: {len(users)}명")
        print("\n사용자 목록:")
        for user in users:
            print(f"  - ID: {user.id}")
            print(f"    Username: {user.username}")
            print(f"    Student ID: {user.student_id}")
            print(f"    Email: {user.email}")
            print(f"    Active: {user.is_active}")
            print()
    finally:
        db.close()

if __name__ == "__main__":
    check_users() 