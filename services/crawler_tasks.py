# ai-content-marketing-tool/services/crawler_tasks.py

import os
import logging
import numpy as np 
import json 

from flask import current_app 

# services/ 디렉토리로 옮겨진 모듈들을 임포트합니다.
from services.rag_system import get_rag_system, init_rag_system 
from services.ai_service import get_ai_content_generator 
from services.web_content_extractor import (
    extract_text_from_url, 
    extract_urls_from_itworld_list_page, 
    extract_urls_from_fashionbiz_list_page, 
    extract_urls_from_10000recipe_list_page, 
    extract_recipe_details_from_10000recipe, 
    extract_article_details_from_itworld,
    extract_urls_from_hidoc_list_page, 
    extract_article_details_from_hidoc,
    extract_urls_from_tlnews_list_page,
    extract_article_details_from_tlnews,
    extract_urls_from_beautynury_list_page,
    extract_article_details_from_beautynury
)
from services.web_utils import sanitize_filename

logger = logging.getLogger(__name__)

# --- 크롤러 함수 맵 (웹사이트별 URL 추출 함수 매핑) ---
CRAWLER_FUNCS = {
    "itworld": extract_urls_from_itworld_list_page,
    "fashionbiz": extract_urls_from_fashionbiz_list_page,
    "10000recipe": extract_urls_from_10000recipe_list_page,
    "hidoc": extract_urls_from_hidoc_list_page,
    "tlnews": extract_urls_from_tlnews_list_page,
    "beautynury": extract_urls_from_beautynury_list_page 
}


# --- 크롤링 핵심 로직 함수 (스케줄러에서 호출될 함수) ---
def perform_marketing_crawl_task():
    """
    사전 정의된 뉴스 목록 URL들을 크롤링하여 기사들을 지식 베이스에 자동으로 추가합니다.
    이 함수는 Flask 앱 컨텍스트 내에서 호출되어야 합니다.
    """
    KNOWLEDGE_BASE_DIR = os.path.join(current_app.root_path, 'knowledge_base')
    os.makedirs(KNOWLEDGE_BASE_DIR, exist_ok=True) 

    logger.info("--- 뉴스 크롤링 작업 시작 (스케줄러 호출) ---")
    crawled_count = 0
    total_urls_processed = 0
    failed_urls = []

    # 1. 크롤링할 뉴스 목록 설정들을 파일에서 읽어오기
    crawler_urls_file_path = os.path.join(current_app.root_path, 'knowledge_base', 'crawler_urls.json')
    
    category_to_urls_map = {} 
    try:
        if os.path.exists(crawler_urls_file_path):
            with open(crawler_urls_file_path, 'r', encoding='utf-8') as f:
                category_to_urls_map = json.load(f) 
            logger.info(f"'{crawler_urls_file_path}'에서 {len(category_to_urls_map)}개의 카테고리 크롤링 컨피그 로드됨.")
        else:
            logger.error(f"크롤링 대상 URL 파일 '{crawler_urls_file_path}'를 찾을 수 없습니다. 크롤링 작업을 건너뜁니다.")
            return {"message": "크롤링 대상 URL 파일 없음", "crawled_count": 0, "failed_urls": []}
    except Exception as e:
        logger.error(f"크롤링 대상 URL 파일 로드 중 오류 발생: {e}", exc_info=True)
        return {"error": f"크롤링 대상 URL 파일 로드 오류: {e}", "crawled_count": 0, "failed_urls": []}

    # 각 카테고리(키)와 해당 URL 목록(값)에 대해 반복
    for target_category, urls_list_for_category in category_to_urls_map.items(): 
        # 각 카테고리별로 디렉토리가 있는지 확인하고 없으면 생성합니다.
        os.makedirs(os.path.join(KNOWLEDGE_BASE_DIR, target_category), exist_ok=True)

        for url_to_crawl_entry in urls_list_for_category: # <--- 변수명 변경 (url_to_crawl_entry는 이제 순수한 URL 문자열입니다)
            # URL 기반 crawler_type 추론 (JSON 파일에 crawler_type이 없으므로 URL에서 추론)
            crawler_type = "unknown" 
            if "itworld.co.kr" in url_to_crawl_entry:
                crawler_type = "itworld"
            elif "fashionbiz.co.kr" in url_to_crawl_entry:
                crawler_type = "fashionbiz"
            elif "10000recipe.com" in url_to_crawl_entry: 
                crawler_type = "10000recipe"
            elif "news.hidoc.co.kr" in url_to_crawl_entry: 
                crawler_type = "hidoc"
            elif "tlnews.co.kr" in url_to_crawl_entry: # TLNews 타입 추론 추가
                crawler_type = "tlnews"
            elif "beautynury.com" in url_to_crawl_entry:
                crawler_type = "beautynury"
            
            if not crawler_type or crawler_type == "unknown":
                logger.warning(f"URL '{url_to_crawl_entry}'에 대한 크롤러 타입을 추론할 수 없습니다. 건너뜁니다.")
                failed_urls.append(f"크롤러 타입 추론 오류: {url_to_crawl_entry}")
                continue

            logger.info(f"뉴스 목록 페이지 크롤링 시작: {url_to_crawl_entry} (대상 카테고리: {target_category}, 크롤러 타입: {crawler_type})")
            try:
                # 1. 뉴스 목록 페이지에서 개별 기사 URL 추출 (크롤러 타입에 따라 함수 선택)
                article_urls_to_crawl_from_list = []
                if crawler_type.lower() in CRAWLER_FUNCS:
                    article_urls_to_crawl_from_list = CRAWLER_FUNCS[crawler_type.lower()](url_to_crawl_entry)
                else:
                    logger.error(f"정의되지 않은 크롤러 타입 '{crawler_type}'. URL 추출을 건너뜁니다.")
                    failed_urls.append(f"크롤러 타입 오류: {url_to_crawl_entry}")
                    continue
                
                if not article_urls_to_crawl_from_list: # <--- 이 부분의 변수명 변경
                    logger.warning(f"'{url_to_crawl_entry}'에서 추출할 기사 URL이 없습니다.") # <--- 이 부분의 변수명 변경
                    continue 

                # 2. 추출된 각 기사 URL에 대해 지식 베이스에 추가
                # !!! 테스트 용도: 각 목록 페이지에서 추출된 URL 중 처음 2개만 처리합니다. !!!
                for url in article_urls_to_crawl_from_list[:2]: # <-- 이 부분을 추가했습니다
                #for url in article_urls_to_crawl_from_list:
                    total_urls_processed += 1
                    try:
                        # --- 웹사이트 타입에 따른 상세 추출 및 포매팅 로직 ---
                        article_title = ""
                        article_content_str = ""

                        if crawler_type.lower() == "10000recipe":
                            recipe_data = extract_recipe_details_from_10000recipe(url) 
                            if not recipe_data:
                                failed_urls.append(f"{url} (레시피 상세 추출 실패)")
                                continue
                            
                            article_title = recipe_data.get('title', '제목 없음')
                            article_content_str = f"제목: {article_title}\n\n" 
                            
                            ingredients = recipe_data.get('ingredients', [])
                            if ingredients:
                                article_content_str += "재료:\n" + "\n".join([f"- {ing}" for ing in ingredients]) + "\n\n"
                            
                            steps = recipe_data.get('steps', [])
                            if steps:
                                article_content_str += "조리순서:\n" + "\n".join([f"STEP {i+1}. {step}" for i, step in enumerate(steps)]) + "\n"
                            

                        elif crawler_type.lower() == "itworld":
                            itworld_article_data = extract_article_details_from_itworld(url) 
                            if not itworld_article_data:
                                failed_urls.append(f"{url} (ITWorld 기사 상세 추출 실패)")
                                continue
                            
                            article_title = itworld_article_data.get('title', '제목 없음')
                            article_content_str = f"제목: {article_title}\n\n" 
                            
                            author = itworld_article_data.get('author', '작성자 불명')
                            date = itworld_article_data.get('date', '날짜 불명')
                            content_body = itworld_article_data.get('content', '')

                            if author != "작성자 불명":
                                article_content_str += f"작성자: {author}\n"
                            if date != "날짜 불명":
                                article_content_str += f"날짜: {date}\n\n"
                            
                            article_content_str += content_body

                        elif crawler_type.lower() == "fashionbiz": 
                            extracted_data = extract_text_from_url(url) 
                            if not extracted_data:
                                failed_urls.append(f"{url} (Fashionbiz 콘텐츠 추출 실패)")
                                continue
                            
                            article_title = extracted_data['title'] 
                            article_content_str = extracted_data['content'] 
                            
                        elif crawler_type.lower() == "hidoc": 
                            hidoc_article_data = extract_article_details_from_hidoc(url)
                            if not hidoc_article_data:
                                failed_urls.append(f"{url} (하이닥 기사 상세 추출 실패)")
                                continue
                            
                            article_title = hidoc_article_data.get('title', '제목 없음')
                            article_content_str = f"제목: {article_title}\n\n"
                            
                            author = hidoc_article_data.get('author', '작성자 불명')
                            date = hidoc_article_data.get('date', '날짜 불명')
                            content_body = hidoc_article_data.get('content', '')

                            if author != "작성자 불명":
                                article_content_str += f"작성자: {author}\n"
                            if date != "날짜 불명":
                                article_content_str += f"날짜: {date}\n\n"
                            
                            article_content_str += content_body
                        
                        elif crawler_type.lower() == "tlnews": # TLNews 상세 추출 로직 추가
                            tlnews_article_data = extract_article_details_from_tlnews(url)
                            if not tlnews_article_data:
                                failed_urls.append(f"{url} (TLNews 기사 상세 추출 실패)")
                                continue

                            article_title = tlnews_article_data.get('title', '제목 없음')
                            article_content_str = f"제목: {article_title}\n\n"

                            author = tlnews_article_data.get('author', '작성자 불명')
                            date = tlnews_article_data.get('date', '날짜 불명')
                            content_body = tlnews_article_data.get('content', '')

                            if author != "작성자 불명":
                                article_content_str += f"작성자: {author}\n"
                            if date != "날짜 불명":
                                article_content_str += f"날짜: {date}\n\n"

                            article_content_str += content_body
                        
                        elif crawler_type.lower() == "beautynury": # Beautynury 상세 추출 로직 추가
                            beautynury_article_data = extract_article_details_from_beautynury(url)
                            if not beautynury_article_data:
                                failed_urls.append(f"{url} (Beautynury 기사 상세 추출 실패)")
                                continue
                            
                            article_title = beautynury_article_data.get('title', '제목 없음')
                            article_content_str = f"제목: {article_title}\n\n"
                            
                            author = beautynury_article_data.get('author', '작성자 불명')
                            date = beautynury_article_data.get('date', '날짜 불명')
                            content_body = beautynury_article_data.get('content', '')

                            if author != "작성자 불명":
                                article_content_str += f"작성자: {author}\n"
                            if date != "날짜 불명":
                                article_content_str += f"날짜: {date}\n\n"
                            
                            article_content_str += content_body

                        else: # 알 수 없는 크롤러 타입인 경우 (혹은 기본 처리)
                            logger.warning(f"정의되지 않은 상세 추출 타입 '{crawler_type}'. 일반 콘텐츠 추출 시도: {url}")
                            extracted_data = extract_text_from_url(url) 
                            if not extracted_data:
                                failed_urls.append(f"{url} (콘텐츠 추출 실패)")
                                continue
                            article_title = extracted_data['title']
                            article_content_str = extracted_data['content']
                        
                        
                        
                        # --- 웹사이트 타입에 따른 상세 추출 및 포매팅 로직 끝 ---

                        closest_industry_folder = target_category 
                        logger.info(f"URL '{url}'의 콘텐츠가 '{target_category}' 업종으로 배정합니다.")
                        
                        # 파일 저장 경로 결정 및 저장
                        KNOWLEDGE_BASE_DIR = os.path.join(current_app.root_path, 'knowledge_base')
                        target_dir = os.path.join(KNOWLEDGE_BASE_DIR, closest_industry_folder)
                        os.makedirs(target_dir, exist_ok=True) 

                        base_filename = sanitize_filename(article_title, url) 
                        final_filename = base_filename
                        filepath = os.path.join(target_dir, final_filename)

                        counter = 1
                        while os.path.exists(filepath):
                            name_without_ext, ext = os.path.splitext(base_filename) 
                            final_filename = f"{name_without_ext}_{counter}{ext}"
                            filepath = os.path.join(target_dir, final_filename)
                            counter += 1

                        with open(filepath, 'w', encoding='utf-8') as f:
                            f.write(article_content_str) 
                        
                        logger.info(f"URL '{url}'의 콘텐츠가 '{closest_industry_folder}/{final_filename}'으로 저장되었습니다.")
                        crawled_count += 1

                    except Exception as e:
                        failed_urls.append(f"{url} (개별 기사 저장 실패: {e})")
                        logger.error(f"개별 기사 크롤링 및 저장 실패: {url} - {e}", exc_info=True)
                        continue
            except Exception as e:
                logger.error(f"뉴스 목록 페이지 '{url_to_crawl_entry}' 크롤링 중 오류 발생: {e}", exc_info=True) # <--- 변수명 변경
                failed_urls.append(f"목록 페이지 '{url_to_crawl_entry}' 처리 실패: {e}") # <--- 변수명 변경
                continue

    if crawled_count > 0: 
        bedrock_runtime_client = current_app.extensions['rag_bedrock_runtime']
        init_rag_system(bedrock_runtime_client)
    
    message = f"총 {total_urls_processed}개의 기사 URL을 처리하여 {crawled_count}개의 기사가 성공적으로 크롤링되어 지식 베이스에 추가되었습니다."
    if failed_urls:
        message += f" 다음 URL들은 실패했습니다: {'; '.join(failed_urls)}"
        logger.warning(message)

    logger.info(f"--- 뉴스 크롤링 작업 완료. {crawled_count}개 기사 크롤링 성공. ---")
    return {"message": message, "crawled_count": crawled_count, "failed_urls": failed_urls}