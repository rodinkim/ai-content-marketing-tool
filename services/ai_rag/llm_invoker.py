# ai-content-marketing-tool/services/ai_rag/llm_invoker.py

import json
import logging
import boto3 # boto3는 Bedrock 클라이언트를 위해 필요합니다.

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
        # Claude 3.5 Sonnet 응답 파싱은 'content' 리스트의 첫 번째 'text' 필드에 있습니다.
        return response_body['content'][0]['text']
    except Exception as e:
        logger.error(f"LLM 호출 실패: {e}")
        # 오류 발생 시 더 명확한 예외를 발생시켜 상위 호출자가 처리하도록 합니다.
        raise RuntimeError(f"콘텐츠 생성 중 LLM 호출 오류 발생: {e}")