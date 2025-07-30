# services/web_crawling/web_content_extractor.py

import logging
from urllib.parse import urlparse

# 이 파일은 각 도메인에 맞는 추출기를 선택하고 호출하는 중앙 게이트웨이 역할을 합니다.
from .extractors.base_extractor import BaseExtractor
from .extractors.itworld import ITWorldExtractor
from .extractors.fashionbiz import FashionbizExtractor
from .extractors.hidoc import HidocExtractor
from .extractors.tlnews import TLNewsExtractor
from .extractors.beautynury import BeautynuryExtractor

logger = logging.getLogger(__name__)

# 각 도메인에 매핑되는 Extractor 클래스의 인스턴스를 정의합니다.
# 여기에 새로운 웹사이트 Extractor를 추가할 때마다 맵을 업데이트합니다.
_EXTRACTORS = {
    "itworld.co.kr": ITWorldExtractor(), 
    "fashionbiz.co.kr": FashionbizExtractor(),
    "news.hidoc.co.kr": HidocExtractor(), 
    "tlnews.co.kr": TLNewsExtractor(), 
    "beautynury.com": BeautynuryExtractor(), 
}

def get_specific_extractor(url: str) -> BaseExtractor | None:
    """
    주어진 URL에 해당하는 웹사이트 추출기 인스턴스를 반환합니다.
    """
    parsed_url = urlparse(url)
    domain = parsed_url.netloc 
    # www. 포함/미포함 등 다양한 도메인 케이스 대응
    possible_domains = [domain]
    if domain.startswith("www."):
        possible_domains.append(domain[4:]) 
    elif not domain.startswith("www.") and "." in domain:
        possible_domains.append("www." + domain)
    # 대소문자 구분 없이 매칭
    normalized_extractors = {k.lower(): v for k, v in _EXTRACTORS.items()}
    for d in possible_domains:
        extractor = normalized_extractors.get(d.lower())
        if extractor:
            return extractor
    return None # 일치하는 Extractor가 없으면 None 반환


def extract_text_from_url(url: str) -> dict | None:
    """
    주어진 URL에서 주요 텍스트 콘텐츠와 기사 제목을 추출합니다.
    URL 도메인에 따라 적절한 추출기를 선택하고, 해당 추출기의 상세 추출 메서드를 호출합니다.
    """
    extractor = get_specific_extractor(url)
    if extractor:
        logger.info(f"Attempting to extract details from {url} using {type(extractor).__name__}.")
        # 각 Extractor의 get_article_details 메서드 호출
        return extractor.get_article_details(url)
    else:
        logger.warning(f"No specific extractor found for URL: {url}. Falling back to generic extraction using BaseExtractor.")
        # 특정 추출기가 없으면 BaseExtractor의 범용 HTML 추출 사용
        base_extractor_instance = BaseExtractor()
        html_content = base_extractor_instance._fetch_html(url)
        if html_content:
            return base_extractor_instance._extract_main_content(html_content, url)
        return None