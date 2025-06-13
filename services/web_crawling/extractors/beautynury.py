# services/web_crawling/extractors/beautynury.py (수정)
import re 
from .base_extractor import BaseExtractor, BeautifulSoup, logger, extract
from ..web_utils import clean_beautynury_title # decode_html_content는 BaseExtractor로 이동했으므로 제거

class BeautynuryExtractor(BaseExtractor):
    """beautynury.com 웹사이트에서 콘텐츠를 추출하는 클래스."""
    BASE_URL = "https://www.beautynury.com"

    def get_list_page_urls(self, list_page_url: str) -> list[str]:
        """beautynury.com의 뉴스 목록 페이지에서 기사 URL들을 추출합니다."""
        article_urls = []
        
        # BaseExtractor의 _fetch_html에서 디코딩을 처리하므로, 여기서는 그냥 HTML 문자열을 받습니다.
        html_content = self._fetch_html(list_page_url, use_selenium=False)
        if not html_content:
            return []
        
        soup = BeautifulSoup(html_content, 'html.parser')

        for li_tag in soup.find_all('li'):
            a_tag = li_tag.find('a', href=re.compile(r'/news/view/\d+/cat/\d+/page/\d+'))
            if a_tag:
                href = a_tag.get('href')
                if href:
                    full_url = self.BASE_URL + href
                    article_urls.append(full_url)

        article_urls = list(set(article_urls))
        logger.info(f"Successfully extracted {len(article_urls)} URLs from {list_page_url} (Beautynury)")
        return article_urls

    def get_article_details(self, article_url: str) -> dict | None:
        """beautynury.com의 기사 상세 페이지에서 제목, 본문, 작성자, 작성 날짜를 추출합니다."""
        # BaseExtractor의 _fetch_html에서 디코딩을 처리하므로, 여기서는 그냥 HTML 문자열을 받습니다.
        html_content = self._fetch_html(article_url, use_selenium=False)
        if not html_content:
            return None

        soup = BeautifulSoup(html_content, 'html.parser')

        # 1. 기사 제목 추출
        title = "제목 없음"
        # BeautyNury는 <title> 태그가 가장 안정적이므로 우선 처리
        title_tag = soup.find('title')
        if title_tag:
            page_title = title_tag.get_text(strip=True)
            # clean_beautynury_title 함수로 제목 정제 (web_utils에서 임포트)
            title = clean_beautynury_title(page_title)
            
            # 정제 후 제목이 너무 짧거나 비어있을 경우, 폴백 로직
            if not title or len(title) < 5: 
                title_con_div = soup.find('div', class_='title_con')
                if title_con_div:
                    strong_tag = title_con_div.find('strong')
                    if strong_tag:
                        title = strong_tag.get_text(strip=True)
                    else:
                        full_title_text = title_con_div.get_text(separator=' ', strip=True)
                        span_tag = title_con_div.find('span')
                        if span_tag:
                            span_text = span_tag.get_text(strip=True)
                            temp_title = full_title_text.replace(span_text, '').strip()
                            if len(temp_title) > 5:
                                title = temp_title
                            else:
                                title = page_title
                        else:
                            title = full_title_text # span도 없으면 title_con_div의 모든 텍스트
                else:
                    title = page_title # title_con_div도 없으면 <title>에서 정제한 제목 사용
            
        logger.info(f"Beautynury 기사 제목 추출: {title}")

        # 2. 작성자 추출 (기존 로직 유지)
        author = "작성자 불명"
        name_con_div = soup.find('div', class_='name_con')
        if name_con_div:
            author_span = name_con_div.find('span')
            if author_span:
                author_text = author_span.get_text(strip=True)
                author = re.sub(r'\s*기자', '', author_text).strip()
                author = re.sub(r'[\r\n\t]+', '', author).strip()
        logger.info(f"Beautynury 기사 작성자 추출: {author}")

        # 3. 작성 날짜 추출 (기존 로직 유지)
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

        # 4. 기사 본문 추출 (BaseExtractor의 _extract_main_content를 사용)
        # Beautynury는 본문 추출에 특화된 요소가 있으므로 직접 구현합니다.
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
            # BaseExtractor의 _fetch_html에서 이미 디코딩된 HTML을 사용하므로,
            # 다시 `extract(decoded_html)`이 아닌 `extract(html_content)`를 사용합니다.
            extracted_fallback = extract(html_content) 
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