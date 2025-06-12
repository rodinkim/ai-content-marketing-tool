# ai-content-marketing-tool/__init__.py

def create_app():
    from flask import Flask
    import boto3
    import os
    import logging
    from flask_apscheduler import APScheduler # Flask-APScheduler 임포트 (함수 내부)

    # 확장 기능 객체들을 임포트합니다.
    from extensions import db, login_manager, migrate, scheduler # scheduler 임포트 추가
    # 사용자 모델을 임포트합니다.
    from models import User 

    # --- 로거 설정 ---
    log_file_path = os.path.join(os.path.abspath(os.path.dirname(__file__)), 'app.log')
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(name)s - %(message)s',
        handlers=[
            logging.FileHandler(log_file_path, encoding='utf-8'),
            logging.StreamHandler()
        ]
    )
    logger = logging.getLogger(__name__)

    app = Flask(__name__)

    # --- 설정 적용 ---
    from config import Config
    try:
        Config.validate()
        app.config.from_object(Config) 
        app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(app.root_path, 'site.db')
    except ValueError as e:
        logger.error(f"환경 설정 오류: {e}")
        exit(1)

    # --- 데이터베이스 및 Flask 확장 초기화 ---
    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)
    login_manager.login_view = 'auth_routes.login' 

    @login_manager.user_loader
    def load_user(user_id):
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
        app.extensions['rag_bedrock_runtime'] = bedrock_runtime 
        logger.info("Flask 앱: Bedrock 클라이언트 초기화 성공!")
    except Exception as e:
        logger.error(f"Flask 앱: Bedrock 클라이언트 초기화 실패: {e}")
        logger.warning("애플리케이션이 Bedrock 서비스 없이 시작됩니다. 관련 기능이 작동하지 않을 수 있습니다.")

    # --- RAG 시스템 및 AI 서비스 초기화 ---
    from services.rag_system import init_rag_system 
    from services.ai_service import init_ai_service 

    with app.app_context():
        rag_system = init_rag_system(bedrock_runtime)
        init_ai_service(bedrock_runtime, rag_system)

    # --- 라우트 블루프린트 등록 ---
    from routes.auth_routes import auth_bp
    from routes.content_routes import content_bp
    from routes.knowledge_base_routes import knowledge_base_bp 

    app.register_blueprint(auth_bp)
    app.register_blueprint(content_bp, url_prefix='/content')
    app.register_blueprint(knowledge_base_bp, url_prefix='/knowledge_base')
    
    # --- 스케줄러 초기화 및 작업 등록 ---
    scheduler.init_app(app) 
    scheduler.start() 

    from services.crawler_tasks import perform_marketing_crawl_task 

    scheduler.add_job(
        id='scheduled_marketing_crawl', 
        func=lambda: app.app_context().push() or perform_marketing_crawl_task() or app.app_context().pop(),
        trigger='cron', 
        day_of_week='thu', 
        hour=10, 
        minute=25, 
        timezone='Asia/Seoul', 
        misfire_grace_time=3600 
    )
    logger.info("스케줄러: 주간 마케팅 뉴스 크롤링 작업이 등록되었습니다.") 

    return app