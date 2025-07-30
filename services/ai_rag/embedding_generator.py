# ai-content-marketing-tool/services/utils/embedding_generator.py

import boto3
import json
import numpy as np
import logging
from typing import Optional, Union, Dict, List
from config import config

logger = logging.getLogger(__name__)

class EmbeddingManager:
    """
    임베딩 관련 로직(텍스트 임베딩 생성, 업종 임베딩 캐싱 등)을 관리하는 유틸리티 클래스.
    Bedrock Titan Text Embeddings v2 기반.
    """

    def __init__(self, bedrock_runtime_client: boto3.client):
        """
        EmbeddingManager를 초기화합니다.
        bedrock_runtime_client: Bedrock API 호출용 boto3 클라이언트
        """
        self.bedrock_runtime_client = bedrock_runtime_client
        self.industry_embeddings: Dict[str, np.ndarray] = {}  # 업종별 임베딩 캐시

    def _get_embedding(self, text: Union[str, Dict, List, None]) -> Optional[np.ndarray]:
        """
        텍스트(또는 JSON)를 받아 Bedrock Titan Text Embeddings v2로 임베딩 벡터를 생성합니다.
        """
        if not text:
            logger.warning("_get_embedding: Input text is empty or None.")
            return None
        # 입력값이 문자열이 아니면 JSON 문자열로 변환
        final_input_text = text if isinstance(text, str) else json.dumps(text, ensure_ascii=False)
        body = json.dumps({"inputText": final_input_text})
        try:
            response = self.bedrock_runtime_client.invoke_model(
                body=body,
                modelId=config.EMBEDDING_MODEL_ID,
                accept="application/json",
                contentType="application/json"
            )
            response_body = json.loads(response.get('body').read())
            return np.array(response_body.get("embedding"), dtype=np.float32)
        except Exception as e:
            logger.error(f"Error getting embedding for text: '{str(text)[:50]}'... Error: {e}", exc_info=True)
            return None

    def precompute_industry_embeddings(self, industries: List[str]):
        """
        사전 정의된 업종 목록에 대한 임베딩을 미리 계산하여 캐시합니다.
        (예: RAG에서 업종별 유사도 검색에 활용)
        """
        logger.info("Precomputing industry embeddings...")
        for industry in industries:
            embedding = self._get_embedding(industry)
            if embedding is not None:
                self.industry_embeddings[industry] = embedding
            else:
                logger.warning(f"업종 '{industry}'에 대한 임베딩 생성 실패.")
        logger.info(f"Finished precomputing {len(self.industry_embeddings)} industry embeddings.")

    def get_industry_embedding(self, industry: str) -> Optional[np.ndarray]:
        """
        캐시된 업종 임베딩을 반환합니다. (없으면 None)
        """
        return self.industry_embeddings.get(industry)