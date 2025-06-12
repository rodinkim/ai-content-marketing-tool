# ai-content-marketing-tool/services/web_crawling/crawler_tasks.py

import os
import logging
import numpy as np # 현재 코드에서는 사용되지 않지만, 기존에 있었으므로 유지
import json
from urllib.parse import urlparse # URL 파싱을 위해 추가

from flask import current_app

# services 디렉토리로 옮겨진 모듈들을 임포트합니다.
# 경로 변경
from services.ai_rag.rag_system import get_rag_system, init_rag_system
from services.ai_rag.ai_service import get_ai_content_generator
# web_content_extractor에서 필요한 함수만 임포트합니다.
# 이제 개별 추출 함수들은 각 Extractor 클래스의 메서드로 대체되었습니다.
from services.web_crawling.web_content_extractor import (
    get_specific_extractor, # 특정 URL에 맞는 Extractor 인스턴스를 가져오는 함수
    extract_text_from_url # 범용적인 텍스트 추출 함수 (폴백용)
)
from services.web_crawling.web_utils import sanitize_filename

logger = logging.getLogger(__name__)

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

        for url_to_crawl_entry in urls_list_for_category:
            # URL에서 도메인 추출 및 크롤러 타입 추론
            parsed_url = urlparse(url_to_crawl_entry)
            domain = parsed_url.netloc
            if domain.startswith("www."):
                domain = domain[4:] # "www." 제거하여 핵심 도메인만 사용

            # 해당 도메인에 맞는 Extractor 인스턴스 가져오기
            extractor = get_specific_extractor(url_to_crawl_entry) # 이제 web_content_extractor.py의 get_specific_extractor 사용

            if not extractor:
                logger.warning(f"URL '{url_to_crawl_entry}'에 대한 특정 크롤러를 찾을 수 없습니다. 건너뜁니다.")
                failed_urls.append(f"크롤러 없음: {url_to_crawl_entry}")
                continue

            logger.info(f"뉴스 목록 페이지 크롤링 시작: {url_to_crawl_entry} (대상 카테고리: {target_category}, Extractor: {type(extractor).__name__})")
            try:
                # 1. 뉴스 목록 페이지에서 개별 기사 URL 추출 (Extractor 인스턴스의 메서드 호출)
                article_urls_to_crawl_from_list = extractor.get_list_page_urls(url_to_crawl_entry)
                
                if not article_urls_to_crawl_from_list:
                    logger.warning(f"'{url_to_crawl_entry}'에서 추출할 기사 URL이 없습니다.")
                    continue

                # 2. 추출된 각 기사 URL에 대해 지식 베이스에 추가
                # !!! 테스트 용도: 각 목록 페이지에서 추출된 URL 중 처음 2개만 처리합니다. !!!
                for url in article_urls_to_crawl_from_list[:2]:
                # for url in article_urls_to_crawl_from_list: # 모든 URL을 처리하려면 이 줄을 사용하세요.
                    total_urls_processed += 1
                    try:
                        # --- 웹사이트 타입에 따른 상세 추출 및 포매팅 로직 ---
                        # 이제 모든 상세 추출은 Extractor 인스턴스의 get_article_details 메서드를 통해 이루어집니다.
                        extracted_data = extractor.get_article_details(url)
                        
                        if not extracted_data:
                            failed_urls.append(f"{url} (상세 콘텐츠 추출 실패 - Extractor: {type(extractor).__name__})")
                            continue
                        
                        article_title = extracted_data.get('title', '제목 없음')
                        article_content_str = f"제목: {article_title}\n\n"

                        # 레시피와 일반 기사의 포맷을 통합하여 처리 (또는 필요에 따라 조건부 처리)
                        if 'ingredients' in extracted_data and 'steps' in extracted_data: # 10000recipe와 같은 레시피 데이터
                            ingredients = extracted_data.get('ingredients', [])
                            if ingredients:
                                article_content_str += "재료:\n" + "\n".join([f"- {ing}" for ing in ingredients]) + "\n\n"
                            
                            steps = extracted_data.get('steps', [])
                            if steps:
                                article_content_str += "조리순서:\n" + "\n".join([f"STEP {i+1}. {step}" for i, step in enumerate(steps)]) + "\n"
                        else: # 일반 기사 데이터 (ITWorld, HiDoc, TLNews, Beautynury, Fashionbiz)
                            author = extracted_data.get('author', '작성자 불명')
                            date = extracted_data.get('date', '날짜 불명')
                            content_body = extracted_data.get('content', '')

                            if author and author != "작성자 불명":
                                article_content_str += f"작성자: {author}\n"
                            if date and date != "날짜 불명":
                                article_content_str += f"날짜: {date}\n\n"
                            
                            article_content_str += content_body
                        
                        # --- 웹사이트 타입에 따른 상세 추출 및 포매팅 로직 끝 ---

                        closest_industry_folder = target_category
                        logger.info(f"URL '{url}'의 콘텐츠가 '{target_category}' 업종으로 배정합니다.")
                        
                        # 파일 저장 경로 결정 및 저장
                        # KNOWLEDGE_BASE_DIR은 함수 시작 부분에 이미 정의되어 있습니다.
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
                logger.error(f"뉴스 목록 페이지 '{url_to_crawl_entry}' 크롤링 중 오류 발생: {e}", exc_info=True)
                failed_urls.append(f"목록 페이지 '{url_to_crawl_entry}' 처리 실패: {e}")
                continue

    if crawled_count > 0:
        # RAG 시스템 초기화 (지식 베이스 업데이트 후 필요)
        bedrock_runtime_client = current_app.extensions['rag_bedrock_runtime']
        init_rag_system(bedrock_runtime_client)
    
    message = f"총 {total_urls_processed}개의 기사 URL을 처리하여 {crawled_count}개의 기사가 성공적으로 크롤링되어 지식 베이스에 추가되었습니다."
    if failed_urls:
        message += f" 다음 URL들은 실패했습니다: {'; '.join(failed_urls)}"
        logger.warning(message)

    logger.info(f"--- 뉴스 크롤링 작업 완료. {crawled_count}개 기사 크롤링 성공. ---")
    return {"message": message, "crawled_count": crawled_count, "failed_urls": failed_urls}