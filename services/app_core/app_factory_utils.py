# ai-content-marketing-tool/services/app_core/app_factory_utils.py

import os
import logging
import boto3
from flask import Flask
from flask_apscheduler import APScheduler

from extensions import db, login_manager, migrate, scheduler
from models import User
from config import Config

logger = logging.getLogger(__name__)

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
    """
    Flask 애플리케이션에 S3 클라이언트를 초기화하고 app.extensions에 등록합니다.
    """
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
    db.init_app(app) # <-- 이 하나로 기존 DB와 pgvector DB 모두 초기화됩니다.
    migrate.init_app(app, db) # migrate도 하나의 db 객체에 연결
    login_manager.init_app(app)
    login_manager.login_view = 'auth_routes.login'

    @login_manager.user_loader
    def load_user(user_id):
        # User 모델은 기본 바인드(mysql_db)를 사용합니다.
        return db.session.get(User, int(user_id))
    
    scheduler.init_app(app)
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
    # services.ai_rag 모듈에서 임포트
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
    # services.web_crawling 모듈에서 임포트
    from services.web_crawling.crawler_tasks import perform_marketing_crawl_task

    if not scheduler.running:
        scheduler.start()
        logger.info("Scheduler started.")

    if scheduler.get_job('scheduled_marketing_crawl'):
        scheduler.remove_job('scheduled_marketing_crawl')
        logger.info("Existing 'scheduled_marketing_crawl' job removed.")

    scheduler.add_job(
        id='scheduled_marketing_crawl',
        func=lambda: app.app_context().push() or perform_marketing_crawl_task() or app.app_context().pop(),
        trigger='cron',
        day_of_week='fri',
        hour=13,
        minute=33,
        timezone='Asia/Seoul',
        misfire_grace_time=3600
    )
    logger.info("Scheduler: Weekly marketing news crawling job registered.")