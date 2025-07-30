from extensions import db
from models import Content
from typing import List, Dict

def create_text_content(user_id: int, generated_text: str, data: Dict) -> Content:
    """
    텍스트 콘텐츠를 DB에 저장하고 Content 인스턴스를 반환합니다.
    """
    new_content = Content(
        user_id=user_id,
        generated_text=generated_text,
        topic=data.get('topic'),
        industry=data.get('industry'),
        content_type=data.get('content_type'),
        target_audience=data.get('target_audience'),
        key_points=data.get('key_points'),
        landing_page_url=data.get('landing_page_url'),
        tone=data.get('tone'),
        length_option=data.get('length_option'),
        seo_keywords=data.get('seo_keywords'),
        blog_style=data.get('blog_style'),
        email_subject=data.get('email_subject'),
        email_type=data.get('email_type'),
        brand_style_tone=data.get('brand_style_tone'),
        product_category=data.get('product_category'),
        ad_purpose=data.get('ad_purpose')
    )
    db.session.add(new_content)
    db.session.commit()
    return new_content

def create_image_content(user_id: int, image_urls: List[str], data: Dict) -> Content:
    """
    이미지 콘텐츠를 DB에 저장하고 Content 인스턴스를 반환합니다.
    """
    new_content = Content(
        user_id=user_id,
        content_type=data.get('content_type'),
        generated_image_url=", ".join(image_urls),
        topic=data.get('topic'),
        industry=data.get('industry'),
        target_audience=data.get('target_audience'),
        brand_style_tone=data.get('brand_style_tone'),
        product_category=data.get('product_category'),
        ad_purpose=data.get('ad_purpose'),
        key_points=data.get('key_points'),
        cut_count=data.get('cut_count'),
        aspect_ratio_sns=data.get('aspect_ratio_sns'),
        other_requirements=data.get('other_requirements')
    )
    db.session.add(new_content)
    db.session.commit()
    return new_content 