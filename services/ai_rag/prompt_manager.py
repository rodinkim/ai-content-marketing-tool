# ai-content-marketing-tool/services/ai_rag/prompt_manager.py

import os # Required for os.path.join
import logging
from typing import Dict, Any # Keeping these imports for potential future use or consistency

logger = logging.getLogger(__name__)

class PromptManager:
    """Manages prompt template loading and dynamic prompt construction logic."""

    def __init__(self, app_root_path: str, template_relative_path: str):
        self.prompt_template = self._load_prompt_template(app_root_path, template_relative_path)
        
    def _load_prompt_template(self, app_root_path: str, template_relative_path: str) -> str:
        """Loads the prompt template file."""
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
                              seo_keywords: str = None ) -> str:
        """Constructs the final prompt using the given parameters."""
        # Generate length_instruction_text
        length_instruction_text = ""
        if length == "short":
            length_instruction_text = "콘텐츠 길이는 짧게(약 500-1000자) 작성하십시오."
        elif length == "medium":
            length_instruction_text = "콘텐츠 길이는 중간(약 1000-2000자)으로 작성하십시오."
        elif length == "long":
            length_instruction_text = "콘텐츠 길이는 길게(약 2000-4000자) 작성하십시오."

        # Generate seo_instruction_text
        seo_instruction_text = f"다음 키워드를 자연스럽게 포함: {seo_keywords}" if seo_keywords else "별도의 SEO 키워드 지시 없음."

        prompt_parts = {
            "topic": topic,
            "industry": industry,
            "content_type": content_type,
            "tone": tone,
            "context": context,
            "length_instruction": length_instruction_text,
            "seo_instruction": seo_instruction_text
        }
        
        final_prompt = self.prompt_template.format(**prompt_parts)
        
        logger.info(f"LLM Prompt for '{topic}' ({content_type}, {industry}) generated.")
        return final_prompt