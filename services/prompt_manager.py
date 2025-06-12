# ai-content-marketing-tool/services/prompt_manager.py

import os
import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)

class PromptManager:
    """프롬프트 템플릿 로드 및 동적 프롬프트 구성 로직을 관리합니다."""

    def __init__(self, app_root_path: str, template_relative_path: str):
        self.prompt_template = self._load_prompt_template(app_root_path, template_relative_path)
        
    def _load_prompt_template(self, app_root_path: str, template_relative_path: str) -> str:
        """프롬프트 템플릿 파일을 로드합니다."""
        prompt_template_path = os.path.join(app_root_path, template_relative_path)
        try:
            with open(prompt_template_path, 'r', encoding='utf-8') as f:
                template = f.read()
            logger.info(f"Prompt template loaded from: {prompt_template_path}")
            return template
        except FileNotFoundError:
            logger.critical(f"Prompt template file not found: {prompt_template_path}. Exiting.")
            raise RuntimeError(f"Prompt template file not found at {prompt_template_path}")
        except Exception as e:
            logger.critical(f"Error loading prompt template: {e}. Exiting.")
            raise RuntimeError(f"Error loading prompt template: {e}")

    def generate_final_prompt(self, 
                              topic: str, 
                              industry: str, 
                              content_type: str, 
                              tone: str, 
                              length: str, 
                              context: str, 
                              seo_keywords: str = None, 
                              email_subject_input: str = None) -> str:
        """주어진 파라미터를 사용하여 최종 프롬프트를 구성합니다."""
        # length_instruction 값 생성
        length_instruction_text = ""
        if length == "short":
            length_instruction_text = "콘텐츠 길이는 짧게(약 500-1000자) 작성하십시오."
        elif length == "medium":
            length_instruction_text = "콘텐츠 길이는 중간(약 1000-2000자)으로 작성하십시오."
        elif length == "long":
            length_instruction_text = "콘텐츠 길이는 길게(약 2000-4000자) 작성하십시오."

        # seo_instruction 값 생성
        seo_instruction_text = f"다음 키워드를 자연스럽게 포함: {seo_keywords}" if seo_keywords else "별도의 SEO 키워드 지시 없음."

        # email_instruction 값 생성
        email_instruction_text = ""
        if content_type == "이메일 뉴스레터":
            if email_subject_input:
                email_instruction_text = f"다음 제목으로 이메일을 작성해주세요: '{email_subject_input}'"
            else:
                email_instruction_text = "적절한 이메일 제목을 2~3개 제안하고, 그중 하나를 본문에 사용해주세요."
        
        prompt_parts = {
            "topic": topic,
            "industry": industry,
            "content_type": content_type,
            "tone": tone,
            "context": context,
            "length_instruction": length_instruction_text,
            "seo_instruction": seo_instruction_text,
            "email_instruction": email_instruction_text
        }
        
        final_prompt = self.prompt_template.format(**prompt_parts)
        
        logger.info(f"LLM Prompt for '{topic}' ({content_type}, {industry}) generated.")
        return final_prompt