# ai-content-marketing-tool/services/ai_rag/llm_invoker.py

import json
import base64
import logging
from abc import ABC, abstractmethod
from typing import Any, Optional
import boto3

logger = logging.getLogger(__name__)

class LLMProvider(ABC):
    """
    LLM(텍스트/이미지 생성) Provider의 공통 인터페이스.
    """
    @abstractmethod
    def invoke(self, prompt: str, **kwargs) -> Any:
        """
        LLM을 호출하여 결과를 반환합니다.
        """
        pass

class BedrockClaudeProvider(LLMProvider):
    """
    Bedrock Claude(Anthropic) 텍스트 LLM 호출 Provider.
    """
    def __init__(self, bedrock_runtime_client: boto3.client, model_id: str):
        self.bedrock_runtime = bedrock_runtime_client
        self.model_id = model_id

    def invoke(self, prompt: str, max_tokens: int, temperature: float, top_p: float, **kwargs) -> str:
        """
        Claude LLM을 호출하여 텍스트를 생성합니다.
        """
        messages = [
            {"role": "user", "content": [{"type": "text", "text": prompt}]}
        ]
        body = json.dumps({
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": max_tokens,
            "temperature": temperature,
            "top_p": top_p,
            "messages": messages
        })
        try:
            response = self.bedrock_runtime.invoke_model(
                body=body,
                modelId=self.model_id,
                accept="application/json",
                contentType="application/json"
            )
            response_body = json.loads(response.get('body').read())
            # Claude 응답에서 텍스트 추출
            if 'content' in response_body and response_body['content']:
                return response_body['content'][0]['text']
            logger.warning(f"Claude 모델 응답에서 텍스트 콘텐츠를 찾을 수 없습니다: {response_body}")
            raise RuntimeError("Claude 모델 응답에 유효한 텍스트 콘텐츠가 없습니다.")
        except Exception as e:
            logger.error(f"LLM 호출 실패: {e}", exc_info=True)
            raise RuntimeError(f"콘텐츠 생성 중 LLM 호출 오류 발생: {e}")

class BedrockImageGeneratorProvider(LLMProvider):
    """
    Stable Image Core 모델을 호출하는 Provider.
    """
    def __init__(self, image_bedrock_client: boto3.client, model_id: str):
        self.bedrock_client = image_bedrock_client
        self.model_id = model_id

    def invoke(self, prompt: str, **kwargs) -> Optional[bytes]:
        """
        Stable Image Core 모델을 호출하여 이미지를 생성합니다.
        """
        if not self.bedrock_client:
            return None
        # 요청 본문 구성
        body = json.dumps({
            "prompt": prompt,
            "seed": kwargs.get('seed', 0),
            "output_format": kwargs.get('output_format', 'png'),
            "aspect_ratio": kwargs.get('aspect_ratio', '1:1'),
            "mode": kwargs.get('mode', 'text-to-image'),
            **({"negative_prompt": kwargs['negative_prompt']} if kwargs.get('negative_prompt') else {}),
            **({"strength": kwargs['strength']} if kwargs.get('mode', 'text-to-image') == 'image-to-image' and kwargs.get('strength') is not None else {})
        })
        try:
            response = self.bedrock_client.invoke_model(
                body=body,
                modelId=self.model_id,
                accept="application/json",
                contentType="application/json"
            )
            response_body = json.loads(response.get("body").read())
            images = response_body.get('images')
            # 첫 번째 이미지만 반환
            if images and len(images) > 0:
                return base64.b64decode(images[0])
            return None
        except Exception:
            return None