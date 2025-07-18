# ai-content-marketing-tool/services/app_core/app_factory_utils.py

import os
import logging
import boto3
from flask import Flask
from flask_apscheduler import APScheduler
from .scheduler import initialize_scheduler_tasks
from extensions import db, login_manager, migrate, scheduler
from models import User
from config import Config
from services.utils.constants import PROMPT_TEMPLATE_RELATIVE_PATH, IMAGE_SAVE_PATH

logger = logging.getLogger(__name__)

# -------------------- 로깅 및 설정 --------------------
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

# -------------------- 외부 서비스 클라이언트 --------------------
def init_s3_client(app: Flask):
    """S3 클라이언트를 초기화하고 app.extensions에 등록합니다."""
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
        logger.error(f"S3 클라이언트 초기화 실패: {e}", exc_info=True)
        raise

def init_bedrock_client(app: Flask):
    """텍스트 생성용 Bedrock 클라이언트를 초기화하고 app.extensions에 등록합니다."""
    try:
        bedrock_runtime = boto3.client(
            service_name='bedrock-runtime',
            region_name=app.config['AWS_REGION_NAME'],
            aws_access_key_id=app.config['AWS_ACCESS_KEY_ID'],
            aws_secret_access_key=app.config['AWS_SECRET_ACCESS_KEY']
        )
        app.extensions['rag_bedrock_runtime'] = bedrock_runtime
        logger.info("Bedrock (text) client initialized successfully!")
        return bedrock_runtime
    except Exception as e:
        logger.error(f"Bedrock (text) client initialization failed: {e}")
        logger.warning("Application will start without Bedrock text service. Related features may not work.")
        return None

def init_image_bedrock_client(app: Flask):
    """이미지 생성용 Bedrock 클라이언트를 별도 리전으로 초기화하고 app.extensions에 등록합니다."""
    try:
        image_bedrock_client = boto3.client(
            service_name='bedrock-runtime',
            region_name=app.config['IMAGE_GENERATION_REGION_NAME'],
            aws_access_key_id=app.config['AWS_ACCESS_KEY_ID'],
            aws_secret_access_key=app.config['AWS_SECRET_ACCESS_KEY']
        )
        app.extensions['image_bedrock_client'] = image_bedrock_client
        logger.info("Bedrock (image) client initialized successfully!")
        return image_bedrock_client
    except Exception as e:
        logger.error(f"Bedrock (image) client initialization failed: {e}", exc_info=True)
        logger.warning("Application will start without Bedrock image service. Related features may not work.")
        return None

# -------------------- Flask 확장 및 DB --------------------
def init_app_extensions(app: Flask):
    """Flask 확장 기능들을 초기화합니다."""
    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)
    login_manager.login_view = 'auth_routes.login'

    @login_manager.user_loader
    def load_user(user_id):
        return db.session.get(User, int(user_id))
    scheduler.init_app(app)
    logger.info("Flask extensions initialized (including multiple DB binds).")

# -------------------- AI 서비스별 초기화 --------------------
def initialize_rag_system(app: Flask):
    """RAG 시스템을 초기화하고 app.extensions에 등록합니다."""
    from services.ai_rag.rag_system import init_rag_system
    bedrock_runtime_client = app.extensions.get('rag_bedrock_runtime')
    with app.app_context():
        rag_system = init_rag_system(bedrock_runtime_client)
        app.extensions['rag_system'] = rag_system
        logger.info("RAG system initialized.")
    return rag_system

def initialize_text_generator(app: Flask):
    """
    텍스트 생성기를 초기화하고 app.extensions에 등록합니다.
    """
    from services.generation.text_generator import create_text_generator
    from config import config
    rag_system = app.extensions.get('rag_system')
    bedrock_runtime_client = app.extensions.get('rag_bedrock_runtime')
    with app.app_context():
        text_generator = create_text_generator(bedrock_runtime_client, rag_system, app.root_path, config.CLAUDE_MODEL_ID)
        app.extensions['text_generator'] = text_generator
        logger.info("Text generator initialized.")
    return text_generator

def initialize_translation_generator(app: Flask):
    """
    번역 생성기를 초기화하고 app.extensions에 등록합니다.
    """
    from services.generation.translation_generator import create_translation_generator
    from services.utils.prompt_manager import PromptManager
    from services.utils.constants import PROMPT_TEMPLATE_RELATIVE_PATH
    from config import config
    text_generator = app.extensions.get('text_generator')
    with app.app_context():
        prompt_manager = PromptManager(app.root_path, PROMPT_TEMPLATE_RELATIVE_PATH)
        # text_provider는 이미 TextGenerator에서 config.CLAUDE_MODEL_ID로 생성됨
        text_provider = text_generator.provider_instances['text']
        translation_generator = create_translation_generator(prompt_manager, text_provider)
        app.extensions['translation_generator'] = translation_generator
        logger.info("Translation generator initialized.")
    return translation_generator

def initialize_image_generator(app: Flask):
    """
    이미지를 생성기를 초기화하고 app.extensions에 등록합니다.
    """
    from services.generation.image_generator import create_image_generator
    from services.utils.prompt_manager import PromptManager
    from services.utils.constants import PROMPT_TEMPLATE_RELATIVE_PATH
    from config import config
    image_bedrock_client = app.extensions.get('image_bedrock_client')
    s3_client = app.extensions.get('s3_client')
    with app.app_context():
        prompt_manager = PromptManager(app.root_path, PROMPT_TEMPLATE_RELATIVE_PATH)
        image_generator = create_image_generator(prompt_manager, image_bedrock_client, s3_client, config.IMAGE_GENERATION_MODEL_ID)
        app.extensions['image_generator'] = image_generator
        logger.info("Image generator initialized.")
    return image_generator

def initialize_ai_services(app: Flask):
    """
    모든 AI 서비스(RAG, 텍스트, 번역, 이미지 생성기)를 순서대로 초기화합니다.
    각 서비스는 app.extensions에 등록됩니다.
    반환값: dict (각 서비스 인스턴스)
    """
    rag_system = initialize_rag_system(app)
    text_generator = initialize_text_generator(app)
    translation_generator = initialize_translation_generator(app)
    image_generator = initialize_image_generator(app)
    logger.info("All AI services initialized.")
    return {
        'rag_system': rag_system,
        'text_generator': text_generator,
        'translation_generator': translation_generator,
        'image_generator': image_generator
    }

# -------------------- 기타 앱 초기화 --------------------
def register_app_blueprints(app: Flask):
    """애플리케이션 블루프린트들을 등록합니다."""
    from routes.auth_routes import auth_bp
    from routes.content_routes import content_bp
    from routes.knowledge_base_routes import knowledge_base_bp
    app.register_blueprint(auth_bp)
    app.register_blueprint(content_bp, url_prefix='/content')
    app.register_blueprint(knowledge_base_bp, url_prefix='/knowledge_base')
    logger.info("Blueprints registered.")

def create_image_dir_at_app_start(app: Flask):
    """애플리케이션 시작 시 이미지 저장 디렉토리를 생성합니다."""
    image_path = os.path.join(app.root_path, IMAGE_SAVE_PATH)
    os.makedirs(image_path, exist_ok=True)
    logger.info(f"Image save directory created at app start: {image_path}")

# -------------------- 전체 초기화 통합 함수 --------------------
def initialize_full_app(app: Flask):
    """
    Flask 애플리케이션의 모든 필수 초기화 단계를 순서대로 수행합니다.
    이 함수는 run.py와 같은 메인 진입점에서 create_app() 호출 후에 호출되어야 합니다.
    """
    configure_logging(app)
    logger_instance = app.logger
    init_s3_client(app)
    init_bedrock_client(app)
    init_image_bedrock_client(app)
    bedrock_runtime_client = app.extensions.get('rag_bedrock_runtime')
    initialize_ai_services(app)
    register_app_blueprints(app)
    initialize_scheduler_tasks(app)
    create_image_dir_at_app_start(app)
    logger_instance.info("Flask application fully initialized and ready to serve!")