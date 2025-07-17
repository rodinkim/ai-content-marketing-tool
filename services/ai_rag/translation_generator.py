# ai-content-marketing-tool/services/ai_rag/translation_generator.py

import logging
from .prompt_manager import PromptManager
from .llm_invoker import BedrockClaudeProvider
from flask import current_app

logger = logging.getLogger(__name__)


class TranslationGenerator:
    def __init__(self, prompt_manager: PromptManager, text_provider: BedrockClaudeProvider):
        """
        TranslationGenerator를 초기화합니다.
        - prompt_manager: 프롬프트 구성을 위한 PromptManager 인스턴스
        - text_provider: 번역을 수행할 LLM 프로바이더 인스턴스
        """
        self.prompt_manager = prompt_manager
        self.text_provider = text_provider
        logger.info("TranslationGenerator 인스턴스가 성공적으로 초기화되었습니다.")

    def translate_for_image_prompt(self, **kwargs):
        """
        한국어 사용자 입력을 바탕으로, 이미지 생성에 최적화된 영어 프롬프트를 반환합니다.
        """
        korean_topic = kwargs.get('topic')
        if not korean_topic:
            raise ValueError("번역할 주제(topic)가 없습니다.")

        translation_kwargs = {
            'korean_topic': korean_topic,
            'brand_style_tone': kwargs.get('brand_style_tone', ''),
            'product_category': kwargs.get('product_category', ''),
            'target_audience': kwargs.get('target_audience', ''),
            'ad_purpose': kwargs.get('ad_purpose', ''),
            'key_points': kwargs.get('key_points', ''),
            'other_requirements': kwargs.get('other_requirements', ''),
        }
        translation_prompt = self.prompt_manager.generate_translate_prompt(
            **translation_kwargs
        )

        text_model_id = current_app.config.get('CLAUDE_MODEL_ID')
        translated_output = self.text_provider.invoke(
            prompt=translation_prompt,
            model_id=text_model_id
        ).strip()

        if not translated_output:
            raise ValueError("번역 결과가 비어있습니다.")
        logger.info(f"Translated '{korean_topic}' to English prompt: {translated_output}")
        return {"image_prompt": translated_output}
    
_translation_generator_instance = None

def init_translation_generator(prompt_manager, text_provider):
    """TranslationGenerator 인스턴스를 초기화합니다."""
    global _translation_generator_instance
    if _translation_generator_instance is None:
        _translation_generator_instance = TranslationGenerator(prompt_manager, text_provider)
    logger.info("TranslationGenerator service initialized.")
    return _translation_generator_instance

def get_translation_generator():
    """초기화된 TranslationGenerator 인스턴스를 반환합니다."""
    if _translation_generator_instance is None:
        logger.warning("TranslationGenerator is not initialized.")
    return _translation_generator_instance