# ai-content-marketing-tool/services/web_crawling/crawler_tasks.py

import os
import logging
import json
from urllib.parse import urlparse
import boto3
from botocore.exceptions import ClientError
from models import User 
from flask import current_app

from services.ai_rag.rag_system import get_rag_system 
from services.web_crawling.web_utils import sanitize_filename

# --- 특정 URL에 맞는 Extractor 가져오기 ---
# 이 부분은 이미 services/web_crawling/web_content_extractor.py에서 정의되어 있습니다
from services.web_crawling.web_content_extractor import (
    get_specific_extractor
)

logger = logging.getLogger(__name__)

# --- S3 클라이언트 및 버킷 정보 가져오기 헬퍼 함수 ---
def _get_s3_info():
    """
    앱 확장(app.extensions)에서 S3 클라이언트와 버킷 이름을 가져와 반환합니다.
    """
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

def _load_crawler_configs_from_s3(s3_client, config_bucket_name: str, s3_key: str) -> dict | None:
    """S3에서 크롤링 설정 파일 (JSON)을 로드합니다."""
    try:
        response = s3_client.get_object(Bucket=config_bucket_name, Key=s3_key)
        config_content = response['Body'].read().decode('utf-8')
        config = json.loads(config_content)
        logger.info(f"S3 '{s3_key}'에서 {len(config)}개의 카테고리 크롤링 컨피그 로드됨.")
        return config
    except ClientError as e:
        error_code = e.response.get('Error', {}).get('Code')
        if error_code in ['NoSuchKey', 'NotFound']:
            logger.error(f"크롤링 대상 URL 파일 '{s3_key}'를 S3에서 찾을 수 없습니다. (config_bucket_name: {config_bucket_name})")
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

def _save_article_to_s3_knowledge_base(
    s3_client,
    bucket_name: str,
    article_title: str,
    article_content_str: str,
    url: str,
    target_category: str 
) -> str | None: # S3 키를 반환하도록 변경, 실패 시 None
    """
    크롤링된 기사를 S3 지식 베이스에 파일로 저장합니다.
    파일은 's3://<bucket_name>/<target_category>/<filename.txt>' 형태로 저장됩니다.
    파일 이름 충돌 시 숫자를 붙여 처리합니다.
    성공적으로 저장된 S3 키를 반환하고, 실패 시 None을 반환합니다.
    """
    try:
        base_filename = sanitize_filename(article_title, url)
        final_s3_object_key = f"{target_category}/{base_filename}"

        try:
            logger.debug(f"S3 HeadObject 호출 시도: Bucket={bucket_name}, Key={final_s3_object_key}")
            s3_client.head_object(Bucket=bucket_name, Key=final_s3_object_key)
            logger.info(f"S3 객체 '{final_s3_object_key}'이(가) 이미 존재합니다. 새 콘텐츠로 덮어씁니다.")
        except ClientError as e:
            http_status = e.response.get('ResponseMetadata', {}).get('HTTPStatusCode')
            if http_status == 404:
                logger.info(f"S3 객체 '{final_s3_object_key}'을(를) 찾을 수 없습니다 (HTTP 404). 새로운 파일로 업로드 진행합니다.")
            else: 
                logger.error(f"S3 HeadObject 알 수 없는 ClientError 발생 (HTTP {http_status}) for '{final_s3_object_key}': {e}", exc_info=True)
                raise
        except Exception as e:
            logger.error(f"S3 HeadObject 예상치 못한 오류 발생 for '{final_s3_object_key}': {e}", exc_info=True)
            raise

        s3_client.put_object(Bucket=bucket_name, Key=final_s3_object_key, Body=article_content_str.encode('utf-8'))
        
        logger.info(f"URL '{url}'의 콘텐츠가 S3에 '{bucket_name}/{final_s3_object_key}'으로 저장되었습니다.")
        return final_s3_object_key # 성공 시 S3 키 반환
    except Exception as e:
        logger.error(f"S3에 개별 기사 저장 중 오류 발생: {url} - {e}", exc_info=True)
        return None # 실패 시 None 반환

# --- 크롤링 핵심 로직 함수 (스케줄러에서 호출될 함수) ---
def perform_marketing_crawl_task(system_user_id: int): # user_id 인자 추가
    """
    사전 정의된 뉴스 목록 URL들을 크롤링하여 기사들을 S3 지식 베이스에 자동으로 추가하고
    RAG 시스템에 반영합니다. 이 함수는 Flask 앱 컨텍스트 내에서 호출되어야 합니다.
    
    Args:
        system_user_id (int): 크롤링된 데이터를 귀속시킬 시스템 사용자(크롤러)의 ID.
    """
    logger.info(f"--- 뉴스 크롤링 작업 시작 (스케줄러 호출, 시스템 User ID: {system_user_id}) ---")
    s3_client, knowledge_base_bucket_name = _get_s3_info()

    crawled_count = 0
    total_urls_processed = 0
    failed_urls = []

    # 1. 크롤링 설정 로드 (S3에서 로드)
    # config.py에 설정된 S3_BUCKET_NAME을 기본 지식 베이스 버킷으로 사용하되,
    # 크롤러 설정 JSON은 별도의 접두사 (예: _system_configs) 아래에 둡니다.
    # config.py에 CRAWLER_CONFIG_S3_KEY와 CRAWLER_CONFIG_BUCKET_NAME을 설정하는 것이 좋습니다.
    # 임시로 기본 버킷을 사용하고 특정 폴더를 가정합니다.
    
    # 크롤러 설정 파일이 저장될 S3 키 (예: 'system_configs/crawler_urls.json')
    # 이 부분은 app_factory_utils.py에서 설정 파일 로드 시점에 결정되도록 합니다.
    crawler_configs_s3_key = current_app.config.get('CRAWLER_CONFIG_S3_KEY', '_system_configs/crawler_urls.json')
    crawler_configs_bucket_name = current_app.config.get('CRAWLER_CONFIG_BUCKET_NAME', knowledge_base_bucket_name) # 같은 버킷 내 다른 폴더 사용

    category_to_urls_map = _load_crawler_configs_from_s3(s3_client, crawler_configs_bucket_name, crawler_configs_s3_key)
    
    if category_to_urls_map is None:
        logger.error("크롤링 대상 URL 설정 파일을 로드할 수 없어 크롤링 작업을 종료합니다.")
        return {"message": "크롤링 대상 URL 파일 없음 또는 S3 로드 실패", "crawled_count": 0, "failed_urls": []}

    # RAG System 인스턴스 가져오기
    rag_system_instance = get_rag_system()
    if not rag_system_instance:
        logger.critical("RAGSystem 인스턴스를 찾을 수 없습니다. 크롤링된 콘텐츠를 벡터 DB에 추가할 수 없습니다.")
        return {"message": "RAG 시스템 초기화 오류", "crawled_count": 0, "failed_urls": []}

    # 각 카테고리(키)와 해당 URL 목록(값)에 대해 반복
    for target_category, urls_list_for_category in category_to_urls_map.items():
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

                for url in article_urls_to_crawl_from_list[:5]: # 테스트 용도: 처음 5개만 처리
                    total_urls_processed += 1
                    
                    extracted_data = None
                    try:
                        extracted_data = extractor.get_article_details(url)
                    except Exception as e:
                        logger.error(f"개별 기사 크롤링 실패: {url} - {e}", exc_info=True)
                        failed_urls.append(f"{url} (상세 콘텐츠 추출 실패 - Extractor: {type(extractor).__name__})")
                        continue
                    
                    is_valid_article_content = False
                    if extracted_data:
                        if extracted_data.get('content'): # 일반 기사 콘텐츠가 있는 경우
                            is_valid_article_content = True
                        elif extracted_data.get('ingredients') and extracted_data.get('steps'): # 레시피 콘텐츠가 있는 경우
                            is_valid_article_content = True
                    
                    if not is_valid_article_content:
                        logger.warning(f"URL '{url}'에서 유효한 콘텐츠를 추출하지 못했습니다. (제목: {extracted_data.get('title', 'N/A')})")
                        failed_urls.append(f"{url} (콘텐츠 추출 실패)")
                        continue

                    article_title = extracted_data.get('title', '제목 없음')
                    article_content_str = _format_article_content(extracted_data)
                    
                    # S3 지식 베이스에 저장
                    s3_key_saved = _save_article_to_s3_knowledge_base(
                        s3_client,
                        knowledge_base_bucket_name, # 지식 베이스 버킷 사용
                        article_title, 
                        article_content_str, 
                        url, 
                        target_category 
                    )
                    
                    if s3_key_saved:
                        crawled_count += 1
                        # 2. RAG 시스템(PgVector DB 및 FAISS)에 문서 추가
                        try:
                            # system_user_id를 사용하여 RAG 시스템에 문서 추가
                            rag_system_instance.add_document_to_rag_system(
                                s3_key=s3_key_saved,
                                user_id=system_user_id # 스케줄러 사용자 ID 할당
                            )
                            logger.info(f"크롤링된 기사 '{s3_key_saved}'가 RAG 시스템에 성공적으로 추가되었습니다. (User ID: {system_user_id})")
                        except Exception as e:
                            logger.error(f"크롤링된 기사 '{s3_key_saved}'의 RAG 시스템 추가 중 오류 발생: {e}", exc_info=True)
                            failed_urls.append(f"{url} (RAG 시스템 추가 실패)")
                    else:
                        failed_urls.append(f"{url} (S3 파일 저장 실패)")

            except Exception as e:
                logger.error(f"뉴스 목록 페이지 '{url_to_crawl_entry}' 크롤링 중 오류 발생: {e}", exc_info=True)
                failed_urls.append(f"목록 페이지 '{url_to_crawl_entry}' 처리 실패: {e}")
                continue

    # 크롤링 완료 후 RAG 시스템 업데이트 로직 제거 (각 기사 추가 시 이미 업데이트됨)
    # if crawled_count > 0:
    #     logger.info("크롤링된 콘텐츠가 있으므로 RAG 시스템을 업데이트합니다.")
    # else:
    #     logger.info("새로 크롤링된 콘텐츠가 없으므로 RAG 시스템을 업데이트하지 않습니다.")
    
    # 결과 요약 및 반환
    message = f"총 {total_urls_processed}개의 기사 URL을 처리하여 {crawled_count}개의 기사가 성공적으로 크롤링되어 S3 지식 베이스에 추가 및 RAG 시스템에 반영되었습니다."
    if failed_urls:
        message += f" 다음 URL들은 실패했습니다: {'; '.join(failed_urls)}"
        logger.warning(message)

    logger.info(f"--- 뉴스 크롤링 작업 완료. {crawled_count}개 기사 크롤링 성공. (S3 및 RAG 시스템) ---")
    return {"message": message, "crawled_count": crawled_count, "failed_urls": failed_urls}
