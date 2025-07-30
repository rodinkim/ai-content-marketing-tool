# ai-content-marketing-tool/services/generation/image_generator.py

import logging
import boto3
import base64
import uuid
import os
import json
from dataclasses import dataclass
from typing import List

from ..utils.prompt_manager import PromptManager
from services.utils.constants import IMAGE_SAVE_PATH

logger = logging.getLogger(__name__)

class ImageGenerationError(Exception):
    """이미지 생성 관련 예외"""
    pass

@dataclass
class ImageGenerationInput:
    """이미지 생성에 필요한 입력값 데이터 클래스"""
    topic: str
    cut_count: int = 1

class ImageGenerator:
    """이미지 생성 및 저장을 담당하는 클래스"""
    def __init__(self, prompt_manager: PromptManager, image_bedrock_client, s3_client, image_model_id: str):
        self.prompt_manager = prompt_manager
        self.bedrock_client = image_bedrock_client
        self.s3_client = s3_client
        self.image_model_id = image_model_id
        logger.info("ImageGenerator 인스턴스가 성공적으로 초기화되었습니다.")

    def create_image(self, image_input: ImageGenerationInput) -> List[str]:
        """
        입력값을 받아 이미지를 생성하고 파일로 저장한 뒤, 이미지 URL 리스트를 반환합니다.
        """
        image_prompt = image_input.topic
        num_images = image_input.cut_count
        request_body = {"prompt": image_prompt}
        image_urls: List[str] = []
        try:
            for _ in range(num_images):
                # Bedrock 모델을 호출하여 이미지 생성
                response = self.bedrock_client.invoke_model(
                    body=json.dumps(request_body),
                    modelId=self.image_model_id,
                    accept="application/json",
                    contentType="application/json"
                )
                response_body = json.loads(response.get("body").read())
                images_list = response_body.get("images")
                if not images_list:
                    logger.warning("이미지 생성 응답에 images 리스트가 없습니다.")
                    continue
                base64_image_data = images_list[0]
                image_bytes = base64.b64decode(base64_image_data)
                # 생성된 이미지를 파일로 저장
                image_url = self._save_image_to_file(image_bytes)
                image_urls.append(image_url)
            if not image_urls:
                logger.error("이미지 생성 결과가 비어 있습니다.")
                raise ImageGenerationError("이미지 생성 결과가 비어 있습니다.")
            return image_urls
        except Exception as e:
            logger.error(f"이미지 생성 중 예외 발생: {e}", exc_info=True)
            raise ImageGenerationError(f"이미지 생성 중 예외 발생: {e}")

    def _save_image_to_file(self, image_bytes: bytes) -> str:
        """
        생성된 이미지를 파일로 저장하고, 접근 가능한 URL을 반환합니다.
        """
        image_filename = f"sns_image_{uuid.uuid4().hex}.png"
        save_dir = os.path.join(IMAGE_SAVE_PATH)
        os.makedirs(save_dir, exist_ok=True)
        output_path = os.path.join(save_dir, image_filename)
        with open(output_path, 'wb') as f:
            f.write(image_bytes)
        logger.info(f"Image saved to {output_path}")
        # 프론트엔드에서 접근 가능한 URL 반환
        image_url = f"/content/{IMAGE_SAVE_PATH}/{image_filename}"
        return image_url


def create_image_generator(prompt_manager: PromptManager, image_bedrock_client: boto3.client, s3_client: boto3.client, image_model_id: str) -> ImageGenerator:
    """
    ImageGenerator 인스턴스를 생성합니다.
    """
    return ImageGenerator(prompt_manager, image_bedrock_client, s3_client, image_model_id)