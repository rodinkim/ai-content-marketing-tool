# ai-content-marketing-tool/config.py
import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    # AWS 관련 설정
    AWS_ACCESS_KEY_ID = os.getenv("AWS_ACCESS_KEY_ID")
    AWS_SECRET_ACCESS_KEY = os.getenv("AWS_SECRET_ACCESS_KEY")
    AWS_REGION_NAME = os.getenv("AWS_REGION_NAME", "ap-northeast-2")
    
    # LLM 관련 설정
    SECRET_KEY = os.getenv("SECRET_KEY")
    CLAUDE_MODEL_ID = os.getenv("CLAUDE_MODEL_ID", "anthropic.claude-3-5-sonnet-20240620-v1:0")
    
    # 관리자 계정 설정
    ADMIN_USERNAME = os.getenv('ADMIN_USERNAME')
    
    # 데이터베이스 설정
    SQLALCHEMY_DATABASE_URI = os.getenv("DATABASE_URL")
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    PGVECTOR_DATABASE_URL = os.getenv("PGVECTOR_DATABASE_URL")
    DATABASE_URL = os.getenv("DATABASE_URL")
    SQLALCHEMY_BINDS = {
        'mysql_db': SQLALCHEMY_DATABASE_URI, # 기존 주요 DB 연결
        'pgvector_db': PGVECTOR_DATABASE_URL # pgvector DB 연결
    }
    
    # S3 Bucket 설정
    S3_BUCKET_NAME = os.getenv('S3_BUCKET_NAME', 'default-s3-bucket-name')
    CRAWLER_URLS_S3_KEY = os.getenv('CRAWLER_URLS_S3_KEY', 'system_config/crawler_urls.json')

    # 스케줄러 크롤러 설정
    # 크롤러 설정 JSON 파일의 S3 키 (지식 베이스 버킷 내 별도 폴더)
    CRAWLER_CONFIG_S3_KEY = os.environ.get('CRAWLER_CONFIG_S3_KEY', '_system_configs/crawler_urls.json')
    # 크롤러 설정 파일이 있는 S3 버킷 이름 (기본은 지식 베이스 버킷과 동일)
    CRAWLER_CONFIG_BUCKET_NAME = os.environ.get('CRAWLER_CONFIG_BUCKET_NAME', S3_BUCKET_NAME) 

    # 스케줄러 크롤링 작업의 User ID를 귀속시킬 시스템 사용자명
    SYSTEM_CRAWLER_USERNAME = os.environ.get('SYSTEM_CRAWLER_USERNAME', 'system_crawler') 
    # 이 'system_crawler' 사용자는 반드시 DB의 'users' 테이블에 미리 생성되어 있어야 합니다.

    @staticmethod
    def validate():
        if not Config.S3_BUCKET_NAME:
            raise ValueError("S3_BUCKET_NAME is not set.")
        if not Config.CRAWLER_CONFIG_S3_KEY:
            raise ValueError("CRAWLER_CONFIG_S3_KEY is not set.")
        if not Config.SYSTEM_CRAWLER_USERNAME:
            raise ValueError("SYSTEM_CRAWLER_USERNAME is not set.")
        
    @classmethod
    def validate(cls):
        required_vars = ["AWS_ACCESS_KEY_ID", "AWS_SECRET_ACCESS_KEY", "DATABASE_URL", "SECRET_KEY", "CLAUDE_MODEL_ID", "PGVECTOR_DATABASE_URL"]
        missing_vars = [var for var in required_vars if not getattr(cls, var)]
        if missing_vars:
            raise ValueError(f"다음 환경 변수가 설정되지 않았습니다: {', '.join(missing_vars)}")
