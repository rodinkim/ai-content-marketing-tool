# ai-content-marketing-tool/services/ai_rag/embedding_generator.py

import boto3
import json
import numpy as np
import logging
from typing import Optional, Union, Dict, List

from .ai_constants import EMBEDDING_MODEL_ID # 임베딩 모델 ID 상수 임포트

logger = logging.getLogger(__name__)

# 단일 함수로 임베딩을 생성하는 기능
def get_embedding(bedrock_runtime_client: boto3.client, text: Union[str, Dict, List, None]) -> Optional[np.ndarray]:
    """텍스트를 받아 Bedrock Titan Text Embeddings v2를 사용하여 임베딩 생성"""
    if text is None:
        logger.warning("get_embedding: Input text is None. Embedding generation skipped.")
        return None
    
    final_input_text = ""
    if isinstance(text, str):
        final_input_text = text
    else:
        try:
            final_input_text = json.dumps(text, ensure_ascii=False)
            logger.warning(f"get_embedding: Input text is not a string ({type(text)}). JSON serialization used.")
        except TypeError:
            final_input_text = str(text)
            logger.warning(f"get_embedding: Input text cannot be JSON serialized. Converted to string with str() ({type(text)}).")
        except Exception as e:
            logger.error(f"get_embedding: Unexpected error during input text conversion: {e}", exc_info=True)
            return None

    body = json.dumps({"inputText": final_input_text})

    try:
        response = bedrock_runtime_client.invoke_model(
            body=body,
            modelId=EMBEDDING_MODEL_ID,
            accept="application/json",
            contentType="application/json"
        )
        response_body = json.loads(response.get('body').read())
        return np.array(response_body.get("embedding"), dtype=np.float32)
    except Exception as e:
        log_text_preview = final_input_text[:50] if isinstance(final_input_text, str) else str(type(final_input_text))
        logger.error(f"Error getting embedding for text: '{log_text_preview}'... Error: {e}", exc_info=True)
        return None

# AIContentGenerator에서 사용될 EmbeddingManager 클래스 (재정의)
class EmbeddingManager:
    """임베딩 관련 로직 (업종 임베딩 사전 계산 등)을 관리합니다."""

    def __init__(self, rag_system_instance):
        self.rag_system = rag_system_instance
        self.industry_embeddings: Dict[str, np.ndarray] = {} # 업종별 임베딩 캐시

    def precompute_industry_embeddings(self, industries: list[str]):
        """사전 정의된 업종 목록에 대한 임베딩을 미리 계산하여 캐시합니다."""
        logger.info("Precomputing industry embeddings...")
        for industry in industries:
            # EmbeddingManager가 rag_system 인스턴스를 통해 get_embedding을 호출
            # rag_system의 get_embedding은 다시 외부의 get_embedding 함수를 호출 (self.rag_system.get_embedding)
            # 여기서는 rag_system에서 제공하는 get_embedding을 사용합니다.
            embedding = self.rag_system.get_embedding(industry) 
            if embedding is not None:
                self.industry_embeddings[industry] = embedding
            else:
                logger.warning(f"업종 '{industry}'에 대한 임베딩 생성 실패.")
        logger.info(f"Finished precomputing {len(self.industry_embeddings)} industry embeddings.")

    def get_industry_embedding(self, industry: str) -> np.ndarray | None:
        """캐시된 업종 임베딩을 반환합니다."""
        return self.industry_embeddings.get(industry)