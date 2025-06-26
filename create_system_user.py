import os
from __init__ import create_app
from extensions import db
from models import User

app = create_app()

with app.app_context():
    # User 모델이 어떤 db 인스턴스를 사용하는지에 따라 다를 수 있습니다.
    # 현재는 db.Model에서 db 인스턴스를 가져오므로, db.session을 바로 사용합니다.
    system_crawler_username = app.config.get('SYSTEM_CRAWLER_USERNAME', 'system_crawler_default')
    existing_user = User.query.filter_by(username=system_crawler_username).first()

    if not existing_user:
        system_crawler = User(username=system_crawler_username, email=f"{system_crawler_username}@example.com")
        system_crawler.set_password(os.environ.get('SYSTEM_CRAWLER_PASSWORD', 'supersecurepassword')) # 안전한 비밀번호 설정 필요!
        db.session.add(system_crawler)
        db.session.commit()
        print(f"시스템 크롤러 사용자 '{system_crawler_username}' (ID: {system_crawler.id}) 생성 완료.")
    else:
        print(f"시스템 크롤러 사용자 '{system_crawler_username}' (ID: {existing_user.id}) 이미 존재.")