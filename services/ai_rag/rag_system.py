# ai-content-marketing-tool/services/ai_rag/rag_system.py

import numpy as np
import logging
import re
from typing import List, Tuple, Optional, Any
from flask import current_app

from .embedding_generator import EmbeddingManager
from .chunker import chunk_text
from .faiss_indexer import FaissIndexer
from .pgvector_store import PgVectorStore

logger = logging.getLogger(__name__)


class RAGSystem:
    """
    RAG (Retrieval-Augmented Generation) 시스템의 핵심 클래스
    
    PgVector DB와 FAISS 인덱스를 통합하여 효율적인 벡터 검색을 제공합니다.
    문서 추가/제거 시 자동으로 인덱스를 동기화합니다.
    """
    
    def __init__(self, bedrock_runtime_client: Any, s3_client: Any, s3_bucket_name: str):
        """
        RAG 시스템을 초기화합니다.
        
        Args:
            bedrock_runtime_client: Bedrock 런타임 클라이언트
            s3_client: S3 클라이언트
            s3_bucket_name: S3 버킷 이름
        """
        self._validate_clients(bedrock_runtime_client, s3_client, s3_bucket_name)
        
        # 클라이언트 설정
        self.bedrock_runtime = bedrock_runtime_client
        self.s3_client = s3_client
        self.s3_bucket_name = s3_bucket_name
        
        # 핵심 컴포넌트 초기화
        self.embedding_manager = EmbeddingManager(self.bedrock_runtime)
        self.faiss_indexer = FaissIndexer()
        self.pgvector_store = PgVectorStore()
        
        # 데이터베이스 및 인덱스 초기화
        self._initialize_database()
        self._load_faiss_from_pgvector()

    def _validate_clients(self, bedrock_client: Any, s3_client: Any, s3_bucket_name: str) -> None:
        """클라이언트들의 유효성을 검증합니다."""
        if not bedrock_client:
            raise ValueError("Bedrock runtime 클라이언트가 유효하지 않습니다.")
        
        if not s3_client or not s3_bucket_name:
            raise ValueError("S3 클라이언트 또는 버킷 이름이 유효하지 않습니다.")

    def _initialize_database(self) -> None:
        """벡터 테이블과 인덱스를 초기화합니다."""
        with current_app.app_context():
            self.pgvector_store._ensure_vector_table_and_index()

    def _load_faiss_from_pgvector(self) -> None:
        """PgVector DB의 모든 청크를 로드하여 FAISS 인덱스를 구축합니다."""
        logger.info("PgVector DB에서 FAISS 인덱스로 청크들을 로드합니다.")
        
        try:
            with current_app.app_context():
                all_vectors = self.pgvector_store.get_all_vectors()

            if not all_vectors:
                logger.warning("PgVector DB에 벡터가 없습니다. 빈 FAISS 인덱스를 생성합니다.")
                self.faiss_indexer.build_index([], np.array([]))
                return

            # 벡터 데이터 추출 및 변환
            chunks = [vector.text_content for vector in all_vectors]
            embeddings = np.vstack([vector.embedding for vector in all_vectors])
            
            self.faiss_indexer.build_index(chunks, embeddings)
            logger.info(f"FAISS 인덱스 구축 완료. 총 청크 수: {len(chunks)}")
            
        except Exception as e:
            logger.error(f"PgVector DB에서 FAISS 인덱스 로드 실패: {e}", exc_info=True)
            self.faiss_indexer.build_index([], np.array([]))

    def get_embedding(self, text: str) -> Optional[List[float]]:
        """텍스트의 임베딩을 생성합니다."""
        return self.embedding_manager._get_embedding(text)

    def _extract_metadata_from_s3_key(self, s3_key: str) -> Tuple[str, str]:
        """S3 키에서 업종명과 원본 파일명을 추출합니다."""
        path_parts = s3_key.split('/')
        industry_name = path_parts[0] if len(path_parts) > 1 else "unspecified"
        
        # URL 해시 제거하여 원본 파일명 복원
        original_filename = re.sub(r'_[0-9a-fA-F]{8}\.txt$', '.txt', path_parts[-1])
        
        return industry_name, original_filename

    def _process_document_for_vector_db(self, s3_key: str, user_id: int) -> None:
        """S3 문서를 로드, 청킹, 임베딩하여 PgVector DB에 저장합니다."""
        logger.info(f"S3 키 '{s3_key}'의 문서를 PgVector DB에 처리합니다. 사용자 ID: {user_id}")
        
        try:
            # S3에서 문서 로드
            response = self.s3_client.get_object(Bucket=self.s3_bucket_name, Key=s3_key)
            file_content = response['Body'].read().decode('utf-8', errors='ignore')

            # 메타데이터 추출
            industry_name, original_filename = self._extract_metadata_from_s3_key(s3_key)

            # 문서 청킹
            chunks = chunk_text(file_content)
            if not chunks:
                logger.warning(f"S3 키 '{s3_key}'에서 청크를 생성할 수 없습니다.")
                return

            # 청크별 임베딩 생성 및 메타데이터 구성
            processed_chunks = []
            embeddings = []
            
            for i, chunk_content in enumerate(chunks):
                if not isinstance(chunk_content, str):
                    logger.warning(f"청크 {i}가 문자열이 아닙니다. 건너뜁니다.")
                    continue

                embedding = self.get_embedding(chunk_content)
                if embedding is None:
                    logger.error(f"S3 키 '{s3_key}'의 청크 {i} 임베딩 생성 실패. 건너뜁니다.")
                    continue
                
                metadata = {
                    "s3_key": s3_key,
                    "user_id": user_id,
                    "industry": industry_name,
                    "original_filename": original_filename,
                    "chunk_index": i,
                }
                
                processed_chunks.append((chunk_content, metadata))
                embeddings.append(embedding)

            if not processed_chunks:
                logger.warning(f"S3 키 '{s3_key}'에 처리 가능한 청크가 없습니다.")
                return

            # PgVector DB에 저장
            with current_app.app_context():
                self.pgvector_store.add_vectors(processed_chunks, embeddings)
                
            logger.info(f"문서 '{s3_key}'이 PgVector DB에 성공적으로 처리되었습니다.")
            
        except Exception as e:
            logger.error(f"문서 '{s3_key}' 처리 실패: {e}", exc_info=True)
            raise

    def add_document_to_rag_system(self, s3_key: str, user_id: int) -> None:
        """새로운 문서를 RAG 시스템에 추가하고 인덱스를 재구성합니다."""
        self._process_document_for_vector_db(s3_key, user_id)
        self._load_faiss_from_pgvector()
        logger.info(f"문서 '{s3_key}'이 추가되고 FAISS 인덱스가 재로드되었습니다.")

    def remove_document_from_rag_system(self, s3_key: str) -> None:
        """RAG 시스템에서 문서를 제거하고 인덱스를 재구성합니다."""
        try:
            with current_app.app_context():
                self.pgvector_store.delete_vector_by_file(s3_key)
            logger.info(f"문서 '{s3_key}'이 PgVector DB에서 제거되었습니다.")
            
            self._load_faiss_from_pgvector()
            logger.info(f"문서 '{s3_key}'이 제거되고 FAISS 인덱스가 재로드되었습니다.")
            
        except Exception as e:
            logger.error(f"문서 '{s3_key}' 제거 실패: {e}", exc_info=True)
            raise

    def retrieve(self, query_text: str, k: int = 3, user_id: Optional[int] = None) -> List[Tuple[str, float, dict]]:
        """
        쿼리 텍스트에 대해 가장 관련성 높은 문서를 검색합니다.
        
        Args:
            query_text: 검색할 쿼리 텍스트
            k: 반환할 최대 결과 수
            user_id: 사용자 ID (필터링용)
            
        Returns:
            (청크_텍스트, 유사도_점수, 메타데이터) 튜플의 리스트
        """
        query_embedding = self.get_embedding(query_text)
        if query_embedding is None:
            logger.warning("쿼리 임베딩 생성 실패. 검색을 수행할 수 없습니다.")
            return []

        # PgVector DB에서 우선 검색
        logger.info(f"사용자 ID {user_id}에 대해 PgVector DB에서 검색합니다.")
        pgvector_results = self.pgvector_store.search(query_embedding, k, user_id=user_id)
        
        if pgvector_results:
            logger.info(f"PgVector DB에서 {len(pgvector_results)}개 청크를 검색했습니다.")
            return [(chunk, score, metadata) for chunk, score, metadata in pgvector_results]
        
        # PgVector DB에 결과가 없으면 FAISS에서 검색
        logger.warning("PgVector DB에 관련 청크가 없습니다. FAISS에서 검색합니다.")
        faiss_results = self.faiss_indexer.search(query_embedding, k)
        
        if faiss_results:
            logger.info(f"FAISS에서 {len(faiss_results)}개 청크를 검색했습니다.")
            return [(chunk, 0.0, {}) for chunk in faiss_results]  # FAISS는 점수를 제공하지 않음
        
        logger.warning("FAISS에서도 관련 청크를 찾을 수 없습니다.")
        return []


# 싱글톤 인스턴스 관리
_rag_system_instance: Optional[RAGSystem] = None


def init_rag_system(bedrock_runtime_client: Any) -> Optional[RAGSystem]:
    """RAGSystem 인스턴스를 초기화하고 싱글톤으로 설정합니다."""
    global _rag_system_instance
    
    try:
        if _rag_system_instance is None:
            s3_client = current_app.extensions.get('s3_client')
            s3_bucket_name = current_app.config.get('S3_BUCKET_NAME')
            
            if not s3_client or not s3_bucket_name:
                raise ValueError("Flask 앱에서 S3 클라이언트 또는 버킷 이름이 설정되지 않았습니다.")
            
            _rag_system_instance = RAGSystem(bedrock_runtime_client, s3_client, s3_bucket_name)
            logger.info("RAGSystem 인스턴스가 성공적으로 초기화되었습니다.")
        else:
            logger.info("RAGSystem 인스턴스가 이미 존재합니다. 초기화를 건너뜁니다.")
            
    except Exception as e:
        logger.critical(f"RAGSystem 초기화 중 치명적 오류 발생: {e}", exc_info=True)
        _rag_system_instance = None
    
    return _rag_system_instance


def get_rag_system() -> Optional[RAGSystem]:
    """초기화된 RAGSystem 인스턴스를 반환합니다."""
    if _rag_system_instance is None:
        logger.warning("RAGSystem이 초기화되지 않았습니다. init_rag_system을 먼저 호출하세요.")
    return _rag_system_instance