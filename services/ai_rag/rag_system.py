# ai-content-marketing-tool/services/ai_rag/rag_system.py

import numpy as np
import logging
from typing import List, Tuple, Optional
from flask import current_app

from .embedding_generator import get_embedding
from .chunker import chunk_text
from .document_loader import load_documents_from_s3 # S3용 로더 임포트
from .faiss_indexer import FaissIndexer
from .pgvector_store import PgVectorStore
from .ai_constants import ENCODER, CHUNK_SIZE, CHUNK_OVERLAP

logger = logging.getLogger(__name__)

class RAGSystem:
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
        self.pgvector_store = PgVectorStore()
        
        from flask import current_app
        with current_app.app_context():
            self.pgvector_store._ensure_vector_table_and_index()

        # RAGSystem 초기화 시에는 PgVector DB에 있는 모든 데이터를 로드하여 FAISS 인덱스를 구축합니다.
        # 이렇게 하면 PgVector DB가 '주요' 벡터 스토어가 되고, FAISS는 그 스냅샷이 됩니다.
        self._initial_load_faiss_from_pgvector()

    def _initial_load_faiss_from_pgvector(self):
        """
        PgVector DB에 있는 모든 청크를 로드하여 FAISS 인덱스를 초기 구축합니다.
        이는 애플리케이션 시작 시 한 번만 수행되어야 합니다.
        """
        logger.info("Performing initial load of all chunks from PgVector DB to FAISS index.")
        try:
            with current_app.app_context():
                # PgVectorStore에 모든 벡터를 가져오는 메서드가 필요합니다. (get_all_vectors 또는 유사한 이름)
                # 만약 없다면 PgVectorStore에 추가해야 합니다.
                all_pg_vectors = self.pgvector_store.get_all_vectors() # <- PgVectorStore에 추가 필요!

            if not all_pg_vectors:
                logger.warning("No vectors found in PgVector DB. Initial FAISS index will be empty.")
                self.faiss_indexer.build_index([], np.array([]))
                return

            all_chunks_only = [v.text_content for v in all_pg_vectors]
            embeddings_array = np.vstack([v.embedding for v in all_pg_vectors])
            
            self.faiss_indexer.build_index(all_chunks_only, embeddings_array)
            logger.info(f"Initial FAISS index built from PgVector DB. Total chunks: {len(all_chunks_only)}, Embedding dimension: {embeddings_array.shape[1]}")
        except Exception as e:
            logger.error(f"Failed to load initial FAISS index from PgVector DB: {e}", exc_info=True)
            self.faiss_indexer.build_index([], np.array([])) # 오류 시 빈 인덱스라도 구축


    def get_embedding(self, text):
        return get_embedding(self.bedrock_runtime, text)

    # 이 함수는 이제 특정 파일을 처리하는 역할로 변경됩니다.
    def _process_document_for_vector_db(self, s3_key: str, user_id: int):
        """
        주어진 S3 키의 문서를 로드, 청크, 임베딩하여 PgVector DB에 추가/업데이트합니다.
        FAISS 인덱스는 이 함수에서 직접 업데이트하지 않습니다.
        """
        logger.info(f"Processing document from S3 key '{s3_key}' for PgVector DB. Assigned user ID: {user_id}")
        
        try:
            response = self.s3_client.get_object(Bucket=self.s3_bucket_name, Key=s3_key)
            file_content_bytes = response['Body'].read()
            file_content = file_content_bytes.decode('utf-8', errors='ignore')

            # S3 키에서 industry, original_filename 추출 (document_loader와 유사하게)
            path_parts = s3_key.split('/')
            industry_name = path_parts[0] if len(path_parts) > 1 else "unspecified_industry"
            filename_only = path_parts[1] if len(path_parts) > 1 else s3_key
            import re
            original_filename_no_uuid = re.sub(r'_[0-9a-fA-F]{8}\.txt$', '.txt', filename_only)

            # 청크 분할 및 반환값 유효성 검사
            chunks = chunk_text(file_content)
            if not isinstance(chunks, list): # chunks가 리스트가 아닐 경우
                logger.error(f"chunk_text returned invalid type: {type(chunks)} for s3_key '{s3_key}'. Expected a list.")
                raise ValueError("chunk_text function did not return a list of chunks.")
            if not chunks: # chunks가 빈 리스트일 경우
                logger.warning(f"No chunks generated for s3_key '{s3_key}'. Document may be empty or unprocessable.")
                return # 더 이상 처리할 청크가 없으므로 함수 종료

            processed_chunk_data = []
            temp_embeddings = []
            for i, chunk_content in enumerate(chunks): # 변수명 'chunk_text' 대신 'chunk_content' 사용 (명확성을 위해)
                # chunk_content가 문자열인지 확인 (chunk_text 함수가 텍스트 청크를 반환한다고 가정)
                if not isinstance(chunk_content, str):
                    logger.warning(f"Chunk {i} from '{s3_key}' is not a string (type: {type(chunk_content)}). Skipping this chunk.")
                    continue

                embedding = self.get_embedding(chunk_content) # 'chunk_content' 사용
                if embedding is None:
                    logger.error(f"Failed to get embedding for chunk {i} of '{s3_key}'. Skipping this chunk.")
                    continue
                
                chunk_metadata = {
                    "s3_key": s3_key,
                    "user_id": user_id, 
                    "industry": industry_name,
                    "original_filename": original_filename_no_uuid,
                    "chunk_index": i,
                }
                processed_chunk_data.append((chunk_content, chunk_metadata)) # 'chunk_content' 사용
                temp_embeddings.append(embedding)

            if not processed_chunk_data:
                logger.warning(f"No processable chunks found for S3 key '{s3_key}' after embedding attempts. No vectors added/updated.")
                return

            with current_app.app_context():
                self.pgvector_store.add_vectors(processed_chunk_data, temp_embeddings)
            logger.info(f"Document '{s3_key}' successfully added/updated in PgVector DB.")

        except Exception as e:
            logger.error(f"Failed to process document '{s3_key}' for vector DB: {e}", exc_info=True)
            raise

    # 외부에서 호출될 함수 (새 파일 추가 시)
    def add_document_to_rag_system(self, s3_key: str, user_id: int):
        """
        새로운 문서를 RAG 시스템에 추가합니다.
        이는 PgVector DB에 추가하고, FAISS 인덱스를 비동기적으로 새로고침하도록 트리거합니다.
        """
        self._process_document_for_vector_db(s3_key, user_id)
        # 중요: FAISS 인덱스 재구축 로직을 여기에 추가하거나,
        # 주기적인 배치 작업으로 FAISS를 PgVector에서 새로고침하도록 설계해야 합니다.
        # 지금은 동기적으로 재구축하도록 호출합니다.
        self._initial_load_faiss_from_pgvector() 
        logger.info(f"Document '{s3_key}' added to RAG system and FAISS index reloaded.")


    # 외부에서 호출될 함수 (파일 삭제 시)
    def remove_document_from_rag_system(self, s3_key: str):
        """
        RAG 시스템에서 문서를 제거합니다 (PgVector DB 및 FAISS 인덱스).
        """
        try:
            with current_app.app_context():
                self.pgvector_store.delete_vector_by_file(s3_key)
            logger.info(f"Document '{s3_key}' successfully removed from PgVector DB.")
            
            # FAISS 인덱스 재구축 (삭제 후에는 전체를 다시 구축하는 것이 안전)
            self._initial_load_faiss_from_pgvector()
            logger.info(f"Document '{s3_key}' removed from RAG system and FAISS index reloaded.")
        except Exception as e:
            logger.error(f"Failed to remove document '{s3_key}' from RAG system: {e}", exc_info=True)
            raise


    # retrieve 함수는 동일하게 유지됩니다.
    def retrieve(self, query_text, k=3, user_id: int = None): 
        query_embedding = self.get_embedding(query_text)
        if query_embedding is None:
            logger.warning("Failed to get embedding for query text. Cannot perform retrieval.")
            return []

        logger.info(f"Attempting retrieval from PgVector DB for user_id: {user_id if user_id is not None else 'None'}")
        pgvector_results = self.pgvector_store.search(query_embedding, k, user_id=user_id) 
        
        if pgvector_results:
            logger.info(f"Retrieved {len(pgvector_results)} relevant chunks from PgVector DB for user_id: {user_id if user_id is not None else 'None'}.")
            return [(chunk, score, metadata) for chunk, score, metadata in pgvector_results] # metadata도 반환하도록 수정
        else:
            logger.warning(f"No relevant chunks found in PgVector DB for user_id: {user_id if user_id is not None else 'None'}. Attempting search from FAISS (unfiltered).")
            faiss_results = self.faiss_indexer.search(query_embedding, k)
            if faiss_results:
                logger.info(f"Retrieved {len(faiss_results)} relevant chunks from FAISS (unfiltered).")
                # FAISS 결과는 (text, distance) 튜플이므로, PgVector 결과 형식에 맞추려면 metadata가 필요
                # FAISS 인덱스 구축 시 metadata를 함께 저장했다면 여기서 추출 가능합니다.
                # 현재 FAISS는 텍스트만 저장하므로, 메타데이터는 PgVector에서 다시 가져오거나 FAISS에 저장해야 합니다.
                # 임시로 메타데이터를 빈 딕셔너리로 반환합니다.
                return [(doc.page_content, score, {}) for doc, score in faiss_results]
            else:
                logger.warning("No relevant chunks found in FAISS either.")
                return []


# RAGSystem 싱글톤 인스턴스를 저장할 변수
_rag_system_instance = None

# init_rag_system 함수 수정: 이제 이 함수는 RAGSystem 인스턴스를 초기화만 합니다.
# 실제 문서 추가/삭제는 add_document_to_rag_system / remove_document_from_rag_system을 통해 이루어집니다.
def init_rag_system(bedrock_runtime_client): # user_id 인자 제거
    """
    RAGSystem 인스턴스를 초기화하고 싱글톤으로 설정합니다.
    앱 시작 시 PgVector DB에서 모든 데이터를 로드하여 FAISS 인덱스를 구축합니다.
    """
    global _rag_system_instance
    try:
        from flask import current_app

        s3_client = current_app.extensions.get('s3_client')
        s3_bucket_name = current_app.config.get('S3_BUCKET_NAME')

        if not s3_client or not s3_bucket_name:
            logger.critical("RAGSystem 초기화 실패: S3 클라이언트 또는 버킷 이름이 앱 설정에 없습니다.")
            raise ValueError("S3 클라이언트 또는 버킷 이름이 없어 RAGSystem을 초기화할 수 없습니다.")

        if _rag_system_instance is None:
            _rag_system_instance = RAGSystem(bedrock_runtime_client, s3_client, s3_bucket_name)
            logger.info(f"RAGSystem 인스턴스가 S3, FAISS, PgVector 기반으로 성공적으로 초기화되었습니다.")
        else:
            # 앱이 이미 초기화되어 있다면, 이 시점에서는 아무것도 하지 않거나
            # 필요에 따라 FAISS를 PgVector에서 재로드하도록 합니다.
            # 하지만 add/remove_document_to_rag_system을 통해 점진적으로 업데이트할 것이므로
            # 여기서는 별다른 작업을 수행하지 않습니다.
            logger.info("RAGSystem 인스턴스가 이미 존재합니다. 초기화 건너뜁니다.")


    except Exception as e:
        logger.critical(f"RAGSystem 인스턴스 초기화 중 치명적인 오류 발생 (S3/FAISS/PgVector 기반): {e}", exc_info=True)
        _rag_system_instance = None
    
    return _rag_system_instance

def get_rag_system() -> Optional[RAGSystem]: # 타입 힌트 추가
    if _rag_system_instance is None:
        logger.warning("RAGSystem이 아직 초기화되지 않았습니다. init_rag_system을 먼저 호출해야 합니다.")
    return _rag_system_instance