# services/web_crawling/web_content_extractor.py (최종 수정)

import logging
from urllib.parse import urlparse

# 새로 만든 Extractor 클래스들을 임포트합니다.
# 이 파일은 이제 각 도메인에 맞는 추출기를 선택하고 호출하는 중앙 게이트웨이 역할을 합니다.
from .extractors.base_extractor import BaseExtractor # BaseExtractor는 일반적인 추출기로도 사용될 수 있음
from .extractors.itworld import ITWorldExtractor
from .extractors.fashionbiz import FashionbizExtractor
from .extractors.ten_thousand_recipe import TenThousandRecipeExtractor
from .extractors.hidoc import HidocExtractor
from .extractors.tlnews import TLNewsExtractor
from .extractors.beautynury import BeautynuryExtractor

logger = logging.getLogger(__name__)

# 각 도메인에 매핑되는 Extractor 클래스의 인스턴스를 정의합니다.
# 여기에 새로운 웹사이트 Extractor를 추가할 때마다 맵을 업데이트합니다.
_EXTRACTORS = {
    "itworld.co.kr": ITWorldExtractor(), # 'www.' 제거
    "fashionbiz.co.kr": FashionbizExtractor(),
    "10000recipe.com": TenThousandRecipeExtractor(), # 'www.' 제거
    "news.hidoc.co.kr": HidocExtractor(), # 서브도메인 포함
    "tlnews.co.kr": TLNewsExtractor(), # 'www.' 제거
    "beautynury.com": BeautynuryExtractor(), # 'www.' 제거
}

def get_specific_extractor(url: str) -> BaseExtractor | None:
    """주어진 URL에 해당하는 웹사이트 추출기 인스턴스를 반환합니다."""
    parsed_url = urlparse(url)
    domain = parsed_url.netloc # 예: "www.itworld.co.kr", "fashionbiz.co.kr"

    # 딕셔너리 키와 일치시키기 위한 정규화된 도메인 리스트를 만듭니다.
    possible_domains = [domain]
    if domain.startswith("www."):
        possible_domains.append(domain[4:]) # "www.itworld.co.kr" -> "itworld.co.kr" 추가
    elif not domain.startswith("www.") and "." in domain:
        # "itworld.co.kr" -> "www.itworld.co.kr" 을 추가할 필요가 있을 수도 있습니다.
        # 하지만 일반적으로 www.를 제거한 형태를 키로 쓰는 것이 좋습니다.
        possible_domains.append("www." + domain)
    
    # _EXTRACTORS 딕셔너리의 키를 미리 소문자로 변환하여 비교합니다.
    # 이렇게 하면 대소문자 문제도 방지할 수 있습니다.
    normalized_extractors = {k.lower(): v for k, v in _EXTRACTORS.items()}

    for d in possible_domains:
        extractor = normalized_extractors.get(d.lower()) # 소문자로 변환하여 찾기
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
        # 각 Extractor의 get_article_details 메서드를 호출하여 상세 정보를 가져옵니다.
        # 레시피나 일반 기사 등, 각 Extractor의 반환 형식에 따라 다르게 처리해야 할 수 있습니다.
        # 여기서는 반환 타입을 dict | None으로 통일합니다.
        return extractor.get_article_details(url)
    else:
        logger.warning(f"No specific extractor found for URL: {url}. Falling back to generic extraction using BaseExtractor.")
        # 특정 추출기가 없는 경우, BaseExtractor의 범용 HTML 추출 및 콘텐츠 추출 로직을 사용합니다.
        base_extractor_instance = BaseExtractor()
        html_content = base_extractor_instance._fetch_html(url)
        if html_content:
            return base_extractor_instance._extract_main_content(html_content, url)
        return None