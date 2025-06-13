# services/web_crawling/extractors/tlnews.py
import re
from .base_extractor import BaseExtractor, BeautifulSoup, logger, extract 

class TLNewsExtractor(BaseExtractor):
    """tlnews.co.kr 웹사이트에서 콘텐츠를 추출하는 클래스."""
    BASE_URL = "https://www.tlnews.co.kr"

    def get_list_page_urls(self, list_page_url: str) -> list[str]:
        """tlnews.co.kr의 뉴스 목록 페이지에서 기사 URL들을 추출합니다."""
        article_urls = []
        html_content = self._fetch_html(list_page_url, use_selenium=False)
        if not html_content:
            return []

        soup = BeautifulSoup(html_content, 'html.parser')

        for li_tag in soup.find_all('li'):
            for a_tag in li_tag.find_all('a', href=True):
                href = a_tag.get('href')
                if href and href.startswith('/news/articleView.html?idxno=') and re.match(r'/news/articleView\.html\?idxno=\d+$', href):
                    full_url = self.BASE_URL + href
                    article_urls.append(full_url)
        
        article_urls = list(set(article_urls))
        logger.info(f"Successfully extracted {len(article_urls)} URLs from {list_page_url} (TLNews)")
        return article_urls

    def get_article_details(self, article_url: str) -> dict | None:
        """tlnews.co.kr의 기사 상세 페이지에서 제목, 본문, 작성자, 작성 날짜를 추출합니다."""
        html_content = self._fetch_html(article_url, use_selenium=False)
        if not html_content:
            return None

        soup = BeautifulSoup(html_content, 'html.parser')

        # 1. 기사 제목 추출
        title = "제목 없음"
        title_tag = soup.find('h3', class_='heading')
        if title_tag:
            title = title_tag.get_text(strip=True)
        logger.info(f"TLNews 기사 제목 추출: {title}")

        # 2. 작성자 추출
        author = "작성자 불명"
        author_list_item = soup.select_one('ul.infomation li i.icon-user-o')
        if author_list_item:
            parent_li = author_list_item.find_parent('li')
            if parent_li:
                for span_tag in parent_li.find_all('span', class_='show-for-sr'):
                    span_tag.decompose()
                author_text = parent_li.get_text(strip=True)
                author = author_text.strip()
        logger.info(f"TLNews 기사 작성자 추출: {author}")

        # 3. 작성 날짜 추출
        date_str = "날짜 불명"
        date_list_item = soup.select_one('ul.infomation li i.icon-clock-o')
        if date_list_item:
            parent_li = date_list_item.find_parent('li')
            if parent_li:
                date_text = parent_li.get_text(strip=True)
                date_match = re.search(r'\d{4}\.\d{2}\.\d{2}', date_text)
                if date_match:
                    date_str = date_match.group(0)
        logger.info(f"TLNews 기사 날짜 추출: {date_str}")

        # 4. 기사 본문 추출
        article_content_full = ""
        article_body_container = soup.find('div', id='article-view-content-div')
        if article_body_container:
            for ad_div in article_body_container.find_all('div', class_='google-auto-placed'):
                ad_div.decompose()
            for script_tag in article_body_container.find_all('script'):
                script_tag.decompose()

            paragraphs = []
            for tag in article_body_container.find_all(['p', 'h1', 'h2', 'h3', 'h4', 'ul', 'li', 'strong']):
                text = tag.get_text(separator=' ', strip=True)
                if text:
                    paragraphs.append(text)

            article_content_full = "\n\n".join(paragraphs).strip()

        if not article_content_full:
            logger.warning(f"TLNews: BeautifulSoup로 본문 추출 실패, trafilatura로 시도: {article_url}")
            extracted_fallback = extract(html_content)
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