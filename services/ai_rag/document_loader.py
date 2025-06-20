# ai-content-marketing-tool/services/ai_rag/document_loader.py

import os # os는 더 이상 파일 시스템 경로 직접 접근에 사용되지 않지만, 다른 용도로 필요할 수 있음
import logging
from typing import List, Tuple
# import chardet # 텍스트 인코딩 감지를 위해 필요할 수 있습니다. (설치했다면 주석 해제)

# chunker 모듈에서 chunk_text 함수를 상대 경로로 임포트합니다.
from .chunker import chunk_text
# ai_constants 모듈에서 필요한 상수들을 임포트합니다.
from .ai_constants import CHUNK_SIZE, CHUNK_OVERLAP # <-- 이 줄은 그대로 유지

logger = logging.getLogger(__name__)

# --- S3에서 문서를 로드하는 함수 (기존 load_documents_from_directory를 대체) ---
def load_documents_from_s3(s3_client, bucket_name: str) -> List[str]:
    """
    S3 버킷의 모든 .txt 파일을 로드하고 청크로 분할하여 반환합니다.
    각 파일은 'username/filename.txt' 객체 키 형태로 저장되어 있다고 가정합니다.
    """
    all_chunks: List[str] = []
    
    logger.info(f"Attempting to load documents from S3 bucket: {bucket_name}")
    
    try:
        paginator = s3_client.get_paginator('list_objects_v2')
        # 접두사(Prefix) 없이 버킷 내의 모든 객체를 조회합니다.
        pages = paginator.paginate(Bucket=bucket_name) 

        for page in pages:
            if 'Contents' in page: # 'Contents'는 페이지에 객체가 있을 때만 존재합니다.
                for obj in page['Contents']:
                    key = obj['Key'] # S3 객체 키 (예: 'ohsung/article1.txt', 'Beauty/report.txt')
                    # .txt 파일만 로드하고, 최상위 폴더(예: 'Beauty/') 자체의 객체는 제외합니다.
                    # S3에서는 폴더도 0바이트 객체로 존재할 수 있기 때문에 key.endswith('/')로 폴더를 제외하는 경우도 있지만,
                    # 여기서는 '.txt' 확장자를 명확히 확인하여 문서 파일만 처리합니다.
                    if key.endswith(".txt"):
                        logger.info(f"Loading S3 object: s3://{bucket_name}/{key}")
                        try:
                            response = s3_client.get_object(Bucket=bucket_name, Key=key)
                            file_content_bytes = response['Body'].read()
                            
                            # 텍스트 인코딩 디코딩
                            # 대부분의 경우 UTF-8일 것이므로, 우선 UTF-8로 시도합니다.
                            # 인코딩 문제가 발생하면 chardet 라이브러리를 고려할 수 있습니다.
                            file_content = file_content_bytes.decode('utf-8', errors='ignore')

                            # chunker.py에 정의된 chunk_text 함수를 사용하여 내용을 청크로 분할합니다.
                            chunks = chunk_text(file_content)
                            all_chunks.extend(chunks)
                            logger.info(f"Successfully loaded and chunked {len(chunks)} chunks from S3 object: {key}")
                        except Exception as e:
                            logger.error(f"Failed to read or chunk S3 object '{key}': {e}", exc_info=True)
            else:
                logger.debug(f"No 'Contents' found in a page from bucket {bucket_name}. This page might be empty.")

    except Exception as e:
        logger.error(f"Failed to list objects in S3 bucket '{bucket_name}': {e}", exc_info=True)
        # S3 목록화 실패 시 빈 리스트 반환
        return []
        
    logger.info(f"Finished loading documents from S3. Total chunks generated: {len(all_chunks)}")
    return all_chunks