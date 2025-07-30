# ai-content-marketing-tool/services/web_crawling/__init__.py

"""
웹 크롤링 모듈들

이 패키지는 다음과 같은 웹 크롤링 관련 기능들을 포함합니다:

- crawler_tasks.py: 크롤링 작업 관리 및 실행
- web_utils.py: 웹 크롤링 유틸리티 함수들
- web_content_extractor.py: 웹 페이지 콘텐츠 추출
- title_extractor.py: 웹 페이지 제목 추출
- html_decoder.py: HTML 디코딩 및 정제
- driver_manager.py: 웹 드라이버 관리
- extractors/: 특정 사이트별 콘텐츠 추출기들
"""

from .crawler_tasks import perform_marketing_crawl_task
from .web_utils import sanitize_filename, decode_html_content, clean_beautynury_title
from .web_content_extractor import get_specific_extractor, extract_text_from_url
from .title_extractor import TitleExtractor
from .html_decoder import HTMLDecoder
from .driver_manager import ChromeDriverManager

__all__ = [
    'perform_marketing_crawl_task',
    'sanitize_filename',
    'decode_html_content',
    'clean_beautynury_title',
    'get_specific_extractor',
    'extract_text_from_url',
    'TitleExtractor',
    'HTMLDecoder',
    'ChromeDriverManager'
]
