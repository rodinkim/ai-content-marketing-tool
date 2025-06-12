# ai-content-marketing-tool/services/llm_invoker.py

import json
import logging
import boto3 # 타입 힌트와 실제 Bedrock 클라이언트 사용을 위해 필요

logger = logging.getLogger(__name__)

def invoke_claude_llm(bedrock_runtime_client: boto3.client, 
                      prompt: str, 
                      model_id: str, 
                      max_tokens: int) -> str:
    """Bedrock Claude 모델을 호출하고 응답을 파싱합니다."""
    body = json.dumps({
        "anthropic_version": "bedrock-2023-05-31",
        "max_tokens": max_tokens,
        "messages": [
            {"role": "user", "content": prompt}
        ]
    })
    try:
        response = bedrock_runtime_client.invoke_model(
            body=body,
            modelId=model_id,
            accept="application/json",
            contentType="application/json"
        )
        response_body = json.loads(response.get('body').read())
        # Claude 3.5 Sonnet 응답 파싱
        return response_body['content'][0]['text']
    except Exception as e:
        logger.error(f"LLM 호출 실패: {e}")
        raise RuntimeError(f"콘텐츠 생성 중 오류 발생: {e}")