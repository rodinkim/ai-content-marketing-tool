# ai-content-marketing-tool/services/ai_rag/rag_system.py

import boto3
import json
import numpy as np
import logging
import os # os는 더 이상 파일 시스템 경로 직접 접근에 사용되지 않지만, 다른 용도로 필요할 수 있음

# --- 새로 분리된 모듈들을 상대 경로로 임포트합니다. ---
from .embedding_generator import get_embedding
from .chunker import chunk_text
# from .document_loader import load_documents_from_directory # <-- 이 임포트를 변경합니다.
from .faiss_indexer import FaissIndexer
from .ai_constants import ENCODER, CHUNK_SIZE, CHUNK_OVERLAP

logger = logging.getLogger(__name__)

class RAGSystem:
    # knowledge_base_dir 대신 S3 버킷 이름과 S3 클라이언트를 받도록 변경
    def __init__(self, bedrock_runtime_client, s3_client, s3_bucket_name):
        self.bedrock_runtime = bedrock_runtime_client
        if not self.bedrock_runtime:
            logger.critical("RAGSystem 초기화 실패: Bedrock runtime 클라이언트가 유효하지 않습니다.")
            raise ValueError("Bedrock runtime 클라이언트가 유효하지 않아 RAGSystem을 초기화할 수 없습니다.")

        self.s3_client = s3_client
        self.s3_bucket_name = s3_bucket_name
        if not self.s3_client or not self.s3_bucket_name:
            logger.critical("RAGSystem 초기화 실패: S3 클라이언트 또는 버킷 이름이 유효하지 않습니다.")
            raise ValueError("S3 클라이언트 또는 버킷 이름이 유효하지 않아 RAGSystem을 초기화할 수 없습니다.")

        self.faiss_indexer = FaissIndexer()
        self.load_and_process_knowledge_base()

    def get_embedding(self, text):
        """EmbeddingGenerator 모듈의 get_embedding 함수를 호출합니다.
        self.bedrock_runtime 클라이언트를 인자로 전달합니다."""
        return get_embedding(self.bedrock_runtime, text)

    def load_and_process_knowledge_base(self):
        """
        S3 버킷에서 문서를 로드하고, 청크로 분할하여 임베딩을 생성한 후 FAISS 인덱스를 구축합니다.
        """
        logger.info(f"Loading knowledge base from S3 bucket: {self.s3_bucket_name}")
        
        # document_loader.py에서 S3로부터 문서를 로드하는 함수를 임포트하고 사용합니다.
        # 기존 load_documents_from_directory 대신 S3에서 로드하는 함수를 사용
        from .document_loader import load_documents_from_s3 # <-- S3용 로더 임포트

        # 1. S3에서 문서 로드 및 청크 분할
        # 이제 S3 클라이언트와 버킷 이름을 load_documents_from_s3 함수에 전달합니다.
        all_chunks = load_documents_from_s3(self.s3_client, self.s3_bucket_name)

        if not all_chunks:
            logger.warning(f"No documents (or chunks) found in S3 bucket '{self.s3_bucket_name}'. FAISS index will not be built.")
            logger.warning("Please ensure your S3 bucket contains .txt files in user-specific prefixes (e.g., 'username/document.txt').")
            self.faiss_indexer.build_index([], np.array([])) # 문서가 없어도 빈 인덱스는 구축
            return

        # 2. 각 청크에 대한 임베딩 생성 (기존 로직 유지)
        temp_embeddings = []
        for i, chunk in enumerate(all_chunks):
            embedding = self.get_embedding(chunk)
            if embedding is not None:
                temp_embeddings.append(embedding)
            else:
                logger.error(f"Failed to get embedding for chunk {i+1}. Skipping this chunk.")
        
        if not temp_embeddings:
            logger.warning("No embeddings generated for knowledge base. FAISS index will not be built.")
            self.faiss_indexer.build_index([], np.array([])) # 임베딩이 없어도 빈 인덱스는 구축
            return

        embeddings_array = np.vstack(temp_embeddings)
        
        # 3. FAISS 인덱스 구축 (기존 로직 유지)
        self.faiss_indexer.build_index(all_chunks, embeddings_array)
        logger.info(f"Knowledge base loaded and indexed from S3. Total chunks: {len(all_chunks)}, Embedding dimension: {embeddings_array.shape[1]}")

    def retrieve(self, query_text, k=3):
        """쿼리 텍스트와 유사한 문서 청크 검색 (기존 로직 유지)"""
        query_embedding = self.get_embedding(query_text)
        if query_embedding is None:
            logger.warning("Failed to get embedding for query text. Cannot perform retrieval.")
            return []
        return self.faiss_indexer.search(query_embedding, k)

# RAGSystem 싱글톤 인스턴스를 저장할 변수
_rag_system_instance = None

# init_rag_system 함수 수정: S3 클라이언트와 버킷 이름을 받도록 변경
def init_rag_system(bedrock_runtime_client):
    """
    RAGSystem 인스턴스를 초기화하고 싱글톤으로 설정합니다.
    S3 버킷에서 지식 베이스를 로드하도록 변경됩니다.
    """
    global _rag_system_instance
    if _rag_system_instance is None:
        try:
            from flask import current_app # Flask 앱 컨텍스트에서 설정 가져오기

            # app.extensions에서 S3 클라이언트와 버킷 이름 가져오기
            s3_client = current_app.extensions.get('s3_client')
            s3_bucket_name = current_app.config.get('S3_BUCKET_NAME')

            if not s3_client or not s3_bucket_name:
                logger.critical("RAGSystem 초기화 실패: S3 클라이언트 또는 버킷 이름이 앱 설정에 없습니다.")
                raise ValueError("S3 클라이언트 또는 버킷 이름이 없어 RAGSystem을 초기화할 수 없습니다.")

            _rag_system_instance = RAGSystem(bedrock_runtime_client, s3_client, s3_bucket_name)
            logger.info("RAGSystem 인스턴스가 S3 기반으로 성공적으로 초기화되었습니다.")
        except Exception as e:
            logger.critical(f"RAGSystem 인스턴스 초기화 중 치명적인 오류 발생 (S3 기반): {e}", exc_info=True)
            _rag_system_instance = None
    
    # RAGSystem이 이미 초기화되어 있다면, load_and_process_knowledge_base를 다시 호출하여
    # 지식 베이스를 새로고침합니다. (새로운 파일 추가/삭제 후 호출될 때)
    elif _rag_system_instance is not None and hasattr(_rag_system_instance, 'load_and_process_knowledge_base'):
        logger.info("기존 RAGSystem 인스턴스를 사용하여 지식 베이스를 새로고침합니다 (S3 기반).")
        _rag_system_instance.load_and_process_knowledge_base()

    return _rag_system_instance

def get_rag_system():
    """초기화된 RAGSystem 인스턴스를 반환합니다."""
    if _rag_system_instance is None:
        logger.warning("RAGSystem이 아직 초기화되지 않았습니다. init_rag_system을 먼저 호출해야 합니다.")
    return _rag_system_instance