# ai-content-marketing-tool/services/ai_rag/document_loader.py

import logging
from typing import List, Tuple
import re # re 모듈 임포트 추가

from .chunker import chunk_text
from .ai_constants import CHUNK_SIZE, CHUNK_OVERLAP 

logger = logging.getLogger(__name__)

# prefix 매개변수 추가 및 기본값 설정
def load_documents_from_s3(s3_client, bucket_name: str, prefix: str = "") -> List[Tuple[str, dict]]:
    """
    S3 버킷에서 지정된 'prefix' 내의 모든 .txt 파일을 로드하고 청크로 분할하여 (청크 텍스트, 메타데이터) 튜플 리스트로 반환합니다.
    메타데이터에는 industry (S3 폴더 이름), original_filename, chunk_index, s3_key 등이 포함됩니다.
    
    Args:
        s3_client: boto3 S3 클라이언트 인스턴스.
        bucket_name (str): S3 버킷 이름.
        prefix (str, optional): S3 객체 키의 접두사 (폴더 경로). 이 경로 내의 파일만 로드합니다.
                                예를 들어, "Beauty/"로 설정하면 "Beauty" 폴더 내의 파일만 가져옵니다.
                                기본값은 "" (빈 문자열)으로, 모든 .txt 파일을 로드합니다.
    Returns:
        List[Tuple[str, dict]]: (텍스트 청크, 메타데이터 딕셔너리) 튜플의 리스트.
    """
    all_chunk_data: List[Tuple[str, dict]] = []
    
    logger.info(f"Attempting to load documents from S3 bucket: {bucket_name} with prefix '{prefix}' for RAG indexing.")
    
    try:
        paginator = s3_client.get_paginator('list_objects_v2')
        # list_objects_v2 호출 시 prefix 인자 사용
        pages = paginator.paginate(Bucket=bucket_name, Prefix=prefix)

        for page in pages:
            if 'Contents' in page:
                for obj in page['Contents']:
                    key = obj['Key'] # S3 객체 키 (예: 'Beauty/제목.txt')
                    
                    # 폴더 자체는 건너뛰고, .txt 파일만 처리
                    if key.endswith('/') or not key.endswith('.txt'):
                        continue
                    
                    # S3 객체 키에서 industry_name(폴더 이름)과 filename 추출
                    # key가 'Beauty/제목.txt'라면 path_parts는 ['Beauty', '제목.txt']
                    path_parts = key.split('/', 1) 
                    
                    # 폴더 구조가 아닌 최상위에 파일이 있을 경우를 대비 (일반적이지 않음)
                    if len(path_parts) < 2:
                        industry_name = "unspecified_industry" # 폴더명 없으면 기본값 설정
                        filename_only = key
                        logger.warning(f"S3 객체 키에 산업 폴더가 없습니다: {key}. 'unspecified_industry'로 처리합니다.")
                    else:
                        industry_name = path_parts[0] # 첫 번째 부분이 산업 폴더 이름
                        filename_only = path_parts[1] # 두 번째 부분이 파일 이름 (폴더 경로 포함 가능성, 하지만 여기서는 첫 슬래시로만 분리)
                        
                    # s3_key에서 원래 파일 이름 (UUID 제거된) 추출 로직 추가
                    # routes/knowledge_base_routes.py의 display_name 로직과 유사
                    original_filename_no_uuid = re.sub(r'_[0-9a-fA-F]{8}\.txt$', '.txt', filename_only)
                    
                    logger.info(f"Loading S3 object for RAG: s3://{bucket_name}/{key}")
                    try:
                        response = s3_client.get_object(Bucket=bucket_name, Key=key)
                        file_content_bytes = response['Body'].read()
                        file_content = file_content_bytes.decode('utf-8', errors='ignore')

                        chunks = chunk_text(file_content)
                        
                        for i, chunk in enumerate(chunks):
                            metadata = {
                                "industry": industry_name, # S3 폴더 이름을 'industry'로 저장
                                "original_filename": original_filename_no_uuid, # UUID 제거된 원본 파일명
                                "chunk_index": i,
                                "s3_key": key, # 원본 S3 객체 키
                            }
                            all_chunk_data.append((chunk, metadata))
                        logger.info(f"Loaded and chunked {len(chunks)} chunks from S3 object: {key}")
                    except Exception as e:
                        logger.error(f"Failed to read or chunk S3 object '{key}': {e}", exc_info=True)
            else:
                logger.debug(f"No 'Contents' found in a page from bucket {bucket_name} with prefix '{prefix}'. This page might be empty.")

    except Exception as e:
        logger.error(f"Failed to list objects in S3 bucket '{bucket_name}' with prefix '{prefix}' for RAG loading: {e}", exc_info=True)
        return []
        
    logger.info(f"Finished loading documents from S3 for RAG. Total chunks generated: {len(all_chunk_data)}")
    return all_chunk_data