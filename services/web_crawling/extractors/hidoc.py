# services/web_crawling/extractors/hidoc.py (최종 수정안)
import re 
from .base_extractor import BaseExtractor, BeautifulSoup, logger, requests, extract # requests 임포트 추가

class HidocExtractor(BaseExtractor):
    """news.hidoc.co.kr 웹사이트에서 콘텐츠를 추출하는 클래스."""
    BASE_URL = "https://news.hidoc.co.kr"

    # HiDoc은 목록 페이지와 상세 페이지 모두 requests로 충분하며,
    # BaseExtractor의 복잡한 인코딩 처리보다는 requests.text가 더 잘 맞는 경우입니다.
    # 따라서, HidocExtractor에서 직접 HTML을 가져오는 메서드를 사용하겠습니다.
    def _fetch_html_for_hidoc(self, url: str) -> str | None:
        """
        HiDoc 전용 HTML fetch 로직: requests.text를 직접 사용합니다.
        BaseExtractor의 복잡한 인코딩 감지 로직이 HiDoc에서 문제를 일으키는 것을 방지합니다.
        """
        logger.info(f"Fetching {url} for HiDoc using direct requests.text strategy...")
        try:
            response = requests.get(url, headers=self.HEADERS, timeout=self.TIMEOUT, verify=False)
            response.raise_for_status()
            
            # 여기서 requests의 기본 인코딩 추론인 response.text를 그대로 사용합니다.
            # 이 방식이 HiDoc에서 과거에 깨지지 않고 잘 작동했다고 하셨으므로.
            html_content = response.text
            logger.debug(f"Requests' inferred encoding for {url} (HiDoc custom): {response.encoding}")

            if not html_content:
                logger.warning(f"HiDoc: No content retrieved for {url} using direct requests.text.")
            elif '�' in html_content:
                logger.warning(f"HiDoc: Content for {url} contains replacement characters even with direct requests.text. This might indicate a deeper issue.")
                # 그럼에도 불구하고, 과거에 됐었다면 일단 반환하여 BeautifulSoup가 처리하도록 합니다.
            return html_content

        except requests.exceptions.RequestException as e:
            logger.error(f"Network or HTTP error fetching HiDoc URL '{url}': {e}", exc_info=True)
            return None
        except Exception as e:
            logger.error(f"Error fetching HiDoc HTML from '{url}': {e}", exc_info=True)
            return None


    def get_list_page_urls(self, list_page_url: str) -> list[str]:
        """news.hidoc.co.kr의 뉴스 목록 페이지에서 기사 URL들을 추출합니다."""
        # 이 메서드도 이제 HiDoc 전용 _fetch_html_for_hidoc를 호출합니다.
        article_urls = []
        html_content = self._fetch_html_for_hidoc(list_page_url) # 변경!
        if not html_content:
            return []

        soup = BeautifulSoup(html_content, 'html.parser')

        for a_tag in soup.find_all('a', class_='thumb', href=True):
            href = a_tag.get('href')
            if href and href.startswith(self.BASE_URL + '/news/articleView.html?idxno=') and re.match(r'https://news\.hidoc\.co\.kr/news/articleView\.html\?idxno=\d+$', href):
                article_urls.append(href)
        
        article_urls = list(set(article_urls))
        logger.info(f"Successfully extracted {len(article_urls)} URLs from {list_page_url} (HiDoc News)")
        return article_urls


    def get_article_details(self, article_url: str) -> dict | None:
        """news.hidoc.co.kr의 기사 상세 페이지에서 제목, 본문, 작성자, 작성 날짜를 추출합니다."""
        # 이 메서드도 이제 HiDoc 전용 _fetch_html_for_hidoc를 호출합니다.
        html_content = self._fetch_html_for_hidoc(article_url) # 변경!
        if not html_content:
            return None

        soup = BeautifulSoup(html_content, 'html.parser')

        # 1. 기사 제목 추출 (h1.heading 사용)
        title_tag = soup.find('h1', class_='heading')
        title = title_tag.get_text(strip=True) if title_tag else "제목 없음"
        logger.info(f"하이닥 기사 제목 추출: {title}")

        # 2. 작성자 추출
        author = "작성자 불명"
        author_list_item = soup.select_one('ul.infomation li i.icon-user-o')
        if author_list_item:
            parent_li = author_list_item.find_parent('li')
            if parent_li:
                for unwanted_tag in parent_li.find_all(['i', 'span']):
                    unwanted_tag.decompose()
                author = parent_li.get_text(strip=True)
                author = re.sub(r'기자명\s*', '', author).strip()
        logger.info(f"하이닥 기사 작성자 추출: {author}")

        # 3. 작성 날짜/시간 추출
        date_str = "날짜 불명"
        date_list_item = soup.select_one('ul.infomation li i.icon-clock-o')
        if date_list_item:
            parent_li = date_list_item.find_parent('li')
            if parent_li:
                date_text = parent_li.get_text(strip=True)
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
            extracted_fallback = extract(html_content) # 변경된 _fetch_html_for_hidoc의 결과를 사용
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