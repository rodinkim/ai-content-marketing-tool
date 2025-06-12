import requests
from bs4 import BeautifulSoup
import logging
from trafilatura import extract
import re
import os
import chardet

# Selenium 임포트
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, WebDriverException

# web_utils 모듈 임포트 (BaseExtractor에서 decode_html_content는 직접 사용하지 않음)
from ..web_utils import clean_beautynury_title # BeautynuryExtractor에서 사용

# --- requests의 SSL 검증을 전역적으로 비활성화 (매우 위험, 임시용) ---
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

    def __init__(self):
        # Selenium 드라이버 경로 설정
        current_file_abs_path = os.path.abspath(__file__)
        current_dir_abs_path = os.path.dirname(current_file_abs_path)
        # extractors 폴더 -> web_crawling -> services -> ai-content-marketing-tool (프로젝트 루트)
        project_root_abs_path = os.path.abspath(os.path.join(current_dir_abs_path, '..', '..', '..'))
        self.chrome_driver_path = os.path.join(project_root_abs_path, 'drivers', 'chromedriver.exe')


    def _fetch_html(self, url: str, use_selenium: bool = False) -> str | None:
        """주어진 URL에서 HTML 콘텐츠를 가져와 적절히 디코딩합니다."""
        driver = None 
        try:
            if use_selenium:
                chrome_options = Options()
                chrome_options.add_argument("--headless")
                chrome_options.add_argument("--no-sandbox")
                chrome_options.add_argument("--disable-dev-shm-usage")
                chrome_options.add_argument(f"user-agent={self.HEADERS['User-Agent']}")
                chrome_options.add_experimental_option('excludeSwitches', ['enable-logging'])
                chrome_options.add_argument("--ignore-certificate-errors")
                chrome_options.add_argument("--allow-insecure-localhost")
                chrome_options.add_argument("--ignore-ssl-errors")
                chrome_options.add_argument("--disable-features=NetworkService")

                service = Service(executable_path=self.chrome_driver_path)
                driver = webdriver.Chrome(service=service, options=chrome_options)

                logger.info(f"Fetching {url} using Selenium...")
                driver.get(url)
                
                if "fashionbiz.co.kr" in url:
                    try:
                        WebDriverWait(driver, self.TIMEOUT).until(
                            EC.presence_of_element_located((By.CSS_SELECTOR, 'div.sc-53c9553f-0.ksjCKq'))
                        )
                        driver.implicitly_wait(2)
                    except TimeoutException:
                        logger.warning(f"Fashionbiz: Timeout waiting for specific element on {url}. Proceeding anyway.")
                    except Exception as e:
                        logger.warning(f"Fashionbiz: Error waiting for element on {url}: {e}")
                
                return driver.page_source
            else: # Requests 사용
                logger.info(f"Fetching {url} using requests...")
                response = requests.get(url, headers=self.HEADERS, timeout=self.TIMEOUT, verify=False)
                response.raise_for_status() # HTTP 에러 발생 시 예외

                # 디코딩 시도 목록 (우선순위: 명시적 강제 -> requests.encoding -> apparent_encoding -> chardet -> 하드코딩 폴백)
                decoding_attempts = []
                
                # 1. 특정 사이트별 명시적 강제 인코딩 (문제 해결 경험 기반)
                if "beautynury.com" in url or "news.hidoc.co.kr" in url:
                    decoding_attempts.append(('utf-8', 'forced')) # Beautynury와 HiDoc은 UTF-8로 강제 시도

                # 2. requests의 response.encoding (HTTP 헤더 기반 추론)
                #    requests가 추론한 인코딩이 있다면 시도 목록에 추가
                if response.encoding and response.encoding.lower() not in [enc.lower() for enc, _ in decoding_attempts]:
                    decoding_attempts.append((response.encoding, 'requests_inferred'))
                #    만약 requests가 인코딩을 None으로 추론했거나, 이미 강제 인코딩을 시도했다면,
                #    여기서도 UTF-8을 기본으로 한 번 더 시도할 수 있습니다.
                elif not response.encoding and 'utf-8' not in [enc.lower() for enc, _ in decoding_attempts]:
                    decoding_attempts.append(('utf-8', 'default_utf8'))

                # 3. requests의 response.apparent_encoding (콘텐츠 기반 추론)
                #    requests가 Content-Type에서 인코딩을 찾지 못할 때, 바이트를 분석하여 추론
                if response.apparent_encoding and response.apparent_encoding.lower() not in [enc.lower() for enc, _ in decoding_attempts]:
                    decoding_attempts.append((response.apparent_encoding, 'apparent_encoding'))

                # 4. chardet (종합적인 바이트 분석)
                detected_by_chardet = chardet.detect(response.content)['encoding']
                if detected_by_chardet and detected_by_chardet.lower() not in [enc.lower() for enc, _ in decoding_attempts]:
                    decoding_attempts.append((detected_by_chardet, 'chardet'))

                # 5. 마지막 폴백: 한국어 웹사이트에서 흔히 사용되는 인코딩
                for enc in ['euc-kr', 'cp949']:
                    if enc.lower() not in [enc_try.lower() for enc_try, _ in decoding_attempts]:
                        decoding_attempts.append((enc, 'fallback'))
                
                # 모든 시도 목록을 순회하며 디코딩을 시도
                html_content = None
                for encoding_name, source in decoding_attempts:
                    try:
                        decoded_content = response.content.decode(encoding_name, errors='replace')
                        if '�' not in decoded_content: # 유니코드 대체 문자('�')가 없다면 성공으로 간주
                            logger.debug(f"Successfully decoded {url} with {encoding_name} (Source: {source}).")
                            html_content = decoded_content
                            break # 성공했으니 루프 종료
                        else:
                            logger.warning(f"Decoding {url} with {encoding_name} (Source: {source}) still contains replacement characters. Trying next.")
                    except (UnicodeDecodeError, LookupError):
                        logger.debug(f"Decoding {url} with {encoding_name} (Source: {source}) failed. Trying next.")
                
                # 모든 시도가 실패한 경우 (html_content가 여전히 None이거나 깨진 경우)
                if html_content is None or '�' in (html_content or ''):
                    logger.error(f"Failed to decode HTML content for '{url}' after all attempts. Returning None.")
                    return None
                
                return html_content

        except requests.exceptions.RequestException as e:
            logger.error(f"Network or HTTP error fetching URL '{url}': {e}")
            return None
        except WebDriverException as e: # Selenium 관련 오류도 처리
            logger.error(f"Selenium WebDriver error for URL '{url}': {e}", exc_info=True)
            return None
        except Exception as e:
            logger.error(f"Error fetching HTML from '{url}': {e}", exc_info=True)
            return None
        finally:
            if driver:
                driver.quit()

    def _extract_main_content(self, html_content: str, url: str, custom_title_selectors: list = None) -> dict | None:
        """
        주어진 HTML에서 주요 텍스트 콘텐츠와 제목을 추출합니다.
        기본적으로 Trafilatura를 사용하고, 실패 시 BeautifulSoup 폴백을 사용합니다.
        """
        if not html_content:
            return None

        soup = BeautifulSoup(html_content, 'html.parser')

        # 제목 추출 로직 (OG/Twitter Meta 우선, 그 다음 custom_title_selectors, 마지막으로 일반 H태그/<title>)
        page_title = "Untitled Article"
        og_title = soup.find('meta', property='og:title') or soup.find('meta', attrs={'name': 'twitter:title'})
        if og_title and og_title.get('content'):
            page_title = og_title['content'].strip()
        elif custom_title_selectors: # 특정 웹사이트를 위한 커스텀 제목 셀렉터
            for selector_args in custom_title_selectors:
                if isinstance(selector_args, tuple): # (tag_name, class_name)
                    title_tag = soup.find(selector_args[0], class_=selector_args[1])
                else: # tag_name
                    title_tag = soup.find(selector_args)
                
                if title_tag:
                    page_title = title_tag.get_text(strip=True)
                    break
        
        # 앞선 시도에서 제목을 찾지 못했거나 기본값("Untitled Article")인 경우 일반적인 H 태그 또는 <title> 시도
        if page_title == "Untitled Article" or not page_title: 
            article_title_tag = soup.find('h1', class_='itemTitle') or \
                                soup.find('h1', class_='card__title') or \
                                soup.find('h1') or \
                                soup.find('h2') or \
                                soup.find('h3')
            if article_title_tag:
                page_title = article_title_tag.get_text(strip=True)
            else:
                title_tag = soup.find('title')
                if title_tag:
                    page_title = title_tag.get_text(strip=True)

        extracted_content_str = extract(html_content)
        
        if extracted_content_str:
            logger.info(f"Successfully extracted text using trafilatura.")
            return {'title': page_title, 'content': str(extracted_content_str)}
        
        logger.warning(f"Trafilatura failed to extract content from {url}, trying BeautifulSoup.")
        
        # Trafilatura 실패 시 BeautifulSoup 폴백 로직
        paragraphs = soup.find_all(['p', 'h1', 'h2', 'h3', 'li'])
        text_content = []
        for p in paragraphs:
            text_content.append(p.get_text(separator=' ', strip=True))
        
        full_text = ' '.join(text_content).strip()
        
        if full_text:
            logger.info(f"Successfully extracted text using BeautifulSoup fallback.")
            return {'title': page_title, 'content': str(full_text)}
        else:
            logger.warning(f"No significant text found from URL: {url}")
            return None

    def get_list_page_urls(self, list_page_url: str) -> list[str]:
        """목록 페이지에서 기사 URL 목록을 추출합니다. 각 하위 클래스에서 구현해야 합니다."""
        raise NotImplementedError("Subclasses must implement get_list_page_urls method.")

    def get_article_details(self, article_url: str) -> dict | None:
        """기사 상세 페이지에서 정보를 추출합니다. 각 하위 클래스에서 구현해야 합니다."""
        # 기본적으로는 _extract_main_content를 사용하도록 폴백을 제공합니다.
        # 대부분의 웹사이트에서 기사 본문 추출은 범용 로직으로 처리될 수 있습니다.
        html_content = self._fetch_html(article_url)
        if not html_content:
            return None
        return self._extract_main_content(html_content, article_url)