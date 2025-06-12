# ai-content-marketing-tool/services/embedding_manager.py

import logging
import numpy as np
from typing import Dict, Any

logger = logging.getLogger(__name__)

class EmbeddingManager:
    """임베딩 관련 로직 (업종 임베딩 사전 계산 등)을 관리합니다."""

    def __init__(self, rag_system_instance):
        self.rag_system = rag_system_instance
        self.industry_embeddings: Dict[str, np.ndarray] = {} # 업종별 임베딩 캐시

    def precompute_industry_embeddings(self, industries: list[str]):
        """사전 정의된 업종 목록에 대한 임베딩을 미리 계산하여 캐시합니다."""
        logger.info("Precomputing industry embeddings...")
        for industry in industries:
            embedding = self.rag_system.get_embedding(industry)
            if embedding is not None:
                self.industry_embeddings[industry] = embedding
            else:
                logger.warning(f"업종 '{industry}'에 대한 임베딩 생성 실패.")
        logger.info(f"Finished precomputing {len(self.industry_embeddings)} industry embeddings.")

    def get_industry_embedding(self, industry: str) -> np.ndarray | None:
        """캐시된 업종 임베딩을 반환합니다."""
        return self.industry_embeddings.get(industry)