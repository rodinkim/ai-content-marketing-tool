# __init__.py

from flask import Flask
# services.app_core 모듈에서 필요한 함수들을 임포트합니다.
from services.app_core.app_factory_utils import ( 
    load_app_config,
    init_app_extensions,
)

def create_app():
    """
    Flask 애플리케이션 인스턴스를 생성하고 필수 확장 기능을 초기화합니다.
    이 함수는 앱의 핵심적인 팩토리 역할을 수행합니다.
    """
    app = Flask(__name__)

    # 1. 앱 설정 로드
    load_app_config(app)

    # 2. Flask 확장 기능 초기화 (db, migrate, login_manager, scheduler의 init_app)
    init_app_extensions(app)
    
    return app