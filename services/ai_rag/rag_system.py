# ai-content-marketing-tool/services/ai_rag/rag_system.py

import boto3
import json
import numpy as np
import logging
import os

# --- 새로 분리된 모듈들을 상대 경로로 임포트합니다. ---
from .embedding_generator import get_embedding       # get_embedding 함수 임포트
from .chunker import chunk_text                      # chunk_text 함수 임포트 (document_loader에서 사용)
from .document_loader import load_documents_from_directory # load_documents_from_directory 함수 임포트
from .faiss_indexer import FaissIndexer              # FaissIndexer 클래스 임포트
from .ai_constants import ENCODER, CHUNK_SIZE, CHUNK_OVERLAP # 상수 임포트

logger = logging.getLogger(__name__)

# ENCODER, CHUNK_SIZE, CHUNK_OVERLAP 상수는 이제 ai_constants.py에 정의되어 있으므로,
# 이 파일에서는 직접 상수를 재정의하지 않습니다.

class RAGSystem:
    def __init__(self, bedrock_runtime_client, knowledge_base_dir):
        self.bedrock_runtime = bedrock_runtime_client
        if not self.bedrock_runtime:
            logger.critical("RAGSystem 초기화 실패: Bedrock runtime 클라이언트가 유효하지 않습니다.")
            raise ValueError("Bedrock runtime 클라이언트가 유효하지 않아 RAGSystem을 초기화할 수 없습니다.")

        self.knowledge_base_dir = knowledge_base_dir
        self.faiss_indexer = FaissIndexer() # FaissIndexer 인스턴스를 생성하여 RAGSystem 내에서 관리
        self.load_and_process_knowledge_base() # 인스턴스 생성 시 지식 베이스 로드 및 처리

    # 기존 RAGSystem 클래스에 있던 get_embedding 메서드와 chunk_text 메서드는
    # 각각 embedding_generator.py와 chunker.py로 분리되었으므로 여기서는 삭제합니다.
    # 대신, RAGSystem의 get_embedding은 외부 함수를 호출하는 래퍼(wrapper) 역할을 합니다.
    def get_embedding(self, text):
        """EmbeddingGenerator 모듈의 get_embedding 함수를 호출합니다.
        self.bedrock_runtime 클라이언트를 인자로 전달합니다."""
        return get_embedding(self.bedrock_runtime, text)

    def load_and_process_knowledge_base(self):
        """
        지식 베이스 디렉토리에서 문서를 로드하고, 청크로 분할하여 임베딩을 생성한 후 FAISS 인덱스를 구축합니다.
        """
        logger.info(f"Loading knowledge base from: {self.knowledge_base_dir}")
        
        # 1. 문서 로드 및 청크 분할: document_loader.py의 함수를 사용합니다.
        all_chunks = load_documents_from_directory(self.knowledge_base_dir)

        if not all_chunks:
            logger.warning("No documents (or chunks) found for knowledge base. FAISS index will not be built.")
            logger.warning("Please ensure your 'knowledge_base' directory contains .txt files, possibly in subdirectories.")
            self.faiss_indexer.build_index([], np.array([])) # 문서가 없어도 빈 인덱스는 구축
            return

        # 2. 각 청크에 대한 임베딩 생성
        temp_embeddings = []
        for i, chunk in enumerate(all_chunks):
            # RAGSystem의 get_embedding 래퍼 메서드를 호출하여 임베딩을 가져옵니다.
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
        
        # 3. FAISS 인덱스 구축: faiss_indexer.py의 FaissIndexer 인스턴스를 사용합니다.
        self.faiss_indexer.build_index(all_chunks, embeddings_array)
        logger.info(f"Knowledge base loaded and indexed. Total chunks: {len(all_chunks)}, Embedding dimension: {embeddings_array.shape[1]}")

    def retrieve(self, query_text, k=3):
        """쿼리 텍스트와 유사한 문서 청크 검색 (faiss_indexer.py의 FaissIndexer 사용)"""
        # 쿼리 텍스트에 대한 임베딩을 가져옵니다.
        query_embedding = self.get_embedding(query_text)
        if query_embedding is None:
            logger.warning("Failed to get embedding for query text. Cannot perform retrieval.")
            return []

        # FaissIndexer 인스턴스의 search 메서드를 호출하여 유사 문서를 검색합니다.
        return self.faiss_indexer.search(query_embedding, k)

# RAGSystem 싱글톤 인스턴스를 저장할 변수
_rag_system_instance = None

def init_rag_system(bedrock_runtime_client):
    """
    RAGSystem 인스턴스를 초기화하고 싱글톤으로 설정합니다.
    """
    global _rag_system_instance
    if _rag_system_instance is None:
        try:
            # Flask의 current_app은 앱 컨텍스트 내에서만 사용 가능하므로,
            # 이 함수 내에서만 임포트합니다.
            from flask import current_app 
            knowledge_base_path = os.path.join(current_app.root_path, "knowledge_base")
            _rag_system_instance = RAGSystem(bedrock_runtime_client, knowledge_base_dir=knowledge_base_path) 
            logger.info("RAGSystem 인스턴스가 성공적으로 초기화되었습니다.")
        except Exception as e:
            logger.critical(f"RAGSystem 인스턴스 초기화 중 치명적인 오류 발생: {e}", exc_info=True)
            _rag_system_instance = None
    return _rag_system_instance

def get_rag_system():
    """초기화된 RAGSystem 인스턴스를 반환합니다."""
    if _rag_system_instance is None:
        logger.warning("RAGSystem이 아직 초기화되지 않았습니다. init_rag_system을 먼저 호출해야 합니다.")
    return _rag_system_instance