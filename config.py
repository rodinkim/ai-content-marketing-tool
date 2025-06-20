# ai-content-marketing-tool/config.py
import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    AWS_ACCESS_KEY_ID = os.getenv("AWS_ACCESS_KEY_ID")
    AWS_SECRET_ACCESS_KEY = os.getenv("AWS_SECRET_ACCESS_KEY")
    AWS_REGION_NAME = os.getenv("AWS_REGION_NAME", "ap-northeast-2")

    SECRET_KEY = os.getenv("SECRET_KEY")
    CLAUDE_MODEL_ID = os.getenv("CLAUDE_MODEL_ID", "anthropic.claude-3-5-sonnet-20240620-v1:0")
    ADMIN_USERNAME = os.getenv('ADMIN_USERNAME')
    S3_BUCKET_NAME = os.getenv('S3_BUCKET_NAME', 'default-s3-bucket-name')
    CRAWLER_URLS_S3_KEY = os.getenv('CRAWLER_URLS_S3_KEY', 'system_config/crawler_urls.json')

    SQLALCHEMY_DATABASE_URI = os.getenv("DATABASE_URL")
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    PGVECTOR_DATABASE_URL = os.getenv("PGVECTOR_DATABASE_URL")
    DATABASE_URL = os.getenv("DATABASE_URL")
    SQLALCHEMY_BINDS = {
        'mysql_db': SQLALCHEMY_DATABASE_URI, # 기존 주요 DB 연결
        'pgvector_db': PGVECTOR_DATABASE_URL # pgvector DB 연결
    }
    
    @classmethod
    def validate(cls):
        required_vars = ["AWS_ACCESS_KEY_ID", "AWS_SECRET_ACCESS_KEY", "DATABASE_URL", "SECRET_KEY", "CLAUDE_MODEL_ID", "PGVECTOR_DATABASE_URL"]
        missing_vars = [var for var in required_vars if not getattr(cls, var)]
        if missing_vars:
            raise ValueError(f"다음 환경 변수가 설정되지 않았습니다: {', '.join(missing_vars)}")
