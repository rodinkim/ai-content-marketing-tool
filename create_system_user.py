import os
from __init__ import create_app
from extensions import db
from models import User

def create_system_user():
    """
    시스템 크롤러 전용 계정이 없으면 생성한다.
    환경변수 SYSTEM_CRAWLER_USERNAME, SYSTEM_CRAWLER_PASSWORD 사용(없으면 기본값).
    """
    app = create_app()
    with app.app_context():
        username = app.config.get('SYSTEM_CRAWLER_USERNAME', 'system_crawler_default')
        password = os.environ.get('SYSTEM_CRAWLER_PASSWORD', 'supersecurepassword')
        existing_user = User.query.filter_by(username=username).first()
        if not existing_user:
            system_crawler = User(username=username, email=f"{username}@example.com")
            system_crawler.set_password(password)
            db.session.add(system_crawler)
            db.session.commit()
            print(f"시스템 크롤러 사용자 '{username}' (ID: {system_crawler.id}) 생성 완료.")
        else:
            print(f"시스템 크롤러 사용자 '{username}' (ID: {existing_user.id}) 이미 존재.")

if __name__ == "__main__":
    create_system_user()