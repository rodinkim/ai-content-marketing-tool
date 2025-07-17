# ai-content-marketing-tool/services/ai_rag/rag_system.py

import numpy as np
import logging
from typing import List, Tuple, Optional
from flask import current_app
import re

from .embedding_generator import EmbeddingManager
from .chunker import chunk_text
from .faiss_indexer import FaissIndexer
from .ai_constants import ENCODER, CHUNK_SIZE, CHUNK_OVERLAP

logger = logging.getLogger(__name__)


class RAGSystem:
    def __init__(self, bedrock_runtime_client, s3_client, s3_bucket_name):
        # Bedrock 런타임 클라이언트 검증
        self.bedrock_runtime = bedrock_runtime_client
        if not self.bedrock_runtime:
            logger.critical("RAGSystem 초기화 실패: Bedrock runtime 클라이언트가 유효하지 않습니다.")
            raise ValueError("Bedrock runtime 클라이언트가 유효하지 않아 RAGSystem을 초기화할 수 없습니다.")

        # S3 클라이언트 및 버킷 이름 검증
        self.s3_client = s3_client
        self.s3_bucket_name = s3_bucket_name
        if not self.s3_client or not self.s3_bucket_name:
            logger.critical("RAGSystem 초기화 실패: S3 클라이언트 또는 버킷 이름이 유효하지 않습니다.")
            raise ValueError("S3 클라이언트 또는 버킷 이름이 유효하지 않아 RAGSystem을 초기화할 수 없습니다.")

        # 임베딩 매니저, FAISS 인덱서 인스턴스화
        self.embedding_manager = EmbeddingManager(self.bedrock_runtime)
        self.faiss_indexer = FaissIndexer()

        # --- [수정] PgVectorStore를 이 시점에 import하고 인스턴스화 ---
        from .pgvector_store import PgVectorStore
        self.pgvector_store = PgVectorStore()
        
        # 벡터 테이블 및 인덱스 보장 (이제 db 객체가 모든 설정을 알고 있으므로 정상 동작)
        with current_app.app_context():
            self.pgvector_store._ensure_vector_table_and_index()

        # FAISS 인덱스 초기화
        self._initial_load_faiss_from_pgvector()

    def _initial_load_faiss_from_pgvector(self):
        """PgVector DB의 모든 청크를 로드하여 FAISS 인덱스를 초기 구축합니다."""
        logger.info("Performing initial load of all chunks from PgVector DB to FAISS index.")
        try:
            with current_app.app_context():
                all_pg_vectors = self.pgvector_store.get_all_vectors()

            if not all_pg_vectors:
                logger.warning("No vectors found in PgVector DB. Initial FAISS index will be empty.")
                self.faiss_indexer.build_index([], np.array([]))
                return

            all_chunks_only = [v.text_content for v in all_pg_vectors]
            embeddings_array = np.vstack([v.embedding for v in all_pg_vectors])
            
            self.faiss_indexer.build_index(all_chunks_only, embeddings_array)
            logger.info(f"Initial FAISS index built. Total chunks: {len(all_chunks_only)}")
        except Exception as e:
            logger.error(f"Failed to load initial FAISS index from PgVector DB: {e}", exc_info=True)
            self.faiss_indexer.build_index([], np.array([]))

    def get_embedding(self, text):
        # 텍스트 임베딩 생성
        return self.embedding_manager._get_embedding(text)

    def _process_document_for_vector_db(self, s3_key: str, user_id: int):
        """주어진 S3 키의 문서를 로드, 청크, 임베딩하여 PgVector DB에 추가/업데이트합니다."""
        logger.info(f"Processing document from S3 key '{s3_key}' for PgVector DB. User ID: {user_id}")
        
        try:
            response = self.s3_client.get_object(Bucket=self.s3_bucket_name, Key=s3_key)
            file_content = response['Body'].read().decode('utf-8', errors='ignore')

            path_parts = s3_key.split('/')
            industry_name = path_parts[0] if len(path_parts) > 1 else "unspecified"
            original_filename = re.sub(r'_[0-9a-fA-F]{8}\.txt$', '.txt', path_parts[-1])

            chunks = chunk_text(file_content)
            if not chunks:
                logger.warning(f"No chunks generated for s3_key '{s3_key}'.")
                return

            processed_chunk_data = []
            temp_embeddings = []
            for i, chunk_content in enumerate(chunks):
                if not isinstance(chunk_content, str):
                    logger.warning(f"Chunk {i} from '{s3_key}' is not a string. Skipping.")
                    continue

                embedding = self.get_embedding(chunk_content)
                if embedding is None:
                    logger.error(f"Failed to get embedding for chunk {i} of '{s3_key}'. Skipping.")
                    continue
                
                chunk_metadata = {
                    "s3_key": s3_key, "user_id": user_id, "industry": industry_name,
                    "original_filename": original_filename, "chunk_index": i,
                }
                processed_chunk_data.append((chunk_content, chunk_metadata))
                temp_embeddings.append(embedding)

            if not processed_chunk_data:
                logger.warning(f"No processable chunks for S3 key '{s3_key}'.")
                return

            with current_app.app_context():
                self.pgvector_store.add_vectors(processed_chunk_data, temp_embeddings)
            logger.info(f"Document '{s3_key}' successfully processed for PgVector DB.")
        except Exception as e:
            logger.error(f"Failed to process document '{s3_key}' for vector DB: {e}", exc_info=True)
            raise

    def add_document_to_rag_system(self, s3_key: str, user_id: int):
        """새로운 문서를 RAG 시스템에 추가하고 인덱스를 재구성합니다."""
        self._process_document_for_vector_db(s3_key, user_id)
        self._initial_load_faiss_from_pgvector()
        logger.info(f"Document '{s3_key}' added and FAISS index reloaded.")

    def remove_document_from_rag_system(self, s3_key: str):
        """RAG 시스템에서 문서를 제거하고 인덱스를 재구성합니다."""
        try:
            with current_app.app_context():
                self.pgvector_store.delete_vector_by_file(s3_key)
            logger.info(f"Document '{s3_key}' removed from PgVector DB.")
            self._initial_load_faiss_from_pgvector()
            logger.info(f"Document '{s3_key}' removed and FAISS index reloaded.")
        except Exception as e:
            logger.error(f"Failed to remove document '{s3_key}': {e}", exc_info=True)
            raise

    def retrieve(self, query_text, k=3, user_id: int = None):
        """쿼리 텍스트에 대해 가장 관련성 높은 문서를 검색합니다."""
        query_embedding = self.get_embedding(query_text)
        if query_embedding is None:
            logger.warning("Failed to get embedding for query. Cannot retrieve.")
            return []

        logger.info(f"Retrieving from PgVector DB for user_id: {user_id}")
        pgvector_results = self.pgvector_store.search(query_embedding, k, user_id=user_id)
        
        if pgvector_results:
            logger.info(f"Retrieved {len(pgvector_results)} chunks from PgVector DB.")
            return [(chunk, score, metadata) for chunk, score, metadata in pgvector_results]
        else:
            logger.warning(f"No relevant chunks in PgVector DB. Trying FAISS.")
            faiss_results = self.faiss_indexer.search(query_embedding, k)
            if faiss_results:
                logger.info(f"Retrieved {len(faiss_results)} chunks from FAISS.")
                return [(doc.page_content, score, {}) for doc, score in faiss_results]
            else:
                logger.warning("No relevant chunks found in FAISS either.")
                return []


# RAGSystem 싱글톤 관리
_rag_system_instance = None

def init_rag_system(bedrock_runtime_client):
    """RAGSystem 인스턴스를 초기화하고 싱글톤으로 설정합니다."""
    global _rag_system_instance
    try:
        if _rag_system_instance is None:
            s3_client = current_app.extensions.get('s3_client')
            s3_bucket_name = current_app.config.get('S3_BUCKET_NAME')
            if not s3_client or not s3_bucket_name:
                raise ValueError("S3 client or bucket name not configured in Flask app.")
            
            _rag_system_instance = RAGSystem(bedrock_runtime_client, s3_client, s3_bucket_name)
            logger.info("RAGSystem instance successfully initialized.")
        else:
            logger.info("RAGSystem instance already exists. Skipping initialization.")
    except Exception as e:
        logger.critical(f"Fatal error during RAGSystem initialization: {e}", exc_info=True)
        _rag_system_instance = None
    
    return _rag_system_instance

def get_rag_system() -> Optional[RAGSystem]:
    if _rag_system_instance is None:
        logger.warning("RAGSystem is not initialized. Call init_rag_system first.")
    return _rag_system_instance