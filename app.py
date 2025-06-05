# ai-content-marketing-tool/app.py
from flask import Flask
import boto3
import os
import logging

# extensions.py에서 전역으로 선언된 Flask 확장 객체들을 임포트
from extensions import db, login_manager, migrate
# User 모델을 명시적으로 임포트 (순환 임포트 문제 해결)
from models import User 

# --- 로거 설정 ---
# 로그 파일 경로 설정 (app.py와 같은 디렉토리에 app.log 생성)
log_file_path = os.path.join(os.path.abspath(os.path.dirname(__file__)), 'app.log')

# 로거 기본 설정: 콘솔과 파일에 동시에 출력하도록 설정
logging.basicConfig(
    level=logging.INFO, # 로그 레벨 (INFO, DEBUG, WARNING, ERROR, CRITICAL)
    format='%(asctime)s - %(levelname)s - %(name)s - %(message)s', # 로그 포맷
    handlers=[
        logging.FileHandler(log_file_path, encoding='utf-8'), # 로그를 파일에 저장 (한글 깨짐 방지)
        logging.StreamHandler() # 로그를 콘솔에 출력
    ]
)
# app.py 모듈 전용 로거 인스턴스 생성
logger = logging.getLogger(__name__)

def create_app():
    app = Flask(__name__)

    # --- 설정 적용 ---
    from config import Config
    try:
        Config.validate() # config.py의 환경 변수 유효성 검사
        app.config.from_object(Config) # Config 객체로부터 앱 설정 로드

        # SQLite 데이터베이스 경로를 앱 루트에 명확히 지정
        # 이 코드는 config.py의 SQLALCHEMY_DATABASE_URI 설정을 덮어씁니다.
        app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(app.root_path, 'site.db')
        
    except ValueError as e:
        logger.error(f"환경 설정 오류: {e}") # 환경 설정 오류 발생 시 로깅
        exit(1) # 애플리케이션 종료

    # --- 데이터베이스 초기화 (app 객체에 바인딩) ---
    db.init_app(app)

    # --- Flask-Migrate 초기화 (db 객체와 app 연결) ---
    migrate.init_app(app, db)

    # --- Flask-Login 초기화 (app 객체에 바인딩) ---
    login_manager.init_app(app)
    login_manager.login_view = 'main.login' # 로그인 페이지 뷰 설정

    # --- 사용자 로더 함수 정의 (Flask-Login 필요) ---
    @login_manager.user_loader
    def load_user(user_id):
        # User 모델은 이제 상단에서 정상적으로 임포트됩니다.
        # db.session을 직접 사용하여 사용자 로드
        return db.session.get(User, int(user_id))

    # --- Bedrock 클라이언트 초기화 ---
    bedrock_runtime = None
    try:
        bedrock_runtime = boto3.client(
            service_name='bedrock-runtime',
            region_name=Config.AWS_REGION_NAME,
            aws_access_key_id=Config.AWS_ACCESS_KEY_ID,
            aws_secret_access_key=Config.AWS_SECRET_ACCESS_KEY
        )
        logger.info("Flask 앱: Bedrock 클라이언트 초기화 성공!")
    except Exception as e:
        logger.error(f"Flask 앱: Bedrock 클라이언트 초기화 실패: {e}")
        logger.warning("애플리케이션이 Bedrock 서비스 없이 시작됩니다. 관련 기능이 작동하지 않을 수 있습니다.")

    # --- RAG 시스템 인스턴스 초기화 (Bedrock 클라이언트 주입) ---
    # rag_system 모듈에서 초기화 함수 임포트
    from rag_system import init_rag_system
    # Bedrock 클라이언트를 RAG 시스템에 주입하여 초기화
    rag_system = init_rag_system(bedrock_runtime) 

    # --- AI 서비스 모듈 초기화 (Bedrock 클라이언트와 RAG 시스템 주입) ---
    # services.ai_service 모듈에서 init_ai_service 함수를 임포트
    from services.ai_service import init_ai_service 
    # init_ai_service 함수를 호출하여 AIContentGenerator 인스턴스를 초기화
    # 이때 Bedrock 클라이언트와 RAG 시스템 인스턴스를 주입
    init_ai_service(bedrock_runtime, rag_system) 

    # --- DB 모델 임포트 (Flask-Migrate가 모델을 찾을 수 있도록) ---
    # models.py를 임포트하여 SQLAlchemy가 모든 모델 클래스를 인식하게 합니다.
    import models 

    # --- 라우트 등록 ---
    from routes import main_bp
    app.register_blueprint(main_bp)

    return app

# --- 메인 실행 블록 ---
if __name__ == '__main__':
    app = create_app()
    app.run(debug=True) # 개발 모드로 애플리케이션 실행