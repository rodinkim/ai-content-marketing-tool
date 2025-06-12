# services/web_crawling/extractors/itworld.py

from .base_extractor import BaseExtractor, requests, BeautifulSoup, re, logger

class ITWorldExtractor(BaseExtractor):
    """ITWorld Korea 웹사이트에서 콘텐츠를 추출하는 클래스."""
    BASE_URL = "https://www.itworld.co.kr"

    def get_list_page_urls(self, list_page_url: str) -> list[str]:
        """ITWorld Korea의 뉴스 목록 페이지에서 기사 URL들을 추출합니다."""
        article_urls = []
        html_content = self._fetch_html(list_page_url, use_selenium=False) # ITWorld는 Selenium 필요 없음
        if not html_content:
            return []

        soup = BeautifulSoup(html_content, 'html.parser')

        for a_tag in soup.find_all('a', class_='grid content-row-article', href=True):
            href = a_tag.get('href')
            if href:
                # 절대 URL 처리
                if href.startswith(self.BASE_URL + '/article/') and re.match(r'https://www.itworld.co.kr/article/\d+/\S+\.html$', href):
                    article_urls.append(href)
                # 상대 URL 처리
                elif href.startswith('/article/') and re.match(r'^/article/\d+/\S+\.html$', href):
                    full_url = self.BASE_URL + href
                    article_urls.append(full_url)
        
        article_urls = list(set(article_urls))
        logger.info(f"Successfully extracted {len(article_urls)} URLs from {list_page_url} (ITWorld)")
        return article_urls

    def get_article_details(self, article_url: str) -> dict | None:
        """ITWorld 기사 상세 페이지에서 제목, 본문, 작성자, 작성 날짜를 추출합니다."""
        html_content = self._fetch_html(article_url, use_selenium=False)
        if not html_content:
            return None

        soup = BeautifulSoup(html_content, 'html.parser')

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
        date_span_tag = soup.find('span', itemprop='datePublished')
        if date_span_tag:
            date_str = date_span_tag.get_text(strip=True)
        else:
            date_span_tag = soup.find('span', text=re.compile(r'\d{4}\.\d{2}\.\d{2}')) #YYYY.MM.DD 패턴
            if date_span_tag:
                date_str = date_span_tag.get_text(strip=True)
        logger.info(f"ITWorld 기사 날짜 추출: {date_str}")

        # 4. 기사 본문 추출 (BaseExtractor의 _extract_main_content를 사용)
        # ITWorld는 상세 추출에 특정 구조가 있으므로 직접 구현하거나 _extract_main_content의 커스텀 셀렉터를 활용할 수 있음
        # 여기서는 기존 로직 유지하며 BaseExtractor의 fallback 활용
        article_content_full = ""
        content_divs = soup.find_all('div', class_='article-column__content')
        
        paragraphs = []
        for content_div in content_divs:
            for p_tag in content_div.find_all('p'):
                text = p_tag.get_text(strip=True)
                if text:
                    paragraphs.append(text)
            for heading_tag in content_div.find_all(['h2', 'h3']):
                text = heading_tag.get_text(strip=True)
                if text:
                    paragraphs.append(text)
            for ul_tag in content_div.find_all('ul'):
                for li_tag in ul_tag.find_all('li'):
                    text = li_tag.get_text(strip=True)
                    if text:
                        paragraphs.append(f"- {text}")
        
        article_content_full = "\n\n".join(paragraphs).strip()
        
        if not article_content_full:
            logger.warning(f"ITWorld: BeautifulSoup로 본문 추출 실패, trafilatura로 시도: {article_url}")
            extracted_fallback = extract(html_content)
            article_content_full = str(extracted_fallback) if extracted_fallback else ""

        if not article_content_full:
            logger.warning(f"ITWorld: 본문 추출 실패: {article_url}")
            return None

        return {
            'title': title,
            'content': article_content_full,
            'author': author,
            'date': date_str
        }