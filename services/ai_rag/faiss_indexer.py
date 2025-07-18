# ai-content-marketing-tool/services/utils/faiss_indexer.py

import faiss
import numpy as np
import logging
from typing import List, Optional, Tuple # 타입 힌트를 위한 임포트

logger = logging.getLogger(__name__)

class FaissIndexer:
    """FAISS 인덱스를 관리하고 벡터 검색을 수행하는 유틸리티 클래스."""

    def __init__(self):
        # FAISS 인덱스 객체, 초기에는 None
        self.index: Optional[faiss.IndexFlatL2] = None
        # 인덱싱된 청크 텍스트 리스트 (FAISS 인덱스의 벡터와 1:1 매핑)
        self.documents: List[str] = []

    def build_index(self, document_chunks: List[str], embeddings: np.ndarray):
        """
        주어진 문서 청크와 해당 임베딩으로 FAISS 인덱스를 구축합니다.
        Args:
            document_chunks: 인덱싱할 텍스트 청크들의 리스트.
            embeddings: 각 청크에 해당하는 임베딩 벡터들의 NumPy 배열.
        """
        # 입력 데이터가 없으면 인덱스 구축을 건너뛰고 경고를 남깁니다.
        if not document_chunks or embeddings is None or embeddings.size == 0:
            logger.warning("No document chunks or embeddings provided to build FAISS index. Index will be empty.")
            self.index = None
            self.documents = []
            return

        self.documents = document_chunks
        d = embeddings.shape[1]  # 임베딩 벡터의 차원 (예: 1024, 512, 256 등)
        # L2(유클리드) 거리 기반의 평면 인덱스 생성
        self.index = faiss.IndexFlatL2(d)
        self.index.add(embeddings)
        logger.info(f"FAISS index built. Total indexed chunks: {len(self.documents)}, Embedding dimension: {d}")

    def search(self, query_embedding: np.ndarray, k: int = 3) -> List[str]:
        """
        주어진 쿼리 임베딩과 가장 유사한 상위 K개 문서 청크를 검색합니다.
        Args:
            query_embedding: 검색할 쿼리 텍스트의 임베딩 벡터 (NumPy 배열).
            k: 검색할 상위 유사 문서 청크의 개수.
        Returns:
            쿼리와 유사한 문서 청크 텍스트들의 리스트.
        """
        # 인덱스가 초기화되지 않았거나 문서가 로드되지 않았으면 검색 불가능
        if self.index is None:
            logger.warning("FAISS index is not initialized. Cannot perform search.")
            return []
        if not self.documents:
            logger.warning("No documents loaded into FAISS index. Cannot perform search.")
            return []

        # 쿼리 임베딩을 2차원 배열로 변환 (FAISS는 2D 입력을 기대함)
        if query_embedding.ndim == 1:
            query_embedding = query_embedding.reshape(1, -1)

        # FAISS 인덱스에서 유사한 벡터 검색
        D, I = self.index.search(query_embedding, k)
        retrieved_docs: List[str] = []
        # 검색된 인덱스(I)를 사용하여 실제 문서 청크를 가져옴
        for i in I[0]:
            if 0 <= i < len(self.documents):
                retrieved_docs.append(self.documents[i])
            else:
                logger.warning(f"Warning: Invalid index {i} found during FAISS search. Index out of bounds.")
        return retrieved_docs