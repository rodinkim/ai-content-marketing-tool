import os
import logging
import json
from urllib.parse import urlparse

from flask import current_app

from services.ai_rag.rag_system import get_rag_system, init_rag_system
from services.ai_rag.ai_service import get_ai_content_generator

from services.web_crawling.web_content_extractor import (
    get_specific_extractor # 특정 URL에 맞는 Extractor 인스턴스를 가져오는 함수
)
from services.web_crawling.web_utils import sanitize_filename

logger = logging.getLogger(__name__)

# --- 헬퍼 함수 정의 ---

def _load_crawler_configs(file_path: str) -> dict | None:
    """크롤링 설정 파일을 로드합니다."""
    try:
        if os.path.exists(file_path):
            with open(file_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
            logger.info(f"'{file_path}'에서 {len(config)}개의 카테고리 크롤링 컨피그 로드됨.")
            return config
        else:
            logger.error(f"크롤링 대상 URL 파일 '{file_path}'를 찾을 수 없습니다.")
            return None
    except Exception as e:
        logger.error(f"크롤링 대상 URL 파일 로드 중 오류 발생: {e}", exc_info=True)
        return None

def _format_article_content(extracted_data: dict) -> str:
    """
    추출된 기사 데이터를 통합된 문자열 형식으로 포맷합니다.
    레시피와 일반 기사 데이터를 구분하여 처리합니다.
    """
    article_title = extracted_data.get('title', '제목 없음')
    article_content_str = f"제목: {article_title}\n\n"

    if 'ingredients' in extracted_data and 'steps' in extracted_data: # 레시피 데이터
        ingredients = extracted_data.get('ingredients', [])
        if ingredients:
            article_content_str += "재료:\n" + "\n".join([f"- {ing}" for ing in ingredients]) + "\n\n"
        
        steps = extracted_data.get('steps', [])
        if steps:
            article_content_str += "조리순서:\n" + "\n".join([f"STEP {i+1}. {step}" for i, step in enumerate(steps)]) + "\n"
    else: # 일반 기사 데이터
        author = extracted_data.get('author', '작성자 불명')
        date = extracted_data.get('date', '날짜 불명')
        content_body = extracted_data.get('content', '')

        if author and author != "작성자 불명":
            article_content_str += f"작성자: {author}\n"
        if date and date != "날짜 불명":
            article_content_str += f"날짜: {date}\n\n"
        
        article_content_str += content_body
    
    return article_content_str

def _save_article_to_knowledge_base(
    article_title: str, 
    article_content_str: str, 
    url: str, 
    target_category: str, 
    knowledge_base_dir: str
) -> bool:
    """
    크롤링된 기사를 지식 베이스에 파일로 저장합니다.
    파일 이름 충돌 시 숫자를 붙여 처리합니다.
    """
    try:
        target_dir = os.path.join(knowledge_base_dir, target_category)
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
        
        logger.info(f"URL '{url}'의 콘텐츠가 '{target_category}/{final_filename}'으로 저장되었습니다.")
        return True
    except Exception as e:
        logger.error(f"개별 기사 저장 중 오류 발생: {url} - {e}", exc_info=True)
        return False

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

    # 1. 크롤링 설정 로드
    crawler_urls_file_path = os.path.join(current_app.root_path, 'knowledge_base', 'crawler_urls.json')
    category_to_urls_map = _load_crawler_configs(crawler_urls_file_path)
    if category_to_urls_map is None:
        return {"message": "크롤링 대상 URL 파일 없음 또는 로드 실패", "crawled_count": 0, "failed_urls": []}

    # 각 카테고리(키)와 해당 URL 목록(값)에 대해 반복
    for target_category, urls_list_for_category in category_to_urls_map.items():
        os.makedirs(os.path.join(KNOWLEDGE_BASE_DIR, target_category), exist_ok=True)

        for url_to_crawl_entry in urls_list_for_category:
            extractor = get_specific_extractor(url_to_crawl_entry)

            if not extractor:
                logger.warning(f"URL '{url_to_crawl_entry}'에 대한 특정 크롤러를 찾을 수 없습니다. 건너뜁니다.")
                failed_urls.append(f"크롤러 없음: {url_to_crawl_entry}")
                continue

            logger.info(f"뉴스 목록 페이지 크롤링 시작: {url_to_crawl_entry} (대상 카테고리: {target_category}, Extractor: {type(extractor).__name__})")
            try:
                article_urls_to_crawl_from_list = extractor.get_list_page_urls(url_to_crawl_entry)
                
                if not article_urls_to_crawl_from_list:
                    logger.warning(f"'{url_to_crawl_entry}'에서 추출할 기사 URL이 없습니다.")
                    continue

                # !!! 테스트 용도: 각 목록 페이지에서 추출된 URL 중 처음 2개만 처리합니다. !!!
                for url in article_urls_to_crawl_from_list[:2]:
                # for url in article_urls_to_crawl_from_list: # 모든 URL을 처리하려면 이 줄을 사용하세요.
                    total_urls_processed += 1
                    
                    extracted_data = None
                    try:
                        extracted_data = extractor.get_article_details(url)
                    except Exception as e:
                        logger.error(f"개별 기사 크롤링 실패: {url} - {e}", exc_info=True)
                        failed_urls.append(f"{url} (상세 콘텐츠 추출 실패 - Extractor: {type(extractor).__name__})")
                        continue # 다음 URL로 넘어감
                    
                    if not extracted_data:
                        failed_urls.append(f"{url} (상세 콘텐츠 추출 실패 - Extractor: {type(extractor).__name__})")
                        continue

                    # 기사 내용 포맷팅
                    article_content_str = _format_article_content(extracted_data)
                    
                    # 지식 베이스에 저장
                    if _save_article_to_knowledge_base(
                        extracted_data.get('title', '제목 없음'), 
                        article_content_str, 
                        url, 
                        target_category, 
                        KNOWLEDGE_BASE_DIR
                    ):
                        crawled_count += 1
                    else:
                        # _save_article_to_knowledge_base 내부에서 이미 에러 로깅 처리됨
                        failed_urls.append(f"{url} (파일 저장 실패)")

            except Exception as e:
                logger.error(f"뉴스 목록 페이지 '{url_to_crawl_entry}' 크롤링 중 오류 발생: {e}", exc_info=True)
                failed_urls.append(f"목록 페이지 '{url_to_crawl_entry}' 처리 실패: {e}")
                continue

    # RAG 시스템 초기화 (크롤링된 콘텐츠가 있다면)
    if crawled_count > 0:
        try:
            bedrock_runtime_client = current_app.extensions['rag_bedrock_runtime']
            init_rag_system(bedrock_runtime_client)
            logger.info("RAG 시스템이 크롤링된 새 콘텐츠로 성공적으로 업데이트되었습니다.")
        except Exception as e:
            logger.error(f"RAG 시스템 업데이트 중 오류 발생: {e}", exc_info=True)
            failed_urls.append(f"RAG 시스템 업데이트 실패: {e}")
    else:
        logger.info("새로 크롤링된 콘텐츠가 없으므로 RAG 시스템을 업데이트하지 않습니다.")
    
    # 결과 요약 및 반환
    message = f"총 {total_urls_processed}개의 기사 URL을 처리하여 {crawled_count}개의 기사가 성공적으로 크롤링되어 지식 베이스에 추가되었습니다."
    if failed_urls:
        message += f" 다음 URL들은 실패했습니다: {'; '.join(failed_urls)}"
        logger.warning(message)

    logger.info(f"--- 뉴스 크롤링 작업 완료. {crawled_count}개 기사 크롤링 성공. ---")
    return {"message": message, "crawled_count": crawled_count, "failed_urls": failed_urls}