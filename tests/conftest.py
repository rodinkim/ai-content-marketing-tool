import pytest
import os
import sys
from unittest.mock import Mock

# 프로젝트 루트 디렉토리를 Python 경로에 추가
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Flask 앱 컨텍스트를 위한 설정
@pytest.fixture(scope="session")
def app():
    """Flask 앱 인스턴스 생성"""
    from flask import Flask
    from config import Config
    
    app = Flask(__name__)
    app.config.from_object(Config)
    
    # 테스트용 설정
    app.config['TESTING'] = True
    app.config['WTF_CSRF_ENABLED'] = False
    
    return app

@pytest.fixture
def client(app):
    """테스트 클라이언트 생성"""
    return app.test_client()

@pytest.fixture
def runner(app):
    """테스트 러너 생성"""
    return app.test_cli_runner()

# Mock AWS 서비스들
@pytest.fixture
def mock_bedrock_client():
    """Mock Bedrock 클라이언트"""
    return Mock()

@pytest.fixture
def mock_s3_client():
    """Mock S3 클라이언트"""
    return Mock()

@pytest.fixture
def mock_image_bedrock_client():
    """Mock 이미지 Bedrock 클라이언트"""
    return Mock()

# Mock 데이터베이스
@pytest.fixture
def mock_db():
    """Mock 데이터베이스"""
    return Mock()

# Mock RAG 시스템
@pytest.fixture
def mock_rag_system():
    """Mock RAG 시스템"""
    mock_rag = Mock()
    mock_rag.retrieve.return_value = ["테스트 문서 1", "테스트 문서 2"]
    return mock_rag

# 테스트용 사용자 데이터
@pytest.fixture
def test_user_data():
    """테스트용 사용자 데이터"""
    return {
        "username": "testuser",
        "email": "test@example.com",
        "password": "testpassword123"
    }

# 테스트용 콘텐츠 데이터
@pytest.fixture
def test_content_data():
    """테스트용 콘텐츠 데이터"""
    return {
        "topic": "AI 마케팅",
        "industry": "IT",
        "content_type": "blog",
        "blog_style": "추천/리스트 글",
        "target_audience": "마케터",
        "key_points": "AI 활용, 효율성, ROI",
        "tone": "전문적",
        "length_option": "medium",
        "seo_keywords": "AI 마케팅, 디지털 마케팅"
    }

# 테스트용 이미지 데이터
@pytest.fixture
def test_image_data():
    """테스트용 이미지 데이터"""
    return {
        "topic": "AI 마케팅 이미지",
        "industry": "IT",
        "content_type": "sns",
        "target_audience": "마케터",
        "brand_style_tone": "전문적",
        "product_category": "소프트웨어",
        "ad_purpose": "브랜드 인지도",
        "cut_count": 1,
        "aspect_ratio_sns": "1:1"
    } 