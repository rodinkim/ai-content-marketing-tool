# ai-content-marketing-tool/services/app_core/app_factory_utils.py

import os
import logging
import boto3
from flask import Flask, current_app
from flask_apscheduler import APScheduler

from extensions import db, login_manager, migrate, scheduler
from models import User
from config import Config

logger = logging.getLogger(__name__)

# 기존의 개별 초기화 함수들은 그대로 유지 (다른 곳에서 호출될 수 있으므로)
def configure_logging(app: Flask):
    """애플리케이션 로깅을 설정합니다."""
    log_file_path = os.path.join(app.root_path, 'app.log')
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(name)s - %(message)s',
        handlers=[
            logging.FileHandler(log_file_path, encoding='utf-8'),
            logging.StreamHandler()
        ]
    )

def load_app_config(app: Flask):
    """애플리케이션 설정을 로드하고 유효성을 검사합니다."""
    try:
        Config.validate()
        app.config.from_object(Config)
        logger.info("Configuration loaded successfully.")
    except ValueError as e:
        logger.error(f"Configuration error: {e}")
        exit(1)

def init_s3_client(app: Flask):
    """Flask 애플리케이션에 S3 클라이언트를 초기화하고 app.extensions에 등록합니다."""
    try:
        s3_client = boto3.client(
            's3',
            region_name=app.config['AWS_REGION_NAME'],
            aws_access_key_id=app.config['AWS_ACCESS_KEY_ID'], 
            aws_secret_access_key=app.config['AWS_SECRET_ACCESS_KEY'] 
        )
        app.extensions['s3_client'] = s3_client
        logger.info("S3 client initialized and registered successfully.")
        return s3_client
    except Exception as e:
        logger.error(f"Failed to initialize S3 client: {e}", exc_info=True)
        raise

def init_app_extensions(app: Flask):
    """Flask 확장 기능들을 초기화합니다. SQLALCHEMY_BINDS 설정으로 여러 DB가 초기화됩니다."""
    db.init_app(app) 
    migrate.init_app(app, db)
    login_manager.init_app(app)
    login_manager.login_view = 'auth_routes.login'

    @login_manager.user_loader
    def load_user(user_id):
        return db.session.get(User, int(user_id))
    
    scheduler.init_app(app) # 스케줄러 자체는 여기서 확장으로 초기화
    logger.info("Flask extensions initialized (including multiple DB binds).")

def init_bedrock_client(app: Flask):
    """AWS Bedrock 런타임 클라이언트를 초기화하고 앱 확장에 등록합니다."""
    bedrock_runtime = None
    try:
        bedrock_runtime = boto3.client(
            service_name='bedrock-runtime',
            region_name=app.config['AWS_REGION_NAME'],
            aws_access_key_id=app.config['AWS_ACCESS_KEY_ID'],
            aws_secret_access_key=app.config['AWS_SECRET_ACCESS_KEY']
        )
        app.extensions['rag_bedrock_runtime'] = bedrock_runtime
        logger.info("Bedrock client initialized successfully!")
    except Exception as e:
        logger.error(f"Bedrock client initialization failed: {e}")
        logger.warning("Application will start without Bedrock service. Related features may not work.")
    return bedrock_runtime

def init_rag_and_ai_services(app: Flask, bedrock_runtime_client):
    """RAG 시스템 및 AI 서비스들을 초기화합니다."""
    from services.ai_rag.rag_system import init_rag_system 
    from services.ai_rag.ai_service import init_ai_service 

    with app.app_context():
        rag_system = init_rag_system(bedrock_runtime_client)
        init_ai_service(bedrock_runtime_client, rag_system)
    logger.info("RAG system and AI services initialized.")


def register_app_blueprints(app: Flask):
    """애플리케이션 블루프린트들을 등록합니다."""
    from routes.auth_routes import auth_bp
    from routes.content_routes import content_bp
    from routes.knowledge_base_routes import knowledge_base_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(content_bp, url_prefix='/content')
    app.register_blueprint(knowledge_base_bp, url_prefix='/knowledge_base')
    logger.info("Blueprints registered.")

def schedule_app_tasks(app: Flask):
    """애플리케이션 스케줄러 작업을 등록합니다."""
    from services.web_crawling.crawler_tasks import perform_marketing_crawl_task

    if not scheduler.running:
        scheduler.start()
        logger.info("Scheduler started.")

    if scheduler.get_job('scheduled_marketing_crawl'):
        scheduler.remove_job('scheduled_marketing_crawl')
        logger.info("Existing 'scheduled_marketing_crawl' job removed.")

    system_crawler_user = None
    with app.app_context():
        system_crawler_username = app.config.get('SYSTEM_CRAWLER_USERNAME', 'system_crawler_default')
        system_crawler_user = User.query.filter_by(username=system_crawler_username).first()
        
    if not system_crawler_user:
        logger.error(f"시스템 크롤러 사용자 '{system_crawler_username}'를 DB에서 찾을 수 없습니다. 스케줄링된 크롤링 작업을 등록할 수 없습니다.")
        logger.error("데이터 무결성을 위해 'system_crawler_default'와 같은 이름으로 User를 생성하거나 config에 올바른 사용자명을 설정해주세요.")
        return

    system_user_id_for_crawler = system_crawler_user.id
    logger.info(f"시스템 크롤러 User ID: {system_user_id_for_crawler} ({system_crawler_username})")


    scheduler.add_job(
        id='scheduled_marketing_crawl',
        func=lambda: app.app_context().push() or perform_marketing_crawl_task(system_user_id=system_user_id_for_crawler) or app.app_context().pop(),
        trigger='cron',
        day_of_week='tue',
        hour=11,
        minute=20,
        timezone='Asia/Seoul',
        misfire_grace_time=3600
    )
    logger.info("Scheduler: Weekly marketing news crawling job registered with system user ID.")

# --- 이미지 저장 디렉토리 생성 함수 ---
def create_image_dir_at_app_start(app: Flask):
    """애플리케이션 시작 시 이미지 저장 디렉토리를 생성합니다."""
    # IMAGE_SAVE_PATH는 config.py에 정의되어 있으므로, app.config에서 가져옵니다.
    image_path = os.path.join(app.root_path, app.config.get('IMAGE_SAVE_PATH', 'generated_images'))
    os.makedirs(image_path, exist_ok=True)
    logger.info(f"Image save directory created at app start: {image_path}")

# --- 앱의 모든 초기화 단계를 통합하는 함수 ---
def initialize_full_app(app: Flask):
    """
    Flask 애플리케이션의 모든 필수 초기화 단계를 순서대로 수행합니다.
    이 함수는 run.py와 같은 메인 진입점에서 create_app() 호출 후에 호출되어야 합니다.
    """
    # 1. 로깅 설정 (create_app에서 app.config 로드 후 app.logger 사용 가능)
    configure_logging(app)
    logger_instance = app.logger # 로거 인스턴스 가져오기

    # 2. S3 클라이언트 초기화
    init_s3_client(app)

    # 3. Bedrock 클라이언트 초기화
    init_bedrock_client(app)
    
    # Bedrock 클라이언트를 init_rag_and_ai_services에 전달 (app.extensions에서 가져오기)
    bedrock_runtime_client = app.extensions.get('rag_bedrock_runtime')

    # 4. RAG 시스템 및 AI 서비스 초기화
    init_rag_and_ai_services(app, bedrock_runtime_client)

    # 5. 블루프린트 등록
    register_app_blueprints(app)

    # 6. 스케줄러 작업 등록
    with app.app_context(): # schedule_app_tasks 내부에 app_context()가 있지만, 안전을 위해 밖에서도 한 번 더.
        schedule_app_tasks(app)

    # 7. 이미지 디렉토리 생성 등록
    create_image_dir_at_app_start(app)
    logger_instance.info("Image directory creation executed directly during app initialization.")

    logger_instance.info("Flask application fully initialized and ready to serve!")