# ai-content-marketing-tool/services/ai_rag/llm_invoker.py

import json
import logging
import boto3 # boto3는 Bedrock 클라이언트를 위해 필요합니다.
from abc import ABC, abstractmethod

logger = logging.getLogger(__name__)

class LLMProvider(ABC):
    """모든 LLM 모델 제공자가 따라야 하는 공통 인터페이스입니다."""
    @abstractmethod
    def invoke(self, prompt: str, model_id: str, **kwargs) -> str:
        """LLM을 호출하여 콘텐츠를 생성합니다."""
        pass

class BedrockClaudeProvider(LLMProvider):
    """Bedrock을 통해 Anthropic Claude 모델을 호출하는 Provider입니다."""
    def __init__(self, bedrock_runtime_client: boto3.client):
        self.bedrock_runtime = bedrock_runtime_client

    def invoke(self, prompt: str, model_id: str, max_tokens: int) -> str:
        """Bedrock Claude 모델을 호출하고 응답을 파싱합니다."""
        body = json.dumps({
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": max_tokens,
            "messages": [
                {"role": "user", "content": prompt}
            ]
        })
        try:
            response = self.bedrock_runtime.invoke_model(
                body=body,
                modelId=model_id,
                accept="application/json",
                contentType="application/json"
            )
            response_body = json.loads(response.get('body').read())
            return response_body['content'][0]['text']
        except Exception as e:
            logger.error(f"LLM 호출 실패: {e}")
            raise RuntimeError(f"콘텐츠 생성 중 LLM 호출 오류 발생: {e}")