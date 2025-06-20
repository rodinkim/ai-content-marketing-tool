# ai-content-marketing-tool/services/web_crawling/crawler_tasks.py

import os
import logging
import json
from urllib.parse import urlparse
import boto3 # boto3 임포트 추가
from botocore.exceptions import ClientError

from flask import current_app # Flask 앱 컨텍스트에서 설정/확장 가져오기

from services.ai_rag.rag_system import get_rag_system, init_rag_system
from services.ai_rag.ai_service import get_ai_content_generator # 아직 사용되지 않을 수 있지만, 임포트 유지

from services.web_crawling.web_content_extractor import (
    get_specific_extractor # 특정 URL에 맞는 Extractor 인스턴스를 가져오는 함수
)
from services.web_crawling.web_utils import sanitize_filename

logger = logging.getLogger(__name__)

# --- S3 클라이언트 및 버킷 정보 가져오기 헬퍼 함수 ---
# knowledge_base_routes.py와 동일한 로직을 사용하지만, 의존성을 줄이기 위해 여기에 다시 정의
def _get_s3_info():
    """앱 확장(app.extensions)에서 S3 클라이언트와 버킷 이름을 가져와 반환합니다."""
    s3_client = current_app.extensions.get('s3_client')
    if not s3_client:
        logger.error("S3 client is not initialized in app.extensions.")
        raise RuntimeError("S3 client not available in crawler_tasks.")
    
    bucket_name = current_app.config.get('S3_BUCKET_NAME')
    if not bucket_name:
        logger.error("S3_BUCKET_NAME is not configured in app.config.")
        raise RuntimeError("S3 bucket name not configured in crawler_tasks.")
    
    return s3_client, bucket_name

# --- 헬퍼 함수 정의 ---

def _load_crawler_configs_from_s3(s3_client, bucket_name, s3_key: str) -> dict | None:
    """S3에서 크롤링 설정 파일을 로드합니다."""
    try:
        # S3에 파일이 존재하는지 확인
        s3_client.head_object(Bucket=bucket_name, Key=s3_key)
        
        response = s3_client.get_object(Bucket=bucket_name, Key=s3_key)
        config_content = response['Body'].read().decode('utf-8')
        config = json.loads(config_content)
        logger.info(f"S3 '{s3_key}'에서 {len(config)}개의 카테고리 크롤링 컨피그 로드됨.")
        return config
    except s3_client.exceptions.ClientError as e:
        error_code = e.response.get('Error', {}).get('Code')
        if error_code in ['NoSuchKey', 'NotFound']: # 파일이 없으면
            logger.error(f"크롤링 대상 URL 파일 '{s3_key}'를 S3에서 찾을 수 없습니다.")
            # 초기 설정을 위해 S3에 기본 crawler_urls.json을 업로드하는 가이드가 필요할 수 있음
        else:
            logger.error(f"S3 크롤링 대상 URL 파일 로드 중 오류 발생: {e}", exc_info=True)
        return None
    except Exception as e:
        logger.error(f"크롤링 대상 URL 파일 파싱 중 오류 발생: {e}", exc_info=True)
        return None

def _format_article_content(extracted_data: dict) -> str:
    """
    추출된 기사 데이터를 통합된 문자열 형식으로 포맷합니다.
    레시피와 일반 기사 데이터를 구분하여 처리합니다.
    (이 함수는 변경 없음)
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
        if date and date != "날명":
            article_content_str += f"날짜: {date}\n\n"
        
        article_content_str += content_body
    
    return article_content_str

def _save_article_to_s3_knowledge_base(
    s3_client,
    bucket_name: str,
    article_title: str,
    article_content_str: str,
    url: str,
    target_category: str # 이제 이 target_category가 S3의 최상위 폴더명이 됨
) -> bool:
    """
    크롤링된 기사를 S3 지식 베이스에 파일로 저장합니다.
    파일은 's3://<bucket_name>/<target_category>/<filename.txt>' 형태로 저장됩니다.
    파일 이름 충돌 시 숫자를 붙여 처리합니다.
    """
    try:
        base_filename = sanitize_filename(article_title, url)
        
        s3_object_key_prefix = target_category
        s3_object_key = f"{s3_object_key_prefix}/{base_filename}"

        counter = 1
        final_s3_object_key = s3_object_key
        while True:
            try:
                s3_client.head_object(Bucket=bucket_name, Key=final_s3_object_key)
                
                name, ext = os.path.splitext(base_filename)
                max_filename_len = 1024 - len(s3_object_key_prefix) - 1 - len(ext) - len(str(counter)) - 1
                if len(name) > max_filename_len:
                    name = name[:max_filename_len]
                final_s3_object_key = f"{s3_object_key_prefix}/{name}_{counter}{ext}"
                counter += 1
            # 수정된 부분: boto3.client.exceptions.ClientError 대신 botocore.exceptions.ClientError 사용
            except ClientError as e: # <-- 수정: boto3.client.exceptions.ClientError 대신 ClientError 사용
                http_status = e.response.get('ResponseMetadata', {}).get('HTTPStatusCode')
                if http_status == 404:
                    break
                else: 
                    logger.error(f"S3 HeadObject 알 수 없는 ClientError 발생 (HTTP {http_status}) for '{final_s3_object_key}': {e}", exc_info=True)
                    raise
            except Exception as e:
                logger.error(f"S3 HeadObject 예상치 못한 오류 발생 for '{final_s3_object_key}': {e}", exc_info=True)
                raise

        s3_client.put_object(Bucket=bucket_name, Key=final_s3_object_key, Body=article_content_str.encode('utf-8'))
        
        logger.info(f"URL '{url}'의 콘텐츠가 S3에 '{bucket_name}/{final_s3_object_key}'으로 저장되었습니다.")
        return True
    except Exception as e: # <-- 상위 Exception으로 ClientError도 잡히도록 변경
        # 모든 S3 관련 오류를 여기서 통합 로깅
        logger.error(f"S3에 개별 기사 저장 중 오류 발생: {url} - {e}", exc_info=True)
        return False

# --- 크롤링 핵심 로직 함수 (스케줄러에서 호출될 함수) ---
def perform_marketing_crawl_task():
    """
    사전 정의된 뉴스 목록 URL들을 크롤링하여 기사들을 S3 지식 베이스에 자동으로 추가합니다.
    이 함수는 Flask 앱 컨텍스트 내에서 호출되어야 합니다.
    """
    logger.info("--- 뉴스 크롤링 작업 시작 (스케줄러 호출) ---")
    s3_client, bucket_name = _get_s3_info()

    crawled_count = 0
    total_urls_processed = 0
    failed_urls = []

    # 1. 크롤링 설정 로드 (S3에서 로드)
    # 이 S3_KEY는 config.py에서 설정되어야 합니다.
    crawler_urls_s3_key = current_app.config.get('CRAWLER_URLS_S3_KEY', 'system_config/crawler_urls.json')
    category_to_urls_map = _load_crawler_configs_from_s3(s3_client, bucket_name, crawler_urls_s3_key)
    
    if category_to_urls_map is None:
        return {"message": "크롤링 대상 URL 파일 없음 또는 S3 로드 실패", "crawled_count": 0, "failed_urls": []}

    # 크롤링된 기사를 저장할 S3 사용자 폴더 설정은 더 이상 필요 없습니다.
    # 각 카테고리 자체가 최상위 폴더가 됩니다.
    # crawler_target_user_folder = current_app.config.get('CRAWLER_TARGET_USER_FOLDER', 'crawled_news')
    # if not crawler_target_user_folder:
    #     crawler_target_user_folder = 'crawled_news' 
    #     logger.warning("CRAWLER_TARGET_USER_FOLDER 설정이 없습니다. 'crawled_news' 폴더에 저장합니다.")

    # 각 카테고리(키)와 해당 URL 목록(값)에 대해 반복
    for target_category, urls_list_for_category in category_to_urls_map.items():
        # 로컬 폴더 생성 로직은 제거 (S3에 바로 저장됨)
        # os.makedirs(os.path.join(KNOWLEDGE_BASE_DIR, target_category), exist_ok=True) 

        for url_to_crawl_entry in urls_list_for_category:
            extractor = get_specific_extractor(url_to_crawl_entry)

            if not extractor:
                logger.warning(f"URL '{url_to_crawl_entry}'에 대한 특정 크롤러를 찾을 수 없습니다. 건너_입니다.")
                failed_urls.append(f"크롤러 없음: {url_to_crawl_entry}")
                continue

            logger.info(f"뉴스 목록 페이지 크롤링 시작: {url_to_crawl_entry} (대상 카테고리: {target_category}, Extractor: {type(extractor).__name__})")
            try:
                article_urls_to_crawl_from_list = extractor.get_list_page_urls(url_to_crawl_entry)
                
                if not article_urls_to_crawl_from_list:
                    logger.warning(f"'{url_to_crawl_entry}'에서 추출할 기사 URL이 없습니다.")
                    continue

                for url in article_urls_to_crawl_from_list[:2]: # 테스트 용도: 처음 2개만 처리
                    total_urls_processed += 1
                    
                    extracted_data = None
                    try:
                        extracted_data = extractor.get_article_details(url)
                    except Exception as e:
                        logger.error(f"개별 기사 크롤링 실패: {url} - {e}", exc_info=True)
                        failed_urls.append(f"{url} (상세 콘텐츠 추출 실패 - Extractor: {type(extractor).__name__})")
                        continue
                    
                    if not extracted_data:
                        failed_urls.append(f"{url} (상세 콘텐츠 추출 실패 - Extractor: {type(extractor).__name__})")
                        continue

                    # 기사 내용 포맷팅
                    article_content_str = _format_article_content(extracted_data)
                    
                    # S3 지식 베이스에 저장 (crawler_user_folder 인자 제거)
                    if _save_article_to_s3_knowledge_base(
                        s3_client,
                        bucket_name,
                        extracted_data.get('title', '제목 없음'), 
                        article_content_str, 
                        url, 
                        target_category # <-- crawler_user_folder 인자 제거
                    ):
                        crawled_count += 1
                    else:
                        failed_urls.append(f"{url} (S3 파일 저장 실패)")

            except Exception as e:
                logger.error(f"뉴스 목록 페이지 '{url_to_crawl_entry}' 크롤링 중 오류 발생: {e}", exc_info=True)
                failed_urls.append(f"목록 페이지 '{url_to_crawl_entry}' 처리 실패: {e}")
                continue

    # RAG 시스템 초기화 (크롤링된 콘텐츠가 있다면)
    if crawled_count > 0:
        try:
            bedrock_runtime_client = current_app.extensions['rag_bedrock_runtime']
            init_rag_system(bedrock_runtime_client)
            logger.info("RAG 시스템이 크롤링된 새 콘텐츠로 성공적으로 업데이트되었습니다. (S3 기반)")
        except Exception as e:
            logger.error(f"RAG 시스템 업데이트 중 오류 발생 (크롤링 후): {e}", exc_info=True)
            failed_urls.append(f"RAG 시스템 업데이트 실패: {e}")
    else:
        logger.info("새로 크롤링된 콘텐츠가 없으므로 RAG 시스템을 업데이트하지 않습니다.")
    
    # 결과 요약 및 반환
    message = f"총 {total_urls_processed}개의 기사 URL을 처리하여 {crawled_count}개의 기사가 성공적으로 크롤링되어 S3 지식 베이스에 추가되었습니다."
    if failed_urls:
        message += f" 다음 URL들은 실패했습니다: {'; '.join(failed_urls)}"
        logger.warning(message)

    logger.info(f"--- 뉴스 크롤링 작업 완료. {crawled_count}개 기사 크롤링 성공. (S3) ---")
    return {"message": message, "crawled_count": crawled_count, "failed_urls": failed_urls}