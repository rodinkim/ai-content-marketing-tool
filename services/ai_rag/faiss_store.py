# ai-content-marketing-tool/services/ai_rag/faiss_store.py

import logging
from typing import List, Tuple, Optional
import numpy as np
import faiss
import os
import pickle

logger = logging.getLogger(__name__)

class FaissStore:
    def __init__(self, index_path: str = "faiss_index.bin", dim: int = 768):
        self.index_path = index_path
        self.dim = dim
        self.index = None
        self.metadata = []  # List[dict], 각 벡터의 메타데이터
        self._load_index()
        logger.info(f"FaissStore 초기화 완료. index_path={self.index_path}, dim={self.dim}")

    def _load_index(self):
        if os.path.exists(self.index_path):
            with open(self.index_path, "rb") as f:
                self.index = faiss.read_index("faiss.index")
                self.metadata = pickle.load(f)
            logger.info("FAISS 인덱스 및 메타데이터 로드 완료.")
        else:
            self.index = faiss.IndexFlatL2(self.dim)
            self.metadata = []
            logger.info("새로운 FAISS 인덱스 생성.")

    def _save_index(self):
        faiss.write_index(self.index, "faiss.index")
        with open(self.index_path, "wb") as f:
            pickle.dump(self.metadata, f)
        logger.info("FAISS 인덱스 및 메타데이터 저장 완료.")

    def add_vectors(self, chunks_data: List[Tuple[str, dict]], embeddings: List[List[float]]):
        """
        새로운 벡터와 메타데이터를 FAISS 인덱스에 추가합니다.
        """
        vectors = np.array(embeddings).astype('float32')
        self.index.add(vectors)
        for i, (_, chunk_metadata) in enumerate(chunks_data):
            self.metadata.append(chunk_metadata)
        self._save_index()
        logger.info(f"FAISS 인덱스에 {len(embeddings)}개 벡터 추가 완료.")

    def search(self, query_embedding: List[float], k: int = 3) -> List[Tuple[str, float, dict]]:
        """
        쿼리 임베딩과 가장 유사한 k개의 벡터를 검색합니다.
        반환: (chunk_text, 유사도 점수, 메타데이터)
        """
        if self.index.ntotal == 0:
            logger.warning("FAISS 인덱스에 벡터가 없습니다.")
            return []
        query = np.array(query_embedding).reshape(1, -1).astype('float32')
        D, I = self.index.search(query, k)
        results = []
        for idx, dist in zip(I[0], D[0]):
            if idx < len(self.metadata):
                meta = self.metadata[idx]
                chunk_text = meta.get('text_content', '')
                similarity = 1 / (1 + dist)  # L2 거리 → 유사도 변환
                results.append((chunk_text, similarity, meta))
        logger.info(f"FAISS 인덱스에서 {len(results)}개 유사 문서 검색 완료.")
        return results

    def clear_vectors(self):
        """
        모든 벡터와 메타데이터를 삭제합니다.
        """
        self.index = faiss.IndexFlatL2(self.dim)
        self.metadata = []
        self._save_index()
        logger.info("FAISS 인덱스 및 메타데이터 전체 삭제 완료.")

    def delete_vector_by_index(self, idx: int):
        """
        특정 인덱스의 벡터와 메타데이터를 삭제합니다.
        (FAISS는 인덱스 삭제가 복잡하므로, 재구성 방식 사용)
        """
        if idx < 0 or idx >= len(self.metadata):
            logger.warning(f"잘못된 인덱스: {idx}")
            return
        self.metadata.pop(idx)
        vectors = self.index.reconstruct_n(0, self.index.ntotal)
        vectors = np.delete(vectors, idx, axis=0)
        self.index = faiss.IndexFlatL2(self.dim)
        self.index.add(vectors)
        self._save_index()
        logger.info(f"FAISS 인덱스에서 {idx}번 벡터 삭제 완료.")
