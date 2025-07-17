# ai-content-marketing-tool/config.py

import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    """
    애플리케이션의 모든 설정값을 .env 파일로부터 읽어와 관리합니다.
    """
    # AWS
    AWS_ACCESS_KEY_ID = os.getenv("AWS_ACCESS_KEY_ID")
    AWS_SECRET_ACCESS_KEY = os.getenv("AWS_SECRET_ACCESS_KEY")
    AWS_REGION_NAME = os.getenv("AWS_REGION_NAME", "ap-northeast-2")
    IMAGE_GENERATION_REGION_NAME = os.getenv("IMAGE_GENERATION_REGION_NAME")

    # Application Secret Key
    SECRET_KEY = os.getenv("SECRET_KEY")

    # Database
    SQLALCHEMY_DATABASE_URI = os.getenv("DATABASE_URL")
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    PGVECTOR_DATABASE_URL = os.getenv("PGVECTOR_DATABASE_URL")
    DATABASE_URL = os.getenv("DATABASE_URL") # 중복될 수 있으나, 기존 코드 유지
    SQLALCHEMY_BINDS = {
        'mysql_db': SQLALCHEMY_DATABASE_URI, # 기존 주요 DB 연결
        'pgvector_db': PGVECTOR_DATABASE_URL # pgvector DB 연결
    }
    
    # Model IDs
    CLAUDE_MODEL_ID = os.getenv("CLAUDE_MODEL_ID")
    IMAGE_GENERATION_MODEL_ID = os.getenv("IMAGE_GENERATION_MODEL_ID")
    EMBEDDING_MODEL_ID = os.getenv("EMBEDDING_MODEL_ID")
    
    # S3 Bucket
    S3_BUCKET_NAME = os.getenv('S3_BUCKET_NAME')

    # File Paths
    IMAGE_SAVE_PATH = os.getenv('IMAGE_SAVE_PATH', 'generated_images')

    # Credentials
    ADMIN_USERNAME = os.getenv('ADMIN_USERNAME')
    CRAWLER_UPLOADER_USERNAME = os.getenv('CRAWLER_UPLOADER_USERNAME')

    @classmethod
    def validate(cls):
        """필수 환경 변수가 모두 설정되었는지 검증합니다."""
        required_vars = [
            "AWS_ACCESS_KEY_ID", 
            "AWS_SECRET_ACCESS_KEY", 
            "DATABASE_URL", 
            "SECRET_KEY", 
            "CLAUDE_MODEL_ID", 
            "IMAGE_GENERATION_MODEL_ID", 
            "IMAGE_GENERATION_REGION_NAME", 
            "EMBEDDING_MODEL_ID", 
            "PGVECTOR_DATABASE_URL",
            "S3_BUCKET_NAME",
            "IMAGE_SAVE_PATH"
        ]
        missing_vars = [var for var in required_vars if not getattr(cls, var)]
        if missing_vars:
            raise ValueError(f"다음 환경 변수가 .env 파일에 설정되지 않았습니다: {', '.join(missing_vars)}")

# 다른 파일에서 import해서 사용할 인스턴스
config = Config()