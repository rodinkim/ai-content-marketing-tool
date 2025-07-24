import requests
from bs4 import BeautifulSoup
import logging
from trafilatura import extract
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, WebDriverException, InvalidSessionIdException
from ..web_utils import clean_beautynury_title
from ..driver_manager import ChromeDriverManager
from ..html_decoder import HTMLDecoder
from ..title_extractor import TitleExtractor
import urllib3
import requests.packages.urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
requests.packages.urllib3.disable_warnings(requests.packages.urllib3.exceptions.InsecureRequestWarning)

logger = logging.getLogger(__name__)

class BaseExtractor:
    """
    모든 웹 콘텐츠 추출기의 기본 클래스.
    - HTTP 요청, Trafilatura 기반 텍스트 추출, Selenium 드라이버 관리 등 공통 기능 제공
    """
    BASE_URL = ""
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
        self.driver_manager = ChromeDriverManager(headless=True)

    def _fetch_html(self, url: str, use_selenium: bool = False) -> str | None:
        """
        주어진 URL에서 HTML 콘텐츠를 가져와 적절히 디코딩합니다.
        Args:
            url (str): 대상 URL
            use_selenium (bool): Selenium 사용 여부
        Returns:
            str | None: HTML 문자열 또는 실패 시 None
        """
        driver = None
        try:
            if use_selenium:
                driver = self.driver_manager.get_driver()
                logger.info(f"Fetching {url} using Selenium...")
                driver.get(url)
                if "fashionbiz.co.kr" in url:
                    try:
                        WebDriverWait(driver, self.TIMEOUT).until(
                            EC.presence_of_element_located((By.CSS_SELECTOR, 'div.sc-53c9553f-0.ksjCKq'))
                        )
                        driver.implicitly_wait(2)
                        logger.debug(f"Fashionbiz specific element found on {url}.")
                    except TimeoutException:
                        logger.warning(f"Fashionbiz: Timeout waiting for specific element on {url}. Proceeding anyway.")
                    except (WebDriverException, Exception) as e:
                        logger.warning(f"Fashionbiz: Error waiting for element on {url}: {e}")
                return driver.page_source
            else:
                logger.info(f"Fetching {url} using requests...")
                response = requests.get(url, headers=self.HEADERS, timeout=self.TIMEOUT, verify=False)
                response.raise_for_status()
                forced_encoding = None
                for domain, encoding in self.FORCED_ENCODING_MAP.items():
                    if domain in url:
                        forced_encoding = encoding
                        break
                initial_encoding_attempt = forced_encoding if forced_encoding else response.encoding
                html_content = HTMLDecoder.decode_html_content(
                    content_bytes=response.content,
                    initial_encoding_hint=initial_encoding_attempt,
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
        except (WebDriverException, InvalidSessionIdException) as e:
            logger.error(f"Selenium WebDriver error for URL '{url}': {e}", exc_info=True)
            if isinstance(e, InvalidSessionIdException):
                logger.warning("Selenium session became invalid. Forcing driver re-initialization.")
                self.driver_manager.quit_driver()
            return None
        except Exception as e:
            logger.error(f"Error fetching HTML from '{url}': {e}", exc_info=True)
            return None
        finally:
            pass

    def _extract_main_content(self, html_content: str, url: str, custom_title_selectors: list = None) -> dict | None:
        """
        HTML에서 주요 텍스트 콘텐츠와 제목을 추출합니다.
        Trafilatura 기반 본문 추출, 실패 시 BeautifulSoup 폴백.
        Args:
            html_content (str): HTML 문자열
            url (str): 원본 URL
            custom_title_selectors (list, optional): 커스텀 제목 셀렉터
        Returns:
            dict | None: {'title': ..., 'content': ...} 또는 None
        """
        if not html_content:
            logger.warning(f"No HTML content provided for extraction from {url}.")
            return None
        effective_custom_selectors = custom_title_selectors if custom_title_selectors is not None else self.CUSTOM_TITLE_SELECTORS
        page_title = TitleExtractor.extract_title(html_content, custom_selectors=effective_custom_selectors)
        extracted_content_str = extract(html_content)
        if extracted_content_str:
            logger.info(f"Successfully extracted text using Trafilatura for {url}.")
            return {'title': page_title, 'content': str(extracted_content_str)}
        logger.warning(f"Trafilatura failed to extract content from {url}, trying BeautifulSoup fallback.")
        soup = BeautifulSoup(html_content, 'html.parser')
        paragraphs = soup.find_all(['p', 'h1', 'h2', 'h3', 'li'])
        text_content = []
        for p in paragraphs:
            for s in p(['script', 'style', 'noscript', 'meta']):
                s.extract()
            cleaned_text = p.get_text(separator=' ', strip=True)
            if cleaned_text:
                text_content.append(cleaned_text)
        full_text = ' '.join(text_content).strip()
        if full_text:
            logger.info(f"Successfully extracted text using BeautifulSoup fallback for {url}.")
            return {'title': page_title, 'content': str(full_text)}
        else:
            logger.warning(f"No significant text found from URL: {url} after all extraction attempts.")
            return None

    def get_list_page_urls(self, list_page_url: str) -> list[str]:
        """
        기사 목록 페이지에서 기사 URL 리스트를 추출합니다.
        하위 클래스에서 반드시 구현해야 합니다.
        """
        raise NotImplementedError("Subclasses must implement get_list_page_urls method.")

    def get_article_details(self, article_url: str) -> dict | None:
        """
        기사 상세 페이지에서 본문/제목 등 주요 정보를 추출합니다.
        Args:
            article_url (str): 기사 상세 URL
        Returns:
            dict | None: {'title': ..., 'content': ...} 또는 None
        """
        html_content = self._fetch_html(article_url)
        if not html_content:
            return None
        return self._extract_main_content(html_content, article_url)

    def __del__(self):
        if hasattr(self, 'driver_manager') and self.driver_manager:
            self.driver_manager.quit_driver()