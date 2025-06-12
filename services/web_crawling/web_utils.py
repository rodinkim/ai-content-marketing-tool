# ai-content-marketing-tool/services/web_crawling/web_utils.py

import re
import chardet # chardet은 decode_html_content 함수에서 사용
import logging

logger = logging.getLogger(__name__)

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

def decode_html_content(content: bytes, url: str) -> str:
    """
    주어진 바이트 콘텐츠의 인코딩을 감지하여 문자열로 디코딩합니다.
    감지 실패 시 여러 한국어 인코딩을 시도합니다.
    """
    detected_encoding = chardet.detect(content)['encoding']
    logger.info(f"Detected encoding for {url} by chardet: {detected_encoding}")

    if detected_encoding:
        try:
            return content.decode(detected_encoding, errors='replace')
        except (UnicodeDecodeError, LookupError):
            logger.warning(f"Failed to decode with {detected_encoding}. Trying common Korean encodings for {url}.")
    
    for encoding in ['euc-kr', 'cp949', 'utf-8']:
        try:
            return content.decode(encoding, errors='replace')
        except UnicodeDecodeError:
            continue
    
    logger.error(f"Failed to decode content for {url} with all common encodings.")
    return content.decode('utf-8', errors='replace') # 최후의 수단으로 utf-8 강제 시도

def clean_beautynury_title(title: str) -> str:
    """뷰티누리 기사 제목에서 불필요한 접두사/접미사를 제거합니다."""
    # '뷰티누리 - 화장품신문 (Beautynury.com) :: ' 접두사와 '| 뷰티누리', '| Beautynury' 접미사 제거
    cleaned_title = re.sub(r'뷰티누리\s*-\s*화장품신문\s*\(Beautynury\.com\)\s*::\s*', '', title).strip()
    cleaned_title = re.sub(r'\s*\|\s*뷰티누리|\s*\|\s*Beautynury', '', cleaned_title).strip()
    return cleaned_title