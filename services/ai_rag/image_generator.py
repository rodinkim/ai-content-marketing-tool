# ai-content-marketing-tool/services/ai_rag/image_generator.py

import logging
import boto3
import base64
import uuid
import os
import json

from .prompt_manager import PromptManager
from config import config
from flask import current_app

logger = logging.getLogger(__name__)


class ImageGenerator:
    def __init__(self, prompt_manager: PromptManager, image_bedrock_client: boto3.client, s3_client: boto3.client):
        """
        ImageGenerator를 초기화합니다.
        - prompt_manager: 프롬프트를 생성하기 위한 PromptManager 인스턴스
        - image_bedrock_client: 이미지 생성을 위한 Bedrock 클라이언트 (us-west-2 리전)
        - s3_client: 이미지를 S3에 업로드하기 위한 클라이언트 (선택적 확장)
        """
        self.prompt_manager = prompt_manager
        self.bedrock_client = image_bedrock_client
        self.s3_client = s3_client
        logger.info("ImageGenerator 인스턴스가 성공적으로 초기화되었습니다.")


    def create_image(self, **kwargs) -> list[str]:
        """
        주어진 사용자 입력을 바탕으로 이미지를 생성하고 URL 목록을 반환합니다.
        """
        # 번역 프롬프트에서 온 완성된 영어 문장만 사용
        image_prompt = kwargs.get('topic', '')
        num_images = int(kwargs.get('cut_count', 1))
        request_body = {
            "prompt": image_prompt
        }

        image_urls = []
        try:
            for i in range(num_images):
                response = self.bedrock_client.invoke_model(
                    body=json.dumps(request_body),
                    modelId=config.IMAGE_GENERATION_MODEL_ID,
                    accept="application/json",
                    contentType="application/json"
                )
                
                response_body = json.loads(response.get("body").read())
                images_list = response_body.get("images")

                if not images_list:
                    continue

                base64_image_data = images_list[0]
                image_bytes = base64.b64decode(base64_image_data)
                image_url = self._save_image_to_file(image_bytes)
                image_urls.append(image_url)

            return image_urls

        except Exception as e:
            logger.error(f"이미지 생성 중 오류 발생: {e}", exc_info=True)
            return []

    def _save_image_to_file(self, image_bytes: bytes) -> str:
        """이미지 데이터를 서버에 파일로 저장하고 접근 가능한 URL을 반환합니다."""
        
        # 고유한 파일 이름 생성
        image_filename = f"sns_image_{uuid.uuid4().hex}.png"
        
        # 저장 경로 설정
        save_dir = os.path.join(current_app.root_path, config.IMAGE_SAVE_PATH)
        os.makedirs(save_dir, exist_ok=True)
        
        output_path = os.path.join(save_dir, image_filename)
        
        # 파일로 저장
        with open(output_path, 'wb') as f:
            f.write(image_bytes)
        logger.info(f"Image saved to {output_path}")

        # 웹에서 접근 가능한 URL 반환
        image_url = f"/content/{config.IMAGE_SAVE_PATH}/{image_filename}"
        return image_url

_image_generator_instance = None

def init_image_generator(app, prompt_manager, image_bedrock_client, s3_client):
    """ImageGenerator 인스턴스를 초기화하고 앱 확장에 등록합니다."""
    global _image_generator_instance
    if _image_generator_instance is None:
        _image_generator_instance = ImageGenerator(prompt_manager, image_bedrock_client, s3_client)
    logger.info("ImageGenerator service initialized.")
    return _image_generator_instance

def get_image_generator():
    """초기화된 ImageGenerator 인스턴스를 반환합니다."""
    if _image_generator_instance is None:
        logger.warning("ImageGenerator is not initialized.")
    return _image_generator_instance