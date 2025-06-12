# ai-content-marketing-tool/services/app_factory_utils.py

import os
import logging
import boto3
from flask import Flask # 타입 힌트를 위해 임포트
from flask_apscheduler import APScheduler # APScheduler 객체는 init_extensions에서 초기화되므로 여기서 임포트 필요 없음.
                                         # 하지만 schedule_tasks에서 Scheduler 객체가 필요하다면 임포트 고려.

# 확장 기능들을 임포트합니다.
from extensions import db, login_manager, migrate, scheduler

# 사용자 모델을 임포트합니다.
from models import User

# 설정 클래스를 임포트합니다.
from config import Config

logger = logging.getLogger(__name__) # 모듈 레벨 로거

def configure_logging(app: Flask):
    """애플리케이션 로깅을 설정합니다."""
    log_file_path = os.path.join(app.root_path, 'app.log') # app.root_path를 사용하여 경로 설정
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(name)s - %(message)s',
        handlers=[
            logging.FileHandler(log_file_path, encoding='utf-8'),
            logging.StreamHandler()
        ]
    )
    # Flask 앱의 기본 로거 설정
    # logging.getLogger('flask').setLevel(logging.INFO) # Flask 자체 로깅 레벨 설정 (선택 사항)
    # logging.getLogger('apscheduler').setLevel(logging.INFO) # APScheduler 로깅 레벨 설정 (선택 사항)

def load_app_config(app: Flask):
    """애플리케이션 설정을 로드하고 유효성을 검사합니다."""
    try:
        Config.validate()
        app.config.from_object(Config)
        app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(app.root_path, 'site.db')
        logger.info("Configuration loaded successfully.")
    except ValueError as e:
        logger.error(f"Configuration error: {e}")
        exit(1) # 설정 오류 시 앱 종료

def init_app_extensions(app: Flask):
    """Flask 확장 기능들을 초기화합니다."""
    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)
    login_manager.login_view = 'auth_routes.login'

    @login_manager.user_loader
    def load_user(user_id):
        return db.session.get(User, int(user_id))
    
    scheduler.init_app(app) # 스케줄러 초기화
    # scheduler.start() 는 create_app 밖에서 호출해야 스케줄러가 백그라운드 스레드에서 시작됩니다.
    # 하지만 Flask-APScheduler는 init_app 시 start_job_on_init=True (기본값) 이면 자동 시작될 수 있습니다.
    # 명시적 start()는 아래 schedule_tasks에서 할 예정입니다.

    logger.info("Flask extensions initialized.")

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
    from services.rag_system import init_rag_system
    from services.ai_service import init_ai_service

    with app.app_context(): # 앱 컨텍스트 내에서 실행되어야 함
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
    from services.crawler_tasks import perform_marketing_crawl_task

    # scheduler.start()는 init_app 이후에 호출되어야 합니다.
    # Flask-APScheduler는 init_app 시 start_job_on_init=True(기본값)이면 자동 시작되므로
    # 명시적 start() 호출이 필요 없을 수 있습니다.
    # 하지만 안정적인 시작을 위해 명시적으로 start()를 호출하는 것이 좋습니다.
    if not scheduler.running: # 스케줄러가 아직 시작되지 않았다면 시작
        scheduler.start()
        logger.info("Scheduler started.")

    # 기존 작업이 이미 등록되어 있을 경우를 대비하여 삭제 후 추가
    if scheduler.get_job('scheduled_marketing_crawl'):
        scheduler.remove_job('scheduled_marketing_crawl')
        logger.info("Existing 'scheduled_marketing_crawl' job removed.")

    scheduler.add_job(
        id='scheduled_marketing_crawl',
        func=lambda: app.app_context().push() or perform_marketing_crawl_task() or app.app_context().pop(),
        trigger='cron',
        day_of_week='thu',
        hour=10,
        minute=51,
        timezone='Asia/Seoul',
        misfire_grace_time=3600
    )
    logger.info("Scheduler: Weekly marketing news crawling job registered.")