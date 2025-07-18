# ai-content-marketing-tool/services/ai_rag/__init__.py

"""
RAG (Retrieval-Augmented Generation) 시스템 모듈들

이 패키지는 다음과 같은 RAG 관련 기능들을 포함합니다:

- rag_system.py: RAG 시스템의 핵심 로직 (검색 + 생성)
- pgvector_store.py: PostgreSQL 벡터 저장소 (RAG 데이터 레이어)
- chunker.py: 텍스트 청킹 유틸리티
- embedding_generator.py: 임베딩 생성 및 관리
- faiss_indexer.py: FAISS 벡터 인덱싱
"""

from .rag_system import RAGSystem
from .pgvector_store import PgVectorStore
from .chunker import chunk_text
from .embedding_generator import EmbeddingManager
from .faiss_indexer import FaissIndexer

__all__ = [
    'RAGSystem',
    'PgVectorStore',
    'chunk_text',
    'EmbeddingManager',
    'FaissIndexer'
]
