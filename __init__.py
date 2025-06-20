# __init__.py

from flask import Flask
import os
# services.app_core 모듈에서 필요한 함수들을 임포트합니다.
from services.app_core.app_factory_utils import ( # <-- 경로 변경
    configure_logging,
    load_app_config,
    init_app_extensions,
    init_bedrock_client,
    init_rag_and_ai_services,
    register_app_blueprints,
    schedule_app_tasks,
    init_s3_client
)

def create_app():
    app = Flask(__name__)

    # 1. 로깅 설정
    configure_logging(app)
    logger = app.logger # Flask 앱 로거 사용

    # 2. 설정 로드
    load_app_config(app)

    # 3. Flask 확장 초기화
    init_app_extensions(app)

    # 4. Bedrock 클라이언트 초기화
    bedrock_runtime_client = init_bedrock_client(app)

    # 5. S3 클라이언트 초기화
    init_s3_client(app)

    # 6. RAG 시스템 및 AI 서비스 초기화
    init_rag_and_ai_services(app, bedrock_runtime_client) # 이 함수 내에서 RAGSystem이 pgvector를 사용하도록 변경 예정

    # 7. 블루프린트 등록
    register_app_blueprints(app)

    # 8. 스케줄러 작업 등록
    schedule_app_tasks(app)

    logger.info("Flask application initialized successfully!")
    
    return app