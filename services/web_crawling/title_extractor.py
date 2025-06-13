import logging
from bs4 import BeautifulSoup, Tag

logger = logging.getLogger(__name__)

class TitleExtractor:
    """
    HTML 콘텐츠에서 제목을 추출하는 유틸리티 클래스입니다.
    다양한 전략(OG/Twitter 메타태그, 커스텀 셀렉터, 일반적인 HTML 태그)을 사용하여 제목을 찾습니다.
    """

    @staticmethod
    def extract_title(html_content: str, custom_selectors: list = None) -> str:
        """
        주어진 HTML 콘텐츠에서 가장 적합한 제목을 추출합니다.
        
        우선순위:
        1. Open Graph (og:title) 또는 Twitter Card (twitter:title) 메타태그
        2. 제공된 custom_selectors (튜플: (태그명, 클래스명), 문자열: 태그명)
        3. 일반적인 기사 제목 태그 (h1.itemTitle, h1.card__title, h1, h2, h3)
        4. HTML <title> 태그
        5. 기본값 "Untitled Article"
        
        Args:
            html_content: 제목을 추출할 HTML 문자열.
            custom_selectors: 특정 웹사이트를 위한 커스텀 제목 CSS 셀렉터 목록.
                              예: [('h1', 'article-title'), 'h2']
            
        Returns:
            추출된 제목 문자열.
        """
        if not html_content:
            return "Untitled Article"

        soup = BeautifulSoup(html_content, 'html.parser')
        page_title = "Untitled Article"

        # 1. Open Graph / Twitter Card 메타태그 시도
        og_title = soup.find('meta', property='og:title') or soup.find('meta', attrs={'name': 'twitter:title'})
        if og_title and og_title.get('content'):
            page_title = og_title['content'].strip()
            logger.debug(f"Title found via OG/Twitter meta: '{page_title}'")
            return page_title # 가장 정확하므로 바로 반환

        # 2. 커스텀 셀렉터 시도 (제공된 경우)
        if custom_selectors:
            for selector_args in custom_selectors:
                title_tag = None
                if isinstance(selector_args, tuple) and len(selector_args) == 2: # (tag_name, class_name)
                    title_tag = soup.find(selector_args[0], class_=selector_args[1])
                elif isinstance(selector_args, str): # tag_name
                    title_tag = soup.find(selector_args)
                
                if title_tag:
                    extracted_title = title_tag.get_text(strip=True)
                    if extracted_title:
                        logger.debug(f"Title found via custom selector '{selector_args}': '{extracted_title}'")
                        return extracted_title

        # 3. 일반적인 기사 제목 태그 시도 (h1, h2, h3)
        article_title_tag = soup.find('h1', class_='itemTitle') or \
                            soup.find('h1', class_='card__title') or \
                            soup.find('h1') or \
                            soup.find('h2') or \
                            soup.find('h3')
        if article_title_tag:
            extracted_title = article_title_tag.get_text(strip=True)
            if extracted_title:
                logger.debug(f"Title found via common article tag: '{extracted_title}'")
                return extracted_title

        # 4. HTML <title> 태그 시도
        title_tag_in_head = soup.find('title')
        if title_tag_in_head:
            extracted_title = title_tag_in_head.get_text(strip=True)
            if extracted_title:
                logger.debug(f"Title found via <title> tag: '{extracted_title}'")
                return extracted_title

        logger.warning("No specific title found. Returning 'Untitled Article'.")
        return "Untitled Article"