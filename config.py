# ai-content-marketing-tool/config.py
import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    # AWS 관련 설정
    AWS_ACCESS_KEY_ID = os.getenv("AWS_ACCESS_KEY_ID")
    AWS_SECRET_ACCESS_KEY = os.getenv("AWS_SECRET_ACCESS_KEY")
    AWS_REGION_NAME = os.getenv("AWS_REGION_NAME", "ap-northeast-2")
    
    # LLM 관련 설정 (변수명 변경 및 Stable Diffusion 모델 ID 추가)
    SECRET_KEY = os.getenv("SECRET_KEY")
    
    # Bedrock Claude 모델 ID 
    BEDROCK_CLAUDE_SONNET_MODEL_ID = os.getenv("CLAUDE_MODEL_ID") 
    
    # Bedrock Stable Diffusion 모델 ID 
    IMAGE_GENERATION_MODEL_ID = os.getenv("IMAGE_GENERATION_MODEL_ID")
    IMAGE_GENERATION_REGION_NAME = os.getenv("IMAGE_GENERATION_REGION_NAME")

    # 관리자 계정 설정
    ADMIN_USERNAME = os.getenv('ADMIN_USERNAME')
    
    # 데이터베이스 설정
    SQLALCHEMY_DATABASE_URI = os.getenv("DATABASE_URL")
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    PGVECTOR_DATABASE_URL = os.getenv("PGVECTOR_DATABASE_URL")
    DATABASE_URL = os.getenv("DATABASE_URL") # 중복될 수 있으나, 기존 코드 유지
    SQLALCHEMY_BINDS = {
        'mysql_db': SQLALCHEMY_DATABASE_URI, # 기존 주요 DB 연결
        'pgvector_db': PGVECTOR_DATABASE_URL # pgvector DB 연결
    }
    
    # S3 Bucket 설정
    S3_BUCKET_NAME = os.getenv('S3_BUCKET_NAME', 'default-s3-bucket-name')
    CRAWLER_URLS_S3_KEY = os.getenv('CRAWLER_URLS_S3_KEY', 'system_config/crawler_urls.json')

    # 스케줄러 크롤러 설정
    CRAWLER_CONFIG_S3_KEY = os.environ.get('CRAWLER_CONFIG_S3_KEY', '_system_configs/crawler_urls.json')
    CRAWLER_CONFIG_BUCKET_NAME = os.environ.get('CRAWLER_CONFIG_BUCKET_NAME', S3_BUCKET_NAME) 
    SYSTEM_CRAWLER_USERNAME = os.environ.get('SYSTEM_CRAWLER_USERNAME', 'system_crawler') 

    # 이미지 저장 경로 
    IMAGE_SAVE_PATH = os.getenv('IMAGE_SAVE_PATH', 'generated_images') 

    @classmethod
    def validate(cls):
        required_vars = [
            "AWS_ACCESS_KEY_ID", 
            "AWS_SECRET_ACCESS_KEY", 
            "DATABASE_URL", 
            "SECRET_KEY", 
            "BEDROCK_CLAUDE_SONNET_MODEL_ID",
            "IMAGE_GENERATION_MODEL_ID", 
            "IMAGE_GENERATION_REGION_NAME", 
            "PGVECTOR_DATABASE_URL",
            "S3_BUCKET_NAME",
            "IMAGE_SAVE_PATH"
        ]
        missing_vars = [var for var in required_vars if not getattr(cls, var)]
        if missing_vars:
            raise ValueError(f"다음 환경 변수가 설정되지 않았습니다: {', '.join(missing_vars)}")
