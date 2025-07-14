# ai-content-marketing-tool/services/ai_rag/llm_invoker.py

import json
import base64
import io
import logging
from PIL import Image
from flask import current_app 
from abc import ABC, abstractmethod
from typing import Any, Union
import boto3

logger = logging.getLogger(__name__)

class LLMProvider(ABC):
    """모든 LLM 모델 제공자가 따라야 하는 공통 인터페이스입니다."""
    @abstractmethod
    def invoke(self, prompt: str, model_id: str, **kwargs) -> Any: # 반환 타입을 Any로 변경하여 텍스트/이미지 모두 지원
        """LLM을 호출하여 콘텐츠를 생성합니다."""
        pass

class BedrockClaudeProvider(LLMProvider):
    """Bedrock을 통해 Anthropic Claude 모델을 호출하는 Provider입니다."""
    def __init__(self, bedrock_runtime_client: boto3.client):
        self.bedrock_runtime = bedrock_runtime_client

    def invoke(self, prompt: str, model_id: str, **kwargs) -> str:
        """Bedrock Claude 모델을 호출하고 응답을 파싱합니다."""
        max_tokens = kwargs.get('max_tokens', 1000) # 기본값 설정
        temperature = kwargs.get('temperature', 0.7)
        top_p = kwargs.get('top_p', 0.9)

        # Claude 3 모델은 Messages API 형식을 사용합니다.
        # prompt는 텍스트 문자열이므로, content 리스트 안에 딕셔너리 형태로 넣어줍니다.
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
                modelId=model_id,
                accept="application/json",
                contentType="application/json"
            )
            response_body = json.loads(response.get('body').read())

            # Claude 3 Messages API 응답 파싱
            if 'content' in response_body and len(response_body['content']) > 0:
                return response_body['content'][0]['text']
            else:
                logger.warning(f"Claude 모델 응답에서 텍스트 콘텐츠를 찾을 수 없습니다: {response_body}")
                raise RuntimeError("Claude 모델 응답에 유효한 텍스트 콘텐츠가 없습니다.")
            
        except Exception as e:
            logger.error(f"LLM 호출 실패: {e}")
            raise RuntimeError(f"콘텐츠 생성 중 LLM 호출 오류 발생: {e}")
    
class BedrockImageGeneratorProvider(LLMProvider): 
    """Bedrock을 통해 이미지 생성 모델을 호출하는 Provider입니다. 교차 리전 호출을 지원합니다."""
    def __init__(self, bedrock_runtime_client: boto3.client):
        # 기본 클라이언트는 app_factory_utils에서 초기화된 클라이언트 (ap-northeast-2)
        self.bedrock_runtime_default = bedrock_runtime_client
        # 이미지 생성 전용 클라이언트는 필요 시 다른 리전으로 초기화
        self.bedrock_runtime_image_gen = None

    def _get_image_gen_client(self):
        """이미지 생성 모델을 위한 Bedrock 클라이언트를 가져오거나 초기화합니다."""
        if self.bedrock_runtime_image_gen is None:
            image_gen_region = current_app.config.get('IMAGE_GENERATION_REGION_NAME')
            aws_access_key_id = current_app.config.get('AWS_ACCESS_KEY_ID')
            aws_secret_access_key = current_app.config.get('AWS_SECRET_ACCESS_KEY')

            if not image_gen_region or not aws_access_key_id or not aws_secret_access_key:
                logger.error("IMAGE_GENERATION_REGION_NAME 또는 AWS 자격 증명이 설정되지 않았습니다.")
                raise RuntimeError("이미지 생성 서비스에 필요한 설정이 부족합니다.")

            try:
                self.bedrock_runtime_image_gen = boto3.client(
                    service_name='bedrock-runtime',
                    region_name=image_gen_region,
                    aws_access_key_id=aws_access_key_id,
                    aws_secret_access_key=aws_secret_access_key
                )
                logger.info(f"Bedrock image generation client initialized for region: {image_gen_region}")
            except Exception as e:
                logger.error(f"이미지 생성 Bedrock 클라이언트 초기화 실패: {e}", exc_info=True)
                raise RuntimeError(f"이미지 생성 Bedrock 클라이언트 초기화 실패: {e}")
        return self.bedrock_runtime_image_gen


    def invoke(self, prompt: str, model_id: str, **kwargs) -> bytes | None:
        """
        Bedrock 이미지 생성 모델을 호출하고 이미지 바이트 데이터를 반환합니다.
        모델 ID에 따라 요청 본문 형식을 조정합니다.
        """
        bedrock_runtime = self._get_image_gen_client() 
        if not bedrock_runtime:
            return None 

        # width, height는 Stable Image Core 모델의 요청 본문에서 직접 사용되지 않음
        # 대신 aspect_ratio를 통해 간접적으로 제어됩니다.
        # kwargs에서 aspect_ratio를 가져옵니다.
        aspect_ratio = kwargs.get('aspect_ratio', '1:1') 
        # Stable Image Core 모델이 지원하는 파라미터만 사용합니다.
        # 오류 메시지: Available fields for core are: prompt, negative_prompt, mode, strength, seed, output_format, image, aspect_ratio
        seed = kwargs.get('seed', 0)
        output_format = kwargs.get('output_format', 'png')
        negative_prompt = kwargs.get('negative_prompt') # negative_prompt도 추가 가능
        mode = kwargs.get('mode', 'text-to-image') # text-to-image 또는 image-to-image
        strength = kwargs.get('strength') # mode가 image-to-image일 때 필요

        # #### START MODIFICATION ####
        # Stable Image Core 모델의 요청 본문 형식 수정
        # 'cfg_scale', 'steps', 'width', 'height'는 이 모델에서 지원되지 않으므로 제거합니다.
        # 'prompt' 키는 최상위 레벨에 직접 와야 합니다.
        if model_id.startswith("stability.stable-image-core"):
            request_body_params = {
                "prompt": prompt,
                "seed": seed,
                "output_format": output_format,
                "aspect_ratio": aspect_ratio
            }
            if negative_prompt:
                request_body_params["negative_prompt"] = negative_prompt
            if mode:
                request_body_params["mode"] = mode
            if mode == 'image-to-image' and strength is not None:
                request_body_params["strength"] = strength
            # 'image' 필드는 image-to-image 모드일 때 필요하지만, 현재는 text-to-image만 가정합니다.

            body = json.dumps(request_body_params)
        # #### END MODIFICATION ####

        elif model_id.startswith("stability."): # 다른 Stability AI Stable Diffusion 계열 모델 (SDXL 등)
            cfg_scale = kwargs.get('cfg_scale', 10)
            seed = kwargs.get('seed', 0)
            steps = kwargs.get('steps', 50)
            sampler = kwargs.get('sampler', "K_DPMPP_2M")

            body = json.dumps(
                {
                    "text_prompts": [{"text": prompt}],
                    "cfg_scale": cfg_scale,
                    "seed": seed,
                    "steps": steps,
                    "width": kwargs.get('width', 1024), 
                    "height": kwargs.get('height', 1024),
                    "sampler": sampler,
                }
            )
        elif model_id.startswith("amazon.titan-image-generator"): # Amazon Titan Image Generator G1
            quality = kwargs.get('quality', 'standard') 
            number_of_images = kwargs.get('number_of_images', 1) 
            cfg_scale_titan = kwargs.get('cfg_scale_titan', 8.0)
            
            body = json.dumps(
                {
                    "textToImageParams": {
                        "text": prompt
                    },
                    "taskType": "TEXT_IMAGE",
                    "imageGenerationConfig": {
                        "numberOfImages": number_of_images,
                        "quality": quality,
                        "height": kwargs.get('height', 1024), 
                        "width": kwargs.get('width', 1024),
                        "cfgScale": cfg_scale_titan,
                        "seed": kwargs.get('seed', 0) 
                    }
                }
            )
        else:
            logger.error(f"지원하지 않는 이미지 모델 ID 형식: {model_id}")
            raise RuntimeError(f"지원하지 않는 이미지 모델 ID 형식: {model_id}")


        try:
            response = bedrock_runtime.invoke_model( 
                body=body,
                modelId=model_id,
                accept="application/json",
                contentType="application/json"
            )
            
            response_body = json.loads(response.get("body").read())
            
            # #### START MODIFICATION ####
            # 모델 유형에 따른 응답 파싱 로직 수정
            if model_id.startswith("stability.stable-image-core"): # Stable Image Core 모델 응답 파싱
                # Stable Image Core는 'images' 키 아래에 Base64 인코딩된 이미지 리스트를 반환합니다.
                if 'images' in response_body and len(response_body['images']) > 0:
                    image_b64 = response_body['images'][0]
                    image_bytes = base64.b64decode(image_b64)
                    return image_bytes
                else:
                    logger.warning(f"Stable Image Core 모델 응답 본문에서 이미지 데이터를 찾을 수 없습니다: {response_body}")
                    return None
            elif model_id.startswith("stability."): # 다른 Stability AI Stable Diffusion 계열 모델 (SDXL 등)
                # 이전에 사용하던 'artifacts' 키를 사용하는 모델 (SDXL 등)
                if 'artifacts' in response_body and len(response_body['artifacts']) > 0:
                    image_b64 = response_body['artifacts'][0]['base64']
                    image_bytes = base64.b64decode(image_b64)
                    return image_bytes
                else:
                    logger.warning(f"다른 Stability AI 모델 응답 본문에서 이미지 데이터를 찾을 수 없습니다: {response_body}")
                    return None
            elif model_id.startswith("amazon.titan-image-generator"): # Titan Image Generator 응답 파싱
                if 'images' in response_body and len(response_body['images']) > 0:
                    image_b64 = response_body['images'][0]
                    image_bytes = base64.b64decode(image_b64)
                    return image_bytes
                else:
                    logger.warning(f"Titan Image Generator 응답 본문에서 이미지 데이터를 찾을 수 없습니다: {response_body}")
                    return None
            else:
                # 지원하지 않는 모델 ID 형식은 이미 위에서 RuntimeError를 발생시켰을 것입니다.
                # 여기에 도달했다면 예상치 못한 상황이므로 None을 반환합니다.
                return None 
            # #### END MODIFICATION ####

        except Exception as e:
            logger.error(f"이미지 모델 호출 중 오류 발생: {e}", exc_info=True)
            raise RuntimeError(f"이미지 생성 중 LLM 호출 오류 발생: {e}")