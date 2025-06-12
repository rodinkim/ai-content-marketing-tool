# ai-content-marketing-tool/services/web_utils.py
import re

def sanitize_filename(title: str, url: str, max_length=50):
    """기사 제목을 기반으로 안전한 파일명을 생성하고, URL을 추가 정보로 사용합니다."""
    # 제목에서 특수문자 제거 및 공백을 언더스코어로 변경
    sanitized_title = re.sub(r'[^a-zA-Z0-9가-힣\s-]', '', title).replace(' ', '_')
    
    # 너무 짧은 제목이나 일반적이지 않은 제목일 경우 URL 기반 파일명도 고려
    if not sanitized_title or len(sanitized_title) < 5:
        # URL에서 도메인을 제거하고 경로를 기반으로 파일명 생성 (이전 동작 유지)
        filename_from_url = url.replace('https://', '').replace('http://', '')
        # 특수문자 제거 및 슬래시를 언더스코어로 변경
        final_base = re.sub(r'[^a-zA-Z0-9가-힣_\-]', '', filename_from_url.replace('/', '_'))
        # 마지막에 .txt 확장자가 중복될 수 있으므로, 이미 .txt로 끝나면 확장자 제거
        if final_base.endswith('.txt'):
            final_base = final_base[:-4]
        if not final_base:
            final_base = "untitled_article_from_url"
    else:
        final_base = sanitized_title

    # 길이 제한 적용
    filename = final_base[:max_length].strip('_')
    if not filename:
        filename = "untitled_article_from_url"
    return f"{filename}.txt"