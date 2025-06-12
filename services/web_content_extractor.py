# ai-content-marketing-tool/services/web_content_extractor.py

import requests
from bs4 import BeautifulSoup
import logging
from trafilatura import extract 
import re 
import os 

import chardet

# selenium 임포트
from selenium import webdriver 
from selenium.webdriver.chrome.service import Service 
from selenium.webdriver.chrome.options import Options 
from selenium.webdriver.common.by import By 
from selenium.webdriver.support.ui import WebDriverWait 
from selenium.webdriver.support import expected_conditions as EC 

# --- requests의 SSL 검증을 전역적으로 비활성화 (매우 위험, 임시용) ---
import urllib3 
import requests.packages.urllib3 
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning) 
requests.packages.urllib3.disable_warnings(requests.packages.urllib3.exceptions.InsecureRequestWarning) 

logger = logging.getLogger(__name__)

# extract_text_from_url 함수: 딕셔너리 반환
def extract_text_from_url(url: str) -> dict | None:
    """
    주어진 URL에서 주요 텍스트 콘텐츠와 기사 제목을 추출합니다.
    성공 시 {'title': '...', 'content': '...'} 딕셔너리를 반환하고, 실패 시 None을 반환합니다.
    """
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        response = requests.get(url, headers=headers, timeout=10, verify=False) 
        response.raise_for_status() 

        soup = BeautifulSoup(response.text, 'html.parser')
        
        page_title = "Untitled Article" 
        article_title_tag = soup.find('h1', class_='itemTitle') or soup.find('h1', class_='card__title')
        if article_title_tag:
            page_title = article_title_tag.get_text(strip=True)
        else:
            title_tag = soup.find('title')
            if title_tag:
                page_title = title_tag.get_text(strip=True)
            else:
                fallback_title_tag = soup.find('h1') or soup.find('h2')
                if fallback_title_tag:
                    page_title = fallback_title_tag.get_text(strip=True)

        # URL에 'fashionbiz.co.kr'이 포함되어 있고, 제목에 '패션비즈 | '가 있다면 제거
        if "fashionbiz.co.kr" in url and page_title.startswith("패션비즈 | "):
            page_title = page_title.replace("패션비즈 | ", "").strip()
            logger.info(f"Fashionbiz 제목에서 '패션비즈 | ' 접두어 제거: {page_title}")
        # --- 정제 로직 끝 ---

        extracted_content_str = extract(response.text) 
        
        if extracted_content_str: 
            logger.info(f"Successfully extracted text from URL using trafilatura: {url}")
            return {'title': page_title, 'content': str(extracted_content_str)} 
        
        logger.warning(f"Trafilatura failed to extract content from {url}, trying BeautifulSoup.")
        
        paragraphs = soup.find_all(['p', 'h1', 'h2', 'h3', 'li'])
        text_content = []
        for p in paragraphs:
            text_content.append(p.get_text(separator=' ', strip=True))
        
        full_text = ' '.join(text_content).strip()
        
        if full_text:
            logger.info(f"Successfully extracted text from URL using BeautifulSoup: {url}")
            return {'title': page_title, 'content': str(full_text)} 
        else:
            logger.warning(f"No significant text found from URL: {url}")
            return None

    except requests.exceptions.RequestException as e:
        logger.error(f"Network or HTTP error fetching URL '{url}': {e}")
        return None
    except Exception as e:
        logger.error(f"Error extracting text from URL '{url}': {e}", exc_info=True)
        return None

# --- ITWorld Korea 뉴스 목록에서 URL 추출하는 함수 ---
def extract_urls_from_itworld_list_page(list_page_url: str) -> list[str]:
    """
    ITWorld Korea의 뉴스 목록 페이지에서 기사 URL들을 추출합니다.
    """
    article_urls = []
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        response = requests.get(list_page_url, headers=headers, timeout=15, verify=False) 
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')

        for a_tag in soup.find_all('a', class_='grid content-row-article', href=True):
            href = a_tag.get('href')
            if href and href.startswith('https://www.itworld.co.kr/article/') and re.match(r'https://www.itworld.co.kr/article/\d+/\S+\.html$', href):
                article_urls.append(href)
            elif href and href.startswith('/article/') and re.match(r'^/article/\d+/\S+\.html$', href):
                full_url = "https://www.itworld.co.kr" + href
                article_urls.append(full_url)
        
        article_urls = list(set(article_urls))
        logger.info(f"Successfully extracted {len(article_urls)} URLs from {list_page_url}")
        return article_urls

    except requests.exceptions.RequestException as e:
        logger.error(f"Network or HTTP error fetching URL list '{list_page_url}': {e}")
        return []
    except Exception as e:
        logger.error(f"Error extracting URLs from list page '{list_page_url}': {e}", exc_info=True)
        return []

# --- ITWorld 기사 상세 페이지에서 정보 추출하는 함수 ---
def extract_article_details_from_itworld(article_url: str) -> dict | None:
    """
    ITWorld 기사 상세 페이지에서 제목, 본문, 작성자, 작성 날짜를 추출합니다.
    성공 시 {'title': '...', 'content': '...', 'author': '...', 'date': '...'} 딕셔너리를 반환합니다.
    """
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        response = requests.get(article_url, headers=headers, timeout=15, verify=False) 
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')

        # 1. 기사 제목 추출
        title = "제목 없음"
        title_tag = soup.find('h1', class_='article-hero__title')
        if title_tag:
            title = title_tag.get_text(strip=True)
        else: # 폴백으로 <title> 태그 사용
            title_tag = soup.find('title')
            if title_tag:
                title = title_tag.get_text(strip=True)
        logger.info(f"ITWorld 기사 제목 추출: {title}")

        # 2. 작성자 추출
        author = "작성자 불명"
        author_div = soup.find('div', class_='author__name')
        if author_div:
            author_a_tag = author_div.find('a', itemprop='url')
            if author_a_tag:
                author = author_a_tag.get_text(strip=True)
            else: # <a> 태그 없이 바로 이름이 있는 경우
                author = author_div.get_text(strip=True).replace('By', '').strip()
        logger.info(f"ITWorld 기사 작성자 추출: {author}")

        # 3. 작성 날짜 추출
        date_str = "날짜 불명"
        # 날짜는 보통 <span itemprop="datePublished"> 같은 태그 안에 있습니다.
        # 또는 <div class="card__info card__info--light"> 안에 있을 수 있습니다.
        date_span_tag = soup.find('span', itemprop='datePublished')
        if date_span_tag:
            date_str = date_span_tag.get_text(strip=True)
        else: # 다른 위치에서 찾기 시도
            # 예시 HTML에서 <span>2025.06.02</span> 같은 패턴을 확인
            # 이를 감싸는 더 큰 div나 p를 찾아야 합니다.
            # 지금 주어진 HTML에는 명확한 부모가 없으므로, 일반적인 span 태그를 시도해봅니다.
            date_span_tag = soup.find('span', text=re.compile(r'\d{4}\.\d{2}\.\d{2}')) # YYYY.MM.DD 패턴
            if date_span_tag:
                date_str = date_span_tag.get_text(strip=True)
        logger.info(f"ITWorld 기사 날짜 추출: {date_str}")


        # 4. 기사 본문 추출
        article_content_full = ""
        # 본문 전체를 감싸는 가장 명확한 컨테이너: <div class="article-column__content">
        content_divs = soup.find_all('div', class_='article-column__content')
        
        # 각 본문 컨테이너에서 <p> 태그들을 추출하여 결합
        paragraphs = []
        for content_div in content_divs:
            for p_tag in content_div.find_all('p'):
                text = p_tag.get_text(strip=True)
                if text:
                    paragraphs.append(text)
            # <h2>, <h3>, <ul> 등 다른 태그들도 본문에 포함
            for heading_tag in content_div.find_all(['h2', 'h3']):
                text = heading_tag.get_text(strip=True)
                if text:
                    paragraphs.append(text)
            for ul_tag in content_div.find_all('ul'):
                for li_tag in ul_tag.find_all('li'):
                    text = li_tag.get_text(strip=True)
                    if text:
                        paragraphs.append(f"- {text}") # 리스트 항목은 - 로 시작
        
        article_content_full = "\n\n".join(paragraphs).strip() # 문단별로 줄바꿈 추가
        
        # 만약 본문이 비어있다면 trafilatura fallback 사용 (extract_text_from_url과 유사)
        if not article_content_full:
            logger.warning(f"ITWorld: BeautifulSoup로 본문 추출 실패, trafilatura로 시도: {article_url}")
            extracted_fallback = extract(response.text)
            article_content_full = str(extracted_fallback) if extracted_fallback else ""

        if not article_content_full:
            logger.warning(f"ITWorld: 본문 추출 실패: {article_url}")
            return None # 본문 없으면 실패로 간주

        return {
            'title': title,
            'content': article_content_full,
            'author': author,
            'date': date_str
        }

    except requests.exceptions.RequestException as e:
        logger.error(f"Network or HTTP error fetching ITWorld article details '{article_url}': {e}", exc_info=True)
        return None
    except Exception as e:
        logger.error(f"Error extracting ITWorld article details from '{article_url}': {e}", exc_info=True)
        return None

# --- Fashionbiz.co.kr 뉴스 목록에서 URL 추출하는 함수 (Selenium 사용) ---
def extract_urls_from_fashionbiz_list_page(list_page_url: str) -> list[str]:
    """
    Fashionbiz.co.kr의 뉴스 목록 페이지 (및 검색 결과 페이지)에서 기사 URL들을 추출합니다.
    Selenium을 사용하여 JavaScript 렌더링을 처리합니다.
    """
    article_urls = []
    driver = None 
    try:
        # Chrome 옵션 설정
        chrome_options = Options()
        chrome_options.add_argument("--headless")  # GUI 없이 백그라운드에서 실행
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument(f"user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36")
        chrome_options.add_experimental_option('excludeSwitches', ['enable-logging'])
        # SSL 인증서 오류 무시 옵션 (강력 적용)
        chrome_options.add_argument("--ignore-certificate-errors") 
        chrome_options.add_argument("--allow-insecure-localhost") 
        chrome_options.add_argument("--ignore-ssl-errors") 
        chrome_options.add_argument("--disable-features=NetworkService") 

        # ChromeDriver 실행 파일의 로컬 경로를 지정합니다.
        chrome_driver_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'drivers', 'chromedriver.exe') 
        service = Service(executable_path=chrome_driver_path) 
        driver = webdriver.Chrome(service=service, options=chrome_options)
        
        logger.info(f"Loading {list_page_url} with Selenium (Type: Fashionbiz, Local Driver)...")
        driver.get(list_page_url)
        
        WebDriverWait(driver, 15).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, 'div.sc-53c9553f-0.ksjCKq')) 
        )
        driver.implicitly_wait(2) 

        soup = BeautifulSoup(driver.page_source, 'html.parser')
        
        for article_div in soup.find_all('div', class_='sc-53c9553f-0 ksjCKq'): 
            a_tag = article_div.find('a', href=True)
            if a_tag:
                href = a_tag.get('href')
                if href and re.match(r'^/article/\d+$', href):
                    full_url = "https://fashionbiz.co.kr" + href
                    article_urls.append(full_url)
        
        article_urls = list(set(article_urls))
        logger.info(f"Successfully extracted {len(article_urls)} URLs from {list_page_url} (Fashionbiz, Selenium)")
        return article_urls

    except Exception as e:
        logger.error(f"Error extracting URLs from list page '{list_page_url}' (Fashionbiz, Selenium): {e}", exc_info=True)
        return []
    finally:
        if driver: 
            driver.quit()

# --- 10000recipe.com 레시피 목록에서 URL 추출하는 새로운 함수 ---
def extract_urls_from_10000recipe_list_page(list_page_url: str) -> list[str]:
    """
    10000recipe.com의 레시피 목록 페이지에서 레시피 URL들을 추출합니다.
    """
    article_urls = []
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        response = requests.get(list_page_url, headers=headers, timeout=15, verify=False) 
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')

        for a_tag in soup.find_all('a', class_='common_sp_link', href=True):
            href = a_tag.get('href')
            if href and re.match(r'^/recipe/\d+$', href):
                full_url = "https://www.10000recipe.com" + href
                article_urls.append(full_url)
        
        article_urls = list(set(article_urls))
        logger.info(f"Successfully extracted {len(article_urls)} URLs from {list_page_url} (10000recipe.com)")
        return article_urls

    except requests.exceptions.RequestException as e:
        logger.error(f"Network or HTTP error fetching URL list '{list_page_url}' (10000recipe.com): {e}", exc_info=True)
        return []
    except Exception as e:
        logger.error(f"Error extracting URLs from list page '{list_page_url}' (10000recipe.com): {e}", exc_info=True)
        return []

# --- 10000recipe.com 레시피 상세 페이지에서 정보 추출하는 함수 ---
def extract_recipe_details_from_10000recipe(recipe_url: str) -> dict | None:
    """
    10000recipe.com의 레시피 상세 페이지에서 제목, 재료, 조리 순서를 추출합니다.
    성공 시 {'title': '...', 'ingredients': ['...'], 'steps': ['...']} 딕셔너리를 반환합니다.
    """
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        # verify=False 옵션 유지 (SSL 검증 우회)
        response = requests.get(recipe_url, headers=headers, timeout=15, verify=False) 
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')

        # 1. 제목 추출 (<h3> 태그 사용)
        title_tag = soup.find('h3') 
        title = title_tag.get_text(strip=True) if title_tag else "제목 없음"
        logger.info(f"레시피 제목 추출: {title}")

        # 2. 재료 목록 추출
        ingredients = []
        # 전체 재료 컨테이너: <div class="ready_ingre3" id="divConfirmedMaterialArea">
        materials_container = soup.find('div', class_='ready_ingre3', id='divConfirmedMaterialArea')
        if materials_container:
            # 각 재료 그룹 (<ul> 태그) 순회
            for ul_tag in materials_container.find_all('ul'):
                # 각 재료 항목 (<li> 태그) 순회
                for li_tag in ul_tag.find_all('li'):
                    name_div = li_tag.find('div', class_='ingre_list_name')
                    amount_span = li_tag.find('span', class_='ingre_list_ea')
                    
                    if name_div and amount_span:
                        ingredient_name = name_div.get_text(strip=True)
                        ingredient_amount = amount_span.get_text(strip=True)
                        ingredients.append(f"{ingredient_name} {ingredient_amount}")
        logger.info(f"레시피 재료 추출: {len(ingredients)}개")

        # 3. 조리 순서 추출
        steps = []
        # 전체 조리 순서 컨테이너: <div class="view_step" id="obx_recipe_step_start">
        # 각 조리 단계: <div id="stepDivX" class="view_step_cont media stepX">
        # 조리 단계 텍스트: <div id="stepdescrX" class="media-body">
        
        # 'view_step_cont' 클래스를 가진 div 태그들을 찾아 순회
        for step_div in soup.find_all('div', class_='view_step_cont'):
            step_description_div = step_div.find('div', class_='media-body')
            if step_description_div:
                step_text = step_description_div.get_text(strip=True)
                steps.append(step_text)
        logger.info(f"레시피 조리 순서 추출: {len(steps)}단계")
        
        if not title or not ingredients or not steps:
            logger.warning(f"레시피 정보 일부 누락: {recipe_url} - 제목:{bool(title)}, 재료:{bool(ingredients)}, 단계:{bool(steps)}")

        return {
            'title': title,
            'ingredients': ingredients,
            'steps': steps
        }

    except requests.exceptions.RequestException as e:
        logger.error(f"Network or HTTP error fetching recipe details '{recipe_url}': {e}", exc_info=True)
        return None
    except Exception as e:
        logger.error(f"Error extracting recipe details from '{recipe_url}': {e}", exc_info=True)
        return None

# --- news.hidoc.co.kr 뉴스 목록에서 URL 추출하는 새로운 함수 ---
def extract_urls_from_hidoc_list_page(list_page_url: str) -> list[str]:
    """
    news.hidoc.co.kr의 뉴스 목록 페이지에서 기사 URL들을 추출합니다.
    """
    article_urls = []
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        # 하이닥은 requests로 충분할 수 있으므로 Selenium 없이 requests 사용
        response = requests.get(list_page_url, headers=headers, timeout=15, verify=False) 
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')

        # 'thumb' 클래스를 가진 <a> 태그를 찾고 href 속성으로 필터링합니다.
        for a_tag in soup.find_all('a', class_='thumb', href=True):
            href = a_tag.get('href')
            # 기사 상세 페이지 URL 패턴: https://news.hidoc.co.kr/news/articleView.html?idxno=숫자
            if href and href.startswith('https://news.hidoc.co.kr/news/articleView.html?idxno=') and re.match(r'https://news\.hidoc\.co\.kr/news/articleView\.html\?idxno=\d+$', href):
                article_urls.append(href)
        
        # 중복 제거 (set을 이용)
        article_urls = list(set(article_urls))
        logger.info(f"Successfully extracted {len(article_urls)} URLs from {list_page_url} (HiDoc News)")
        return article_urls

    except requests.exceptions.RequestException as e:
        logger.error(f"Network or HTTP error fetching URL list '{list_page_url}' (HiDoc News): {e}", exc_info=True)
        return []
    except Exception as e:
        logger.error(f"Error extracting URLs from list page '{list_page_url}' (HiDoc News): {e}", exc_info=True)
        return []

# --- news.hidoc.co.kr 기사 상세 페이지에서 정보 추출하는 함수 ---
def extract_article_details_from_hidoc(article_url: str) -> dict | None:
    """
    news.hidoc.co.kr의 기사 상세 페이지에서 제목, 본문, 작성자, 작성 날짜를 추출합니다.
    성공 시 {'title': '...', 'content': '...', 'author': '...', 'date': '...'} 딕셔너리를 반환합니다.
    """
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        response = requests.get(article_url, headers=headers, timeout=15, verify=False) 
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')

        # 1. 기사 제목 추출 (h1.heading 사용)
        title_tag = soup.find('h1', class_='heading') 
        title = title_tag.get_text(strip=True) if title_tag else "제목 없음"
        logger.info(f"하이닥 기사 제목 추출: {title}")

        # 2. 작성자 추출
        author = "작성자 불명"
        # <ul class="infomation"> 안의 <li> 태그 중 icon-user-o 아이콘을 가진 li를 찾습니다.
        author_list_item = soup.select_one('ul.infomation li i.icon-user-o') # icon-user-o 아이콘을 직접 찾음
        if author_list_item:
            # 아이콘 태그의 부모 (li)에서 모든 텍스트를 가져오되, 아이콘 태그는 제거합니다.
            parent_li = author_list_item.find_parent('li')
            if parent_li:
                # 불필요한 자식 태그들(<i>, <span>)을 제거합니다.
                for unwanted_tag in parent_li.find_all(['i', 'span']):
                    unwanted_tag.decompose()
                author = parent_li.get_text(strip=True)
                # "기자명" 같은 불필요한 접두사 제거
                author = re.sub(r'기자명\s*', '', author).strip()
        
        logger.info(f"하이닥 기사 작성자 추출: {author}")

        # 3. 작성 날짜/시간 추출
        date_str = "날짜 불명"
        # <ul class="infomation"> 안의 <li> 태그 중 icon-clock-o 아이콘을 가진 li를 찾습니다.
        date_list_item = soup.select_one('ul.infomation li i.icon-clock-o') # icon-clock-o 아이콘을 직접 찾음
        if date_list_item:
            # 아이콘 태그의 부모 (li)에서 모든 텍스트를 가져옵니다.
            parent_li = date_list_item.find_parent('li')
            if parent_li:
                date_text = parent_li.get_text(strip=True)
                # "입력 YYYY.MM.DD HH:MM" 형태에서 날짜 부분만 추출
                date_match = re.search(r'\d{4}\.\d{2}\.\d{2}', date_text)
                if date_match:
                    date_str = date_match.group(0) 
        
        logger.info(f"하이닥 기사 날짜 추출: {date_str}")

        # 4. 기사 본문 추출 (기존 로직 유지)
        article_content_full = ""
        article_body_container = soup.find('article', id='article-view-content-div')
        if article_body_container:
            for ad_div in article_body_container.find_all('div', id=re.compile(r'^AD\d+')):
                ad_div.decompose() 
            
            paragraphs = []
            for p_tag in article_body_container.find_all('p'):
                text = p_tag.get_text(strip=True)
                if text:
                    paragraphs.append(text)
            
            article_content_full = "\n\n".join(paragraphs).strip()
        
        if not article_content_full:
            logger.warning(f"하이닥: BeautifulSoup로 본문 추출 실패, trafilatura로 시도: {article_url}")
            extracted_fallback = extract(response.text)
            article_content_full = str(extracted_fallback) if extracted_fallback else ""

        if not article_content_full:
            logger.warning(f"하이닥: 본문 추출 실패: {article_url}")
            return None 

        return {
            'title': title,
            'content': article_content_full,
            'author': author,
            'date': date_str
        }

    except requests.exceptions.RequestException as e:
        logger.error(f"Network or HTTP error fetching HiDoc article details '{article_url}': {e}", exc_info=True)
        return None
    except Exception as e:
        logger.error(f"Error extracting HiDoc article details from '{article_url}': {e}", exc_info=True)
        return None

# --- tlnews.co.kr 뉴스 목록에서 URL 추출하는 새로운 함수 ---
def extract_urls_from_tlnews_list_page(list_page_url: str) -> list[str]:
    """
    tlnews.co.kr의 뉴스 목록 페이지에서 기사 URL들을 추출합니다.
    """
    article_urls = []
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        # tlnews는 requests로 충분할 수 있으므로 Selenium 없이 requests 사용
        response = requests.get(list_page_url, headers=headers, timeout=15, verify=False) 
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')

        # 각 기사 항목 전체를 감싸는 <li> 태그를 찾습니다.
        # 그 안에 있는 모든 <a> 태그 중, articleView.html?idxno= 패턴을 가진 링크를 추출합니다.
        for li_tag in soup.find_all('li'): # 각 기사가 <li> 태그로 구분
            for a_tag in li_tag.find_all('a', href=True): # <li> 안의 모든 <a> 태그 탐색
                href = a_tag.get('href')
                # 기사 상세 페이지 URL 패턴: /news/articleView.html?idxno=숫자
                if href and href.startswith('/news/articleView.html?idxno=') and re.match(r'/news/articleView\.html\?idxno=\d+$', href):
                    full_url = "https://www.tlnews.co.kr" + href
                    article_urls.append(full_url)
        
        # 중복 제거 (set을 이용)
        article_urls = list(set(article_urls))
        logger.info(f"Successfully extracted {len(article_urls)} URLs from {list_page_url} (TLNews)")
        return article_urls

    except requests.exceptions.RequestException as e:
        logger.error(f"Network or HTTP error fetching URL list '{list_page_url}' (TLNews): {e}", exc_info=True)
        return []
    except Exception as e:
        logger.error(f"Error extracting URLs from list page '{list_page_url}' (TLNews): {e}", exc_info=True)
        return []

# --- tlnews.co.kr 기사 상세 페이지에서 정보 추출하는 함수 ---
def extract_article_details_from_tlnews(article_url: str) -> dict | None:
    """
    tlnews.co.kr의 기사 상세 페이지에서 제목, 본문, 작성자, 작성 날짜를 추출합니다.
    성공 시 {'title': '...', 'content': '...', 'author': '...', 'date': '...'} 딕셔너리를 반환합니다.
    """
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        response = requests.get(article_url, headers=headers, timeout=15, verify=False)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')

        # 1. 기사 제목 추출
        title = "제목 없음"
        # TLNews 기사 제목 태그를 확인합니다. (예: <h3 class="titles">)
        title_tag = soup.find('h3', class_='heading')
        if title_tag:
            title = title_tag.get_text(strip=True)
        logger.info(f"TLNews 기사 제목 추출: {title}")

        # 2. 작성자 추출
        author = "작성자 불명"
        # 'icon-user-o' 클래스를 가진 <i> 태그의 부모 <li>를 찾습니다.
        author_list_item = soup.select_one('ul.infomation li i.icon-user-o')
        if author_list_item:
            parent_li = author_list_item.find_parent('li')
            if parent_li:
                # <i> 태그 내의 <span> 태그 제거 (예: <span class="show-for-sr">기자명</span>)
                for span_tag in parent_li.find_all('span', class_='show-for-sr'):
                    span_tag.decompose()
                author_text = parent_li.get_text(strip=True)
                # 불필요한 공백 제거 및 정리
                author = author_text.strip()
        logger.info(f"TLNews 기사 작성자 추출: {author}")

        # 3. 작성 날짜 추출
        date_str = "날짜 불명"
        # 'icon-clock-o' 클래스를 가진 <i> 태그의 부모 <li>를 찾습니다.
        date_list_item = soup.select_one('ul.infomation li i.icon-clock-o')
        if date_list_item:
            parent_li = date_list_item.find_parent('li')
            if parent_li:
                date_text = parent_li.get_text(strip=True)
                # "입력 2025.05.27 10:15" 형태에서 날짜 부분만 추출 (YYYY.MM.DD)
                date_match = re.search(r'\d{4}\.\d{2}\.\d{2}', date_text)
                if date_match:
                    date_str = date_match.group(0)
        logger.info(f"TLNews 기사 날짜 추출: {date_str}")

        # 4. 기사 본문 추출
        article_content_full = ""
        # 실제 tlnews.co.kr의 기사 본문 컨테이너 태그를 확인해야 합니다.
        # 예시: <div id="article-view-content-div" class="article-view-content"> ... </div>
        article_body_container = soup.find('div', id='article-view-content-div') # TLNews 웹사이트에 맞게 수정
        if article_body_container:
            # 광고나 불필요한 요소 제거 (필요하다면)
            for ad_div in article_body_container.find_all('div', class_='google-auto-placed'): # 예시: 구글 광고 div 제거
                ad_div.decompose()
            for script_tag in article_body_container.find_all('script'): # script 태그 제거
                script_tag.decompose()

            paragraphs = []
            # 본문 내의 모든 텍스트를 포함하는 태그들을 찾습니다.
            for tag in article_body_container.find_all(['p', 'h1', 'h2', 'h3', 'h4', 'ul', 'li', 'strong']):
                text = tag.get_text(separator=' ', strip=True)
                if text:
                    paragraphs.append(text)

            article_content_full = "\n\n".join(paragraphs).strip()

        if not article_content_full:
            logger.warning(f"TLNews: BeautifulSoup로 본문 추출 실패, trafilatura로 시도: {article_url}")
            extracted_fallback = extract(response.text)
            article_content_full = str(extracted_fallback) if extracted_fallback else ""

        if not article_content_full:
            logger.warning(f"TLNews: 본문 추출 실패: {article_url}")
            return None

        return {
            'title': title,
            'content': article_content_full,
            'author': author,
            'date': date_str
        }

    except requests.exceptions.RequestException as e:
        logger.error(f"Network or HTTP error fetching TLNews article details '{article_url}': {e}", exc_info=True)
        return None
    except Exception as e:
        logger.error(f"Error extracting TLNews article details from '{article_url}': {e}", exc_info=True)
        return None

# --- beautynury.com 뉴스 목록에서 URL 추출하는 함수 ---
def extract_urls_from_beautynury_list_page(list_page_url: str) -> list[str]:
    """
    beautynury.com의 뉴스 목록 페이지에서 기사 URL들을 추출합니다.
    """
    article_urls = []
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        response = requests.get(list_page_url, headers=headers, timeout=15, verify=False)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')

        # <li> 태그 내의 <a> 태그에서 href를 추출합니다.
        # <a href="/news/view/108191/cat/10/page/1">
        for li_tag in soup.find_all('li'):
            a_tag = li_tag.find('a', href=re.compile(r'/news/view/\d+/cat/\d+/page/\d+'))
            if a_tag:
                href = a_tag.get('href')
                if href:
                    full_url = "https://www.beautynury.com" + href
                    article_urls.append(full_url)

        article_urls = list(set(article_urls)) # 중복 제거
        logger.info(f"Successfully extracted {len(article_urls)} URLs from {list_page_url} (Beautynury)")
        return article_urls

    except requests.exceptions.RequestException as e:
        logger.error(f"Network or HTTP error fetching URL list '{list_page_url}' (Beautynury): {e}", exc_info=True)
        return []
    except Exception as e:
        logger.error(f"Error extracting URLs from list page '{list_page_url}' (Beautynury): {e}", exc_info=True)
        return []

# --- beautynury.com 기사 상세 페이지에서 정보 추출하는 함수 ---
def extract_article_details_from_beautynury(article_url: str) -> dict | None:
    """
    주어진 URL에서 주요 텍스트 콘텐츠와 기사 제목을 추출합니다.
    성공 시 {'title': '...', 'content': '...'} 딕셔너리를 반환하고, 실패 시 None을 반환합니다.
    """
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        response = requests.get(article_url, headers=headers, timeout=15, verify=False)
        response.raise_for_status()

        detected_encoding = chardet.detect(response.content)['encoding']
        logger.info(f"Detected encoding for {article_url}: {detected_encoding}")

        if detected_encoding:
            try:
                decoded_html = response.content.decode(detected_encoding, errors='replace')
            except (UnicodeDecodeError, LookupError):
                logger.warning(f"Failed to decode with {detected_encoding}. Trying common Korean encodings.")
                try:
                    decoded_html = response.content.decode('euc-kr', errors='replace')
                except UnicodeDecodeError:
                    try:
                        decoded_html = response.content.decode('cp949', errors='replace')
                    except UnicodeDecodeError:
                        logger.warning("Tried euc-kr and cp949, still failing. Trying utf-8 as last resort.")
                        decoded_html = response.content.decode('utf-8', errors='replace')
        else:
            logger.warning("Could not detect encoding, falling back to common Korean encodings.")
            try:
                decoded_html = response.content.decode('euc-kr', errors='replace')
            except UnicodeDecodeError:
                try:
                    decoded_html = response.content.decode('cp949', errors='replace')
                except UnicodeDecodeError:
                    logger.warning("Tried euc-kr and cp949, still failing. Trying utf-8 as last resort.")
                    decoded_html = response.content.decode('utf-8', errors='replace')

        soup = BeautifulSoup(decoded_html, 'html.parser')

        # 1. 기사 제목 추출
        title = "제목 없음"
        title_con_div = soup.find('div', class_='title_con')
        logger.info(f"Debug: Found title_con_div: {bool(title_con_div)}")

        if title_con_div:
            strong_tag = title_con_div.find('strong')
            if strong_tag:
                title = strong_tag.get_text(strip=True)
            else:
                full_title_text = title_con_div.get_text(separator=' ', strip=True)
                logger.info(f"Debug: No strong tag. Full text from title_con_div: '{full_title_text}'")
                span_tag = title_con_div.find('span')
                if span_tag:
                    span_text = span_tag.get_text(strip=True)
                    title = full_title_text.replace(span_text, '').strip()
                else:
                    title = full_title_text

            if title and (title == "제목 없음" or len(title) < 10 or len(title) > 100):
                title_match = re.match(r"^(.*?)\s*(?:\[.*?\]|\(.*?\)|[가-힣\s]*?기획전\s*진행|[가-힣\s]*?확대\s*방안|[가-힣\s]*?선봬|[가-힣\s]*?공개|[가-힣\s]*?발표|[가-힣\s]*?협업|\.\.\.)?$", title)
                if title_match:
                    title = title_match.group(1).strip()

        # title_con_div 자체가 없거나, 위에서 제목을 찾지 못했을 때 <title> 태그 폴백
        if title == "제목 없음" or not title:
            title_tag = soup.find('title')
            if title_tag:
                page_title = title_tag.get_text(strip=True)
                # '뷰티누리 - 화장품신문 (Beautynury.com) :: ' 접두사와 '| 뷰티누리', '| Beautynury' 접미사 제거
                # 변경된 부분: 접두사 제거 정규식 추가
                title = re.sub(r'뷰티누리\s*-\s*화장품신문\s*\(Beautynury\.com\)\s*::\s*', '', page_title).strip()
                title = re.sub(r'\s*\|\s*뷰티누리|\s*\|\s*Beautynury', '', title).strip()
                if not title:
                    title = page_title
        
        logger.info(f"Beautynury 기사 제목 추출: {title}")

        # 2. 작성자 추출
        author = "작성자 불명"
        name_con_div = soup.find('div', class_='name_con')
        if name_con_div:
            author_span = name_con_div.find('span')
            if author_span:
                author_text = author_span.get_text(strip=True)
                author = re.sub(r'\s*기자', '', author_text).strip()
                author = re.sub(r'[\r\n\t]+', '', author).strip()
        logger.info(f"Beautynury 기사 작성자 추출: {author}")

        # 3. 작성 날짜 추출
        date_str = "날짜 불명"
        date_con_div = soup.find('div', class_='date_con')
        if date_con_div:
            input_date_span = date_con_div.find('span', text=re.compile(r'입력 \d{4}-\d{2}-\d{2} \d{2}:\d{2}'))
            if input_date_span:
                date_text = input_date_span.get_text(strip=True)
                date_match = re.search(r'\d{4}-\d{2}-\d{2}', date_text)
                if date_match:
                    date_str = date_match.group(0)
            else:
                for span_tag in date_con_div.find_all('span'):
                    date_text = span_tag.get_text(strip=True)
                    date_match = re.search(r'\d{4}-\d{2}-\d{2}', date_text)
                    if date_match:
                        date_str = date_match.group(0)
                        break
        logger.info(f"Beautynury 기사 날짜 추출: {date_str}")

        # 4. 기사 본문 추출
        article_content_full = ""
        article_body_container = soup.find('div', class_='text article_view')
        if article_body_container:
            paragraphs = []
            for tag in article_body_container.find_all(['p', 'figcaption']):
                text = tag.get_text(strip=True)
                if text:
                    paragraphs.append(text)

            article_content_full = "\n\n".join(paragraphs).strip()

        if not article_content_full:
            logger.warning(f"Beautynury: BeautifulSoup로 본문 추출 실패, trafilatura로 시도: {article_url}")
            extracted_fallback = extract(decoded_html)
            article_content_full = str(extracted_fallback) if extracted_fallback else ""

        if not article_content_full:
            logger.warning(f"Beautynury: 본문 추출 실패: {article_url}")
            return None

        return {
            'title': title,
            'content': article_content_full,
            'author': author,
            'date': date_str
        }

    except requests.exceptions.RequestException as e:
        logger.error(f"Network or HTTP error fetching Beautynury article details '{article_url}': {e}", exc_info=True)
        return None
    except Exception as e:
        logger.error(f"Error extracting Beautynury article details from '{article_url}': {e}", exc_info=True)
        return None

if __name__ == "__main__":
    # 로깅 설정 (콘솔에 정보 메시지 출력)
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

    print("\n" + "-"*50 + "\n")

    # Beautynury 뉴스 목록 추출 테스트
    beautynury_list_url = "https://www.beautynury.com/news/lists/cat/10/page/"
    print(f"--- Beautynury URL 추출 테스트: {beautynury_list_url} ---")
    extracted_beautynury_urls = extract_urls_from_beautynury_list_page(beautynury_list_url)
    if extracted_beautynury_urls:
        print(f"Beautynury에서 성공적으로 {len(extracted_beautynury_urls)}개의 URL 추출:")
        for i, url in enumerate(extracted_beautynury_urls[:5]):
            print(f"{i+1}. {url}")
        if len(extracted_beautynury_urls) > 5:
            print(f"... 그리고 {len(extracted_beautynury_urls) - 5}개의 URL이 더 있습니다.")

        print("\n" + "-"*50 + "\n")

        # Beautynury 상세 기사 추출 테스트
        if extracted_beautynury_urls:
            test_article_url_beautynury = extracted_beautynury_urls[0]
            print(f"--- Beautynury 상세 기사 추출 테스트: {test_article_url_beautynury} ---")
            article_details_beautynury = extract_article_details_from_beautynury(test_article_url_beautynury)

            if article_details_beautynury:
                print("\n--- Beautynury 기사 상세 정보 ---")
                print(f"제목: {article_details_beautynury.get('title', 'N/A')}")
                print(f"작성자: {article_details_beautynury.get('author', 'N/A')}")
                print(f"날짜: {article_details_beautynury.get('date', 'N/A')}")
                print("\n본문 (일부):\n")
                content_beautynury = article_details_beautynury.get('content', 'N/A')
                print(content_beautynury[:500] + "..." if len(content_beautynury) > 500 else content_beautynury)
                print("\n" + "-"*50 + "\n")
            else:
                print(f"Beautynury 기사 상세 정보 추출 실패: {test_article_url_beautynury}")
                print("로그를 확인하여 오류를 파악하세요.")
    else:
        print("Beautynury에서 URL을 추출하지 못했습니다. 로그를 확인하여 오류를 파악하세요.")

    print("\n" + "-"*50 + "\n")
    print("모든 웹 콘텐츠 추출 테스트가 완료되었습니다.")