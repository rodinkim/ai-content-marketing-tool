# ai-content-marketing-tool/services/ai_rag/faiss_indexer.py

import faiss
import numpy as np
import logging
from typing import List, Optional, Tuple # 타입 힌트를 위한 임포트

logger = logging.getLogger(__name__) # 모듈 레벨 로거 초기화

class FaissIndexer:
    """FAISS 인덱스를 관리하고 벡터 검색을 수행합니다."""

    def __init__(self):
        self.index: Optional[faiss.IndexFlatL2] = None # FAISS 인덱스 객체, 초기에는 None
        self.documents: List[str] = [] # 인덱싱된 청크 텍스트 리스트 (FAISS 인덱스의 벡터와 1:1 매핑)

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
            self.index = None # 인덱스를 비웁니다.
            self.documents = [] # 문서 리스트도 비웁니다.
            return

        self.documents = document_chunks # 문서 청크를 클래스 변수에 저장
        d = embeddings.shape[1] # 임베딩 벡터의 차원 (예: Titan 임베딩은 1024 512 256)
        
        # FAISS IndexFlatL2 생성: L2 (유클리드) 거리 기반의 평면 인덱스
        self.index = faiss.IndexFlatL2(d) 
        self.index.add(embeddings) # 임베딩 벡터들을 인덱스에 추가
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
        if not self.documents: # self.documents가 비어있는지 확인
            logger.warning("No documents loaded into FAISS index. Cannot perform search.")
            return []

        # FAISS 검색을 위해 쿼리 임베딩의 차원(ndim)을 2차원으로 조정 (FAISS는 2D 입력을 기대함)
        # 단일 쿼리 벡터일 경우 (1, D) 형태로 변환
        if query_embedding.ndim == 1:
            query_embedding = query_embedding.reshape(1, -1)

        # FAISS 인덱스에서 유사한 벡터 검색을 수행합니다.
        # D: 거리 (Distances), I: 인덱스 (Indices)
        D, I = self.index.search(query_embedding, k)
        
        retrieved_docs: List[str] = []
        # 검색된 인덱스(I)를 사용하여 실제 문서 청크를 가져옵니다.
        # I[0]은 첫 번째 쿼리(우리는 보통 1개 쿼리)에 대한 결과 인덱스 리스트입니다.
        for i in I[0]: 
            if 0 <= i < len(self.documents): # 검색된 인덱스가 유효한 범위 내에 있는지 확인
                retrieved_docs.append(self.documents[i])
            else:
                logger.warning(f"Warning: Invalid index {i} found during FAISS search. Index out of bounds.")
        return retrieved_docs