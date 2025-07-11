# ai-content-marketing-tool/services/ai_rag/prompt_manager.py

import os
import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)

class PromptManager:
    """여러 프롬프트 템플릿을 관리하고, 상황에 맞는 프롬프트를 동적으로 구성합니다."""

    def __init__(self, app_root_path: str, templates_dir_relative_path: str):
        # --- 수정: 여러 템플릿을 로드하여 딕셔너리에 저장 ---
        self.templates_dir = os.path.join(app_root_path, templates_dir_relative_path)
        self.templates = self._load_all_templates()

    def _load_all_templates(self) -> Dict[str, str]:
        """지정된 디렉토리에서 모든 .md 프롬프트 템플릿 파일을 로드합니다."""

        templates = {}
        try:
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
        except FileNotFoundError as e:
            logger.critical(f"Prompt templates directory not found or empty: {self.templates_dir}. {e}")
            raise
        except Exception as e:
            logger.critical(f"Error loading prompt templates: {e}")
            raise

    def generate_final_prompt(self, 
                              content_type: str,
                              blog_style: str = None, 
                              topic: str = None, 
                              industry: str = None, 
                              tone: str = None, 
                              length: str = None, 
                              context: str = None, 
                              seo_keywords: str = None,
                              email_subject: str = None,
                              target_audience: str = None,
                              email_type: str = None,
                              key_points: str = None,
                              landing_page_url: str = None,
                              **kwargs) -> str:
        """주어진 파라미터에 맞는 템플릿을 선택하고 최종 프롬프트를 구성합니다."""
        
        # content_type 자체가 바로 template_key가 됩니다.
        template_key = content_type

        # 해당 키의 템플릿이 로드되었는지 확인합니다.
        if template_key not in self.templates:
            # 에러 메시지를 더 명확하게 변경합니다.
            raise ValueError(f"'{template_key}'에 해당하는 프롬프트 템플릿(.md) 파일을 찾을 수 없습니다. templates 폴더에 파일이 있는지 확인하세요.")
        
        selected_template = self.templates[template_key]
        # --------------------------------

        # 기존의 instruction 생성 로직은 동일
        length_instruction_text = ""
        if length == "short":
            length_instruction_text = "콘텐츠 길이는 짧게(약 500-1000자) 작성하십시오."
        elif length == "medium":
            length_instruction_text = "콘텐츠 길이는 중간(약 1000-2000자)으로 작성하십시오."
        elif length == "long":
            length_instruction_text = "콘텐츠 길이는 길게(약 2000-4000자) 작성하십시오."

        seo_instruction_text = f"다음 키워드를 자연스럽게 포함: {seo_keywords}" if seo_keywords else "별도의 SEO 키워드 지시 없음."

        # .format()에 사용될 모든 변수를 담은 딕셔너리
        prompt_parts = {
            "topic": topic, "industry": industry, "content_type": content_type,
            "tone": tone, "context": context, "length_instruction": length_instruction_text,
            "seo_instruction": seo_instruction_text, "blog_style": blog_style,
            "email_subject": email_subject,
            "target_audience": target_audience,
            "email_type": email_type,
            "key_points": key_points,
            "landing_page_url": landing_page_url
        }
        # **kwargs를 통해 추가적인 변수도 전달 가능
        prompt_parts.update(kwargs)
        
        # .format()이 실패하지 않도록 없는 키는 빈 문자열로 대체
        final_prompt = selected_template.format_map({k: v for k, v in prompt_parts.items() if v is not None})
        
        if content_type == 'blog':
            log_detail = f"{content_type}, {blog_style}"
        elif content_type == 'email':
            log_detail = f"{content_type}, {email_type}"
        else:
            log_detail = content_type

        logger.info(f"LLM Prompt for '{topic}' ({log_detail}) generated.")
        return final_prompt