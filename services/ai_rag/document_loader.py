# ai-content-marketing-tool/services/ai_rag/document_loader.py

import os # os는 더 이상 파일 시스템 경로 직접 접근에 사용되지 않지만, 다른 용도로 필요할 수 있음
import logging
from typing import List, Tuple # List, Tuple 임포트 확인
# import chardet # 텍스트 인코딩 감지를 위해 필요할 수 있습니다. (필요시 주석 해제 및 설치)

from .chunker import chunk_text # chunk_text 함수 임포트
from .ai_constants import CHUNK_SIZE, CHUNK_OVERLAP 

logger = logging.getLogger(__name__)

def load_documents_from_s3(s3_client, bucket_name: str) -> List[Tuple[str, dict]]:
    """
    S3 버킷의 모든 .txt 파일을 로드하고 청크로 분할하여 (청크 텍스트, 메타데이터) 튜플 리스트로 반환합니다.
    메타데이터에는 user_folder_name, filename, chunk_index, s3_key 등이 포함됩니다.
    """
    all_chunk_data: List[Tuple[str, dict]] = [] # (청크 텍스트, 메타데이터 딕셔너리) 튜플 리스트
    
    logger.info(f"Attempting to load documents from S3 bucket: {bucket_name} for RAG indexing.")
    
    try:
        paginator = s3_client.get_paginator('list_objects_v2')
        pages = paginator.paginate(Bucket=bucket_name)

        for page in pages:
            if 'Contents' in page: # 'Contents'는 페이지에 객체가 있을 때만 존재합니다.
                for obj in page['Contents']:
                    key = obj['Key'] # S3 객체 키 (예: 'ohsung/article1.txt', 'Beauty/report.txt')
                    if key.endswith(".txt") and '/' in key: # .txt 파일이고 사용자 폴더 내에 있는 파일만 처리
                        # S3 객체 키에서 user_folder_name과 filename 추출
                        # 예: 'Beauty/제목.txt'에서 user_folder_name='Beauty', filename='제목.txt'
                        parts = key.split('/', 1) # 첫 번째 슬래시 기준으로 분리
                        if len(parts) < 2: # 최상위 폴더에 파일이 직접 있는 경우 (일반적이지 않음)
                            user_folder_name = "root_folder_user" # 폴더명 없으면 기본값 설정
                            filename_only = key
                            logger.warning(f"S3 객체 키에 사용자 폴더가 없습니다: {key}. 'root_folder_user'로 처리합니다.")
                        else:
                            user_folder_name = parts[0]
                            filename_only = parts[1]
                        
                        logger.info(f"Loading S3 object for RAG: s3://{bucket_name}/{key}")
                        try:
                            response = s3_client.get_object(Bucket=bucket_name, Key=key)
                            file_content_bytes = response['Body'].read()
                            file_content = file_content_bytes.decode('utf-8', errors='ignore')

                            chunks = chunk_text(file_content)
                            
                            for i, chunk in enumerate(chunks):
                                # 각 청크에 대한 메타데이터 딕셔너리 생성
                                metadata = {
                                    "user_folder_name": user_folder_name,
                                    "filename": filename_only,
                                    "chunk_index": i,
                                    "s3_key": key, # 원본 S3 객체 키 저장 (나중에 필요할 수 있음)
                                    # "source_url": "..." (원본 URL 정보가 있다면 여기에 추가)
                                }
                                all_chunk_data.append((chunk, metadata)) # (청크 텍스트, 메타데이터) 튜플로 추가
                            logger.info(f"Loaded and chunked {len(chunks)} chunks from S3 object: {key}")
                        except Exception as e:
                            logger.error(f"Failed to read or chunk S3 object '{key}': {e}", exc_info=True)
            else:
                logger.debug(f"No 'Contents' found in a page from bucket {bucket_name}. This page might be empty.")

    except Exception as e:
        logger.error(f"Failed to list objects in S3 bucket '{bucket_name}' for RAG loading: {e}", exc_info=True)
        return []
        
    logger.info(f"Finished loading documents from S3 for RAG. Total chunks generated: {len(all_chunk_data)}")
    return all_chunk_data