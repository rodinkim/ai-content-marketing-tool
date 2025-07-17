# ai-content-marketing-tool/services/ai_rag/content_creation_service.py

import os
import uuid
import logging
from flask import current_app
from .llm_invoker import BedrockClaudeProvider, BedrockImageGeneratorProvider
from .prompt_manager import PromptManager

logger = logging.getLogger(__name__)

class ContentCreationService:
    """콘텐츠 생성(번역, 이미지 생성, 파일 저장) 관련 비즈니스 로직을 담당합니다."""

    def __init__(self, prompt_manager: PromptManager):
        self.prompt_manager = prompt_manager
        self.bedrock_runtime_client = None
        self.text_generator = None
        self.image_generator = None

    def _initialize_clients(self):
        """필요한 Bedrock 클라이언트와 Provider를 초기화합니다."""
        if self.bedrock_runtime_client is None:
            self.bedrock_runtime_client = current_app.extensions.get('rag_bedrock_runtime')
            if not self.bedrock_runtime_client:
                raise RuntimeError("Bedrock client is not initialized.")
        
        if self.text_generator is None:
            self.text_generator = BedrockClaudeProvider(self.bedrock_runtime_client)
        
        if self.image_generator is None:
            self.image_generator = BedrockImageGeneratorProvider(self.bedrock_runtime_client)

    def _translate_topic_to_english_prompt(self, **kwargs) -> str:
        """LLM을 사용하여 한국어 주제와 상세 문맥을 영어 이미지 프롬프트로 번역합니다."""
        self._initialize_clients()
        
        korean_topic = kwargs.get('topic')
        if not korean_topic:
            raise ValueError("Korean topic for translation is missing.")

        # --- [수정] 충돌을 피하기 위해 kwargs에서 기존 content_type 제거 ---
        # **kwargs의 복사본을 만들어 작업합니다.
        translation_kwargs = kwargs.copy()
        translation_kwargs.pop('content_type', None) # 'content_type' 키를 안전하게 제거
        
        # PromptManager에는 하드코딩된 'translate_to_english'와 정리된 인자만 전달합니다.
        translation_prompt_template = self.prompt_manager.generate_final_prompt(
            content_type='translate_to_english',
            **translation_kwargs # 'content_type'이 제거된 kwargs를 전달
        )
        # --- 수정 끝 ---
        
        text_model_id = current_app.config.get('BEDROCK_CLAUDE_SONNET_MODEL_ID')
        
        translated_prompt = self.text_generator.invoke(
            prompt=translation_prompt_template,
            model_id=text_model_id
        ).strip()
        
        if not translated_prompt:
            raise ValueError("Translation resulted in an empty prompt.")
            
        logger.info(f"Translated '{korean_topic}' to: {translated_prompt}")
        return translated_prompt

    def _generate_and_save_image(self, prompt: str, **kwargs) -> str:
        """영어로 번역된 프롬프트를 사용해 이미지를 생성하고 저장한 뒤, URL을 반환합니다."""
        self._initialize_clients()
        
        image_model_id = current_app.config.get('IMAGE_GENERATION_MODEL_ID')
        
        image_bytes = self.image_generator.invoke(
            prompt=prompt,
            model_id=image_model_id,
            **kwargs 
        )
        
        if not image_bytes:
            raise RuntimeError("Image generation failed, no image data returned.")

        image_filename = f"sns_image_{uuid.uuid4().hex}.png"
        save_dir = os.path.join(current_app.root_path, current_app.config.get('IMAGE_SAVE_PATH', 'generated_images'))
        
        os.makedirs(save_dir, exist_ok=True)
        output_path = os.path.join(save_dir, image_filename)
        
        with open(output_path, 'wb') as f:
            f.write(image_bytes)
        logger.info(f"Image saved to {output_path}")

        image_url = f"/content/{current_app.config.get('IMAGE_SAVE_PATH', 'generated_images')}/{image_filename}"
        return image_url

    def create_sns_image_from_topic(self, **kwargs) -> dict:
        """
        한국어 주제와 선택적 인자들을 받아 번역, 이미지 생성, 저장을 모두 처리하는 메인 함수입니다.
        """
        try:
            english_prompt = self._translate_topic_to_english_prompt(**kwargs)
            image_url = self._generate_and_save_image(english_prompt, **kwargs)
            
            return {
                "status": "success",
                "prompt_used": english_prompt,
                "image_url": image_url
            }
        except Exception as e:
            logger.error(f"SNS image creation process failed: {e}", exc_info=True)
            raise