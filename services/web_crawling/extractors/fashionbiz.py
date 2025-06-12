# services/web_crawling/extractors/fashionbiz.py (수정)

from .base_extractor import BaseExtractor, BeautifulSoup, re, logger, WebDriverWait, EC, By

class FashionbizExtractor(BaseExtractor):
    """Fashionbiz.co.kr 웹사이트에서 콘텐츠를 추출하는 클래스."""
    BASE_URL = "https://fashionbiz.co.kr"

    def get_list_page_urls(self, list_page_url: str) -> list[str]:
        """Fashionbiz.co.kr의 뉴스 목록 페이지에서 기사 URL들을 추출합니다. Selenium 사용."""
        article_urls = []
        html_content = self._fetch_html(list_page_url, use_selenium=True) # Selenium 사용
        if not html_content:
            return []

        soup = BeautifulSoup(html_content, 'html.parser')
        
        for article_div in soup.find_all('div', class_='sc-53c9553f-0 ksjCKq'):
            a_tag = article_div.find('a', href=True)
            if a_tag:
                href = a_tag.get('href')
                if href and re.match(r'^/article/\d+$', href):
                    full_url = self.BASE_URL + href
                    article_urls.append(full_url)
        
        article_urls = list(set(article_urls))
        logger.info(f"Successfully extracted {len(article_urls)} URLs from {list_page_url} (Fashionbiz, Selenium)")
        return article_urls

    def get_article_details(self, article_url: str) -> dict | None:
        """Fashionbiz 기사 상세 페이지에서 제목, 본문 등을 추출합니다."""
        html_content = self._fetch_html(article_url, use_selenium=False) # 상세 페이지는 Requests로 시도
        if not html_content:
            return None

        # BaseExtractor의 범용 추출 로직을 사용합니다.
        extracted_data = self._extract_main_content(html_content, article_url)

        if extracted_data and extracted_data.get('title'):
            # Fashionbiz 고유의 제목 정제 로직 적용
            title = extracted_data['title']
            if title.startswith("패션비즈 | "):
                title = title.replace("패션비즈 | ", "").strip()
                logger.info(f"Fashionbiz 제목에서 '패션비즈 | ' 접두어 제거: {title}")
                extracted_data['title'] = title
        
        # Fashionbiz는 작성자/날짜가 본문과 함께 추출되는 경우가 많으므로 별도 파싱 로직이 없다면 content만 활용
        # 필요하다면 여기에 추가적인 BeautifulSoup 파싱 로직을 추가할 수 있습니다.
        # 예시:
        # soup = BeautifulSoup(html_content, 'html.parser')
        # author_tag = soup.find('span', class_='author') # 예시 셀렉터
        # if author_tag:
        #     extracted_data['author'] = author_tag.get_text(strip=True)

        return extracted_data