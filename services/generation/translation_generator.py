# ai-content-marketing-tool/services/ai_rag/translation_generator.py

import logging
from dataclasses import dataclass
from typing import Optional, Dict, Any
from ..utils.prompt_manager import PromptManager
from ..utils.llm_invoker import BedrockClaudeProvider
from services.utils.constants import (
    DEFAULT_LLM_MAX_TOKENS,
    DEFAULT_LLM_TEMPERATURE,
    DEFAULT_LLM_TOP_P
)

logger = logging.getLogger(__name__)

class TranslationPromptError(Exception):
    """번역 프롬프트 생성/실행 관련 예외"""
    pass

@dataclass
class TranslationPromptInput:
    """번역 프롬프트에 필요한 입력값 데이터 클래스"""
    topic: str
    brand_style_tone: Optional[str] = ""
    product_category: Optional[str] = ""
    target_audience: Optional[str] = ""
    ad_purpose: Optional[str] = ""
    key_points: Optional[str] = ""
    other_requirements: Optional[str] = ""

class TranslationGenerator:
    """이미지 프롬프트용 영어 번역 생성기"""
    def __init__(self, prompt_manager: PromptManager, text_provider: BedrockClaudeProvider):
        self.prompt_manager = prompt_manager
        self.text_provider = text_provider
        logger.info("TranslationGenerator 인스턴스가 성공적으로 초기화되었습니다.")

    def translate_for_image_prompt(self, prompt_input: TranslationPromptInput) -> Dict[str, Any]:
        """
        입력값을 받아 영어 이미지 프롬프트로 번역합니다.
        """
        if not prompt_input.topic:
            raise TranslationPromptError("번역할 주제(topic)가 없습니다.")

        translation_kwargs = {
            'topic': prompt_input.topic,
            'brand_style_tone': prompt_input.brand_style_tone,
            'product_category': prompt_input.product_category,
            'target_audience': prompt_input.target_audience,
            'ad_purpose': prompt_input.ad_purpose,
            'key_points': prompt_input.key_points,
            'other_requirements': prompt_input.other_requirements,
        }
        # 프롬프트 템플릿 생성
        translation_prompt = self.prompt_manager.generate_translate_prompt(
            **translation_kwargs
        )

        try:
            # LLM 호출로 번역 수행
            translated_output = self.text_provider.invoke(
                prompt=translation_prompt,
                max_tokens=DEFAULT_LLM_MAX_TOKENS,
                temperature=DEFAULT_LLM_TEMPERATURE,
                top_p=DEFAULT_LLM_TOP_P
            ).strip()
        except Exception as e:
            logger.error(f"LLM 번역 호출 실패: {e}", exc_info=True)
            raise TranslationPromptError(f"LLM 번역 호출 실패: {e}")

        if not translated_output:
            raise TranslationPromptError("번역 결과가 비어있습니다.")
        logger.info(f"Translated '{prompt_input.topic}' to English prompt: {translated_output}")
        return {"image_prompt": translated_output}


def create_translation_generator(prompt_manager: PromptManager, text_provider: BedrockClaudeProvider, translate_model_id: Optional[str] = None) -> TranslationGenerator:
    """
    TranslationGenerator 인스턴스를 생성합니다.
    """
    return TranslationGenerator(prompt_manager, text_provider)