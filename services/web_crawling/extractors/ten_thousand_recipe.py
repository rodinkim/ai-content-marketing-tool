# services/web_crawling/extractors/ten_thousand_recipe.py

from .base_extractor import BaseExtractor, requests, BeautifulSoup, re, logger

class TenThousandRecipeExtractor(BaseExtractor):
    """10000recipe.com 웹사이트에서 레시피 콘텐츠를 추출하는 클래스."""
    BASE_URL = "https://www.10000recipe.com"

    def get_list_page_urls(self, list_page_url: str) -> list[str]:
        """10000recipe.com의 레시피 목록 페이지에서 레시피 URL들을 추출합니다."""
        article_urls = []
        html_content = self._fetch_html(list_page_url, use_selenium=False)
        if not html_content:
            return []

        soup = BeautifulSoup(html_content, 'html.parser')

        for a_tag in soup.find_all('a', class_='common_sp_link', href=True):
            href = a_tag.get('href')
            if href and re.match(r'^/recipe/\d+$', href):
                full_url = self.BASE_URL + href
                article_urls.append(full_url)
        
        article_urls = list(set(article_urls))
        logger.info(f"Successfully extracted {len(article_urls)} URLs from {list_page_url} (10000recipe.com)")
        return article_urls

    def get_article_details(self, recipe_url: str) -> dict | None:
        """10000recipe.com의 레시피 상세 페이지에서 제목, 재료, 조리 순서를 추출합니다."""
        html_content = self._fetch_html(recipe_url, use_selenium=False)
        if not html_content:
            return None

        soup = BeautifulSoup(html_content, 'html.parser')

        # 1. 제목 추출 (<h3> 태그 사용)
        title_tag = soup.find('h3')
        title = title_tag.get_text(strip=True) if title_tag else "제목 없음"
        logger.info(f"레시피 제목 추출: {title}")

        # 2. 재료 목록 추출
        ingredients = []
        materials_container = soup.find('div', class_='ready_ingre3', id='divConfirmedMaterialArea')
        if materials_container:
            for ul_tag in materials_container.find_all('ul'):
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