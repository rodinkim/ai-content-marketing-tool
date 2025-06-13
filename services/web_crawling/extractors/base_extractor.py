import requests
from bs4 import BeautifulSoup
import logging
from trafilatura import extract

from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, WebDriverException, InvalidSessionIdException

from ..web_utils import clean_beautynury_title # BeautynuryExtractor에서 사용
from ..driver_manager import ChromeDriverManager
from ..html_decoder import HTMLDecoder
from ..title_extractor import TitleExtractor # 새로 만든 TitleExtractor 임포트

import urllib3
import requests.packages.urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
requests.packages.urllib3.disable_warnings(requests.packages.urllib3.exceptions.InsecureRequestWarning)

logger = logging.getLogger(__name__)

class BaseExtractor:
    """
    모든 웹 콘텐츠 추출기의 기본 클래스입니다.
    공통 HTTP 요청, Trafilatura 기반 텍스트 추출, Selenium 드라이버 설정 등을 처리합니다.
    """
    BASE_URL = "" # 각 하위 클래스에서 오버라이드
    HEADERS = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    TIMEOUT = 15
    FORCED_ENCODING_MAP = {
        "beautynury.com": "utf-8",
        "news.hidoc.co.kr": "utf-8",
    }

    CUSTOM_TITLE_SELECTORS = None
    
    def __init__(self):
        # HTMLDecoder는 정적 메서드를 사용하므로 인스턴스 변수로 둘 필요는 없습니다.
        self.driver_manager = ChromeDriverManager(headless=True)


    def _fetch_html(self, url: str, use_selenium: bool = False) -> str | None:
        """주어진 URL에서 HTML 콘텐츠를 가져와 적절히 디코딩합니다."""
        # driver 변수를 밖으로 빼내어 finally에서 사용 가능하도록 함
        driver = None 
        try:
            if use_selenium:
                driver = self.driver_manager.get_driver() # 드라이버 인스턴스 가져오기
                logger.info(f"Fetching {url} using Selenium...")
                driver.get(url)
                
                # 특정 사이트별 Selenium 대기 로직 (여기 두는 것이 적합)
                if "fashionbiz.co.kr" in url:
                    try:
                        WebDriverWait(driver, self.TIMEOUT).until(
                            EC.presence_of_element_located((By.CSS_SELECTOR, 'div.sc-53c9553f-0.ksjCKq'))
                        )
                        driver.implicitly_wait(2) # 짧은 추가 대기
                        logger.debug(f"Fashionbiz specific element found on {url}.")
                    except TimeoutException:
                        logger.warning(f"Fashionbiz: Timeout waiting for specific element on {url}. Proceeding anyway.")
                    except (WebDriverException, Exception) as e: # 좀 더 포괄적인 예외 처리
                        logger.warning(f"Fashionbiz: Error waiting for element on {url}: {e}")
                
                return driver.page_source
            else: # Requests 사용
                logger.info(f"Fetching {url} using requests...")
                response = requests.get(url, headers=self.HEADERS, timeout=self.TIMEOUT, verify=False)
                response.raise_for_status() # HTTP 에러 발생 시 예외
                
                # HTMLDecoder를 사용하여 콘텐츠 디코딩
                forced_encoding = None
                for domain, encoding in self.FORCED_ENCODING_MAP.items():
                    if domain in url:
                        forced_encoding = encoding
                        break

                # 강제 인코딩이 있다면 response.encoding보다 먼저 시도하도록 전달
                # 그렇지 않다면 response.encoding을 첫 번째 시도 인코딩으로 전달
                initial_encoding_attempt = forced_encoding if forced_encoding else response.encoding

                html_content = HTMLDecoder.decode_html_content(
                    content_bytes=response.content,
                    initial_encoding_hint=initial_encoding_attempt, # 첫 번째 시도 인코딩
                    apparent_encoding=response.apparent_encoding,
                    url=url
                )
                
                if html_content is None:
                    logger.error(f"Failed to decode HTML content for '{url}' after all attempts in HTMLDecoder. Returning None.")
                    return None
                
                return html_content

        except requests.exceptions.RequestException as e:
            logger.error(f"Network or HTTP error fetching URL '{url}': {e}")
            return None
        except (WebDriverException, InvalidSessionIdException) as e: # Selenium 관련 오류 처리 강화
            logger.error(f"Selenium WebDriver error for URL '{url}': {e}", exc_info=True)
            # 드라이버 세션이 유효하지 않은 경우, 드라이버를 재초기화하도록 관리자에 알림
            if isinstance(e, InvalidSessionIdException):
                logger.warning("Selenium session became invalid. Forcing driver re-initialization.")
                self.driver_manager.quit_driver() # 현재 드라이버 인스턴스 강제 종료
            return None
        except Exception as e:
            logger.error(f"Error fetching HTML from '{url}': {e}", exc_info=True)
            return None
        finally:
            # 드라이버는 BaseExtractor 객체가 소멸될 때 ChromeDriverManager에 의해 종료됩니다.
            # 개별 _fetch_html 호출 시마다 종료하지 않습니다.
            pass


    def _extract_main_content(self, html_content: str, url: str, custom_title_selectors: list = None) -> dict | None:
        """
        주어진 HTML에서 주요 텍스트 콘텐츠와 제목을 추출합니다.
        Trafilatura 기반의 본문 추출을 시도하고, 실패 시 BeautifulSoup 폴백을 사용합니다.
        """
        if not html_content:
            logger.warning(f"No HTML content provided for extraction from {url}.")
            return None

        # 제목 추출
        # 인스턴스에 정의된 custom_title_selectors가 있다면 이를 사용하고,
        # 메서드 인자로 전달된 custom_title_selectors가 있다면 이를 오버라이드합니다.
        # 이렇게 하면 BaseExtractor의 기본값 또는 하위 클래스의 재정의된 값을 사용할 수 있습니다.
        effective_custom_selectors = custom_title_selectors if custom_title_selectors is not None else self.CUSTOM_TITLE_SELECTORS
        page_title = TitleExtractor.extract_title(html_content, custom_selectors=effective_custom_selectors)
        
        extracted_content_str = extract(html_content) # Trafilatura 시도
        
        if extracted_content_str:
            logger.info(f"Successfully extracted text using Trafilatura for {url}.")
            return {'title': page_title, 'content': str(extracted_content_str)}
        
        logger.warning(f"Trafilatura failed to extract content from {url}, trying BeautifulSoup fallback.")
        
        # Trafilatura 실패 시 BeautifulSoup 폴백 로직
        soup = BeautifulSoup(html_content, 'html.parser')
        paragraphs = soup.find_all(['p', 'h1', 'h2', 'h3', 'li'])
        text_content = []
        for p in paragraphs:
            # 스크립트, 스타일 태그 내부의 텍스트는 제외
            # 일부 태그는 get_text() 시 줄바꿈이 필요한 경우도 있습니다.
            # 하지만 여기서는 간단하게 공백으로 구분합니다.
            for s in p(['script', 'style', 'noscript', 'meta']): # 불필요한 태그 제거
                s.extract()
            cleaned_text = p.get_text(separator=' ', strip=True)
            if cleaned_text: # 빈 문자열이 아닌 경우에만 추가
                text_content.append(cleaned_text)
        
        full_text = ' '.join(text_content).strip()
        
        if full_text:
            logger.info(f"Successfully extracted text using BeautifulSoup fallback for {url}.")
            return {'title': page_title, 'content': str(full_text)}
        else:
            logger.warning(f"No significant text found from URL: {url} after all extraction attempts.")
            return None

    def get_list_page_urls(self, list_page_url: str) -> list[str]:
        raise NotImplementedError("Subclasses must implement get_list_page_urls method.")

    def get_article_details(self, article_url: str) -> dict | None:
        # 이 메서드는 이제 custom_title_selectors를 직접 전달할 수 없으므로,
        # BaseExtractor의 self.CUSTOM_TITLE_SELECTORS 또는 하위 클래스에서 정의된 값을 사용하게 됩니다.
        # 만약 get_article_details에서 custom_title_selectors를 동적으로 전달해야 한다면,
        # get_article_details의 시그니처를 변경해야 합니다.
        html_content = self._fetch_html(article_url)
        if not html_content:
            return None
        return self._extract_main_content(html_content, article_url)

    def __del__(self):
        if hasattr(self, 'driver_manager') and self.driver_manager:
            self.driver_manager.quit_driver()