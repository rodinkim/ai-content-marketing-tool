import os
import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)

class PromptManager:
    """
    프롬프트 템플릿을 관리하고, 입력값에 맞는 프롬프트를 동적으로 생성합니다.
    """
    def __init__(self, app_root_path: str, templates_dir_relative_path: str):
        self.templates_dir = os.path.join(app_root_path, templates_dir_relative_path)
        self.templates = self._load_all_templates()

    def _load_all_templates(self) -> Dict[str, str]:
        """
        템플릿 디렉토리에서 모든 .md 프롬프트 파일을 로드합니다.
        """
        templates = {}
        for filename in os.listdir(self.templates_dir):
            if filename.endswith(".md"):
                template_key = os.path.splitext(filename)[0]
                file_path = os.path.join(self.templates_dir, filename)
                with open(file_path, 'r', encoding='utf-8') as f:
                    templates[template_key] = f.read()
                logger.info(f"Loaded prompt template: {template_key} from {filename}")
        if not templates:
            raise FileNotFoundError("No prompt templates (.md) found in the directory.")
        return templates

    def get_template_key(self, content_type: str, blog_style: str = None, email_type: str = None) -> str:
        """
        입력값에 따라 사용할 템플릿 키를 결정합니다.
        """
        if content_type == "blog":
            if blog_style == "추천/리스트 글":
                return "blog_list"
            elif blog_style == "리뷰/후기 글":
                return "blog_review"
            else:
                return "blog_list"
        elif content_type == "email":
            if email_type == "newsletter":
                return "email_newsletter"
            elif email_type == "promotion":
                return "email_promotion"
            else:
                return "email_newsletter"
        else:
            return content_type

    def generate_text_prompt(
        self,
        content_type: str,
        topic: str,
        industry: str,
        context: str = None,
        target_audience: str = None,
        key_points: str = None,
        blog_style: str = None,
        tone: str = None,
        length: str = None,
        seo_keywords: str = None,
        email_subject: str = None,
        email_type: str = None,
        landing_page_url: str = None,
        brand_style_tone: str = None,
        product_category: str = None,
        ad_purpose: str = None,
        **kwargs
    ) -> str:
        """
        텍스트 콘텐츠(블로그, 이메일) 생성을 위한 최종 프롬프트를 생성합니다.
        """
        template_key = self.get_template_key(content_type, blog_style, email_type)
        if template_key not in self.templates:
            raise ValueError(f"'{template_key}'에 해당하는 프롬프트 템플릿(.md) 파일을 찾을 수 없습니다.")
        selected_template = self.templates[template_key]

        # 길이 옵션에 따른 안내문 생성
        length_instruction_text = ""
        if length == "short":
            length_instruction_text = "콘텐츠 길이는 짧게(약 500-1000자) 작성하십시오."
        elif length == "medium":
            length_instruction_text = "콘텐츠 길이는 중간(약 1000-2000자)으로 작성하십시오."
        elif length == "long":
            length_instruction_text = "콘텐츠 길이는 길게(약 2000-4000자) 작성하십시오."

        all_vars = {
            "topic": topic,
            "industry": industry,
            "context": context,
            "content_type": content_type,
            "blog_style": blog_style,
            "email_subject": email_subject,
            "email_type": email_type,
            "landing_page_url": landing_page_url or "",
            "length_instruction": length_instruction_text,
            "target_audience": target_audience or "",
            "key_points": key_points or "",
            "tone": tone or "",
            "seo_keywords": seo_keywords or "",
            "brand_style_tone": brand_style_tone or "",
            "product_category": product_category or "",
            "ad_purpose": ad_purpose or "",
        }
        final_prompt = selected_template.format(**all_vars)
        logger.info(f"Text-based LLM Prompt for '{topic}' ({content_type}) generated.")
        return final_prompt

    def generate_translate_prompt(
        self,
        topic: str,
        brand_style_tone: str = "",
        product_category: str = "",
        target_audience: str = "",
        ad_purpose: str = "",
        key_points: str = "",
        other_requirements: str = "",
        ad_slogan: str = "",
        cut_count: str = "",
        aspect_ratio_sns: str = "",
        **kwargs
    ) -> str:
        """
        번역 프롬프트를 생성합니다.
        """
        template_key = "translate_to_english"
        if template_key not in self.templates:
            raise ValueError(f"'{template_key}'에 해당하는 프롬프트 템플릿(.md) 파일을 찾을 수 없습니다.")
        selected_template = self.templates[template_key]
        prompt_parts = {
            "topic": topic,
            "brand_style_tone": brand_style_tone or "",
            "product_category": product_category or "",
            "target_audience": target_audience or "",
            "ad_purpose": ad_purpose or "",
            "key_points": key_points or "",
            "other_requirements": other_requirements or "",
            "ad_slogan": ad_slogan or "",
            "cut_count": cut_count or "",
            "aspect_ratio_sns": aspect_ratio_sns or "",
        }
        final_prompt = selected_template.format(**prompt_parts)
        logger.info(f"Translation LLM Prompt for '{topic}' generated.")
        return final_prompt