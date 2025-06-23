# ai-content-marketing-tool/services/web_crawling/web_utils.py

import re
import chardet 
import logging
import hashlib

logger = logging.getLogger(__name__)

def sanitize_filename(title: str, url: str, max_length=150) -> str: # max_length를 더 길게 설정 (URL 해시 포함)
    """
    기사 제목과 URL 해시를 기반으로 안전하고 유니크한 파일명을 생성합니다.
    파일명은 '정화된_제목_URLHASH.txt' 형식이 됩니다.
    """
    # 1. 제목 정화
    # 특수문자 제거 및 공백을 언더스코어로 변경
    # 한글, 영문, 숫자, 하이픈(-) 외에는 제거 (파일명에 적합하도록)
    sanitized_title = re.sub(r'[^a-zA-Z0-9가-힣\s-]', '', title).replace(' ', '_').strip()
    
    # 2. URL 해시 생성 (MD5 해시의 앞 8자리를 사용)
    # URL이 동일하면 해시도 동일하므로 유니크한 식별자로 사용될 수 있습니다.
    url_hash = hashlib.md5(url.encode('utf-8')).hexdigest()[:8]

    # 3. 최종 파일명 베이스 구성
    if not sanitized_title: # 제목이 없을 경우 URL 해시만으로 구성
        final_base = f"untitled_article_{url_hash}"
        logger.warning(f"제목 없이 파일명 생성: {url} -> {final_base}") # 로그 기록
    else:
        # 제목이 너무 길 경우 적절히 자르고 해시를 붙입니다.
        # 총 길이 max_length에서 해시와 확장자 길이 등을 뺀 길이만큼 제목을 자릅니다.
        # 해시길이(8) + 언더스코어(1) + .txt(4) = 13자
        title_part_max_len = max_length - 13
        if len(sanitized_title) > title_part_max_len:
            sanitized_title = sanitized_title[:title_part_max_len].rstrip('_') # 자를 때 언더스코어 제거
        
        final_base = f"{sanitized_title}_{url_hash}"

    # 최종 파일명 길이 제한 (OS 및 S3 키 제한을 고려)
    # S3 키는 최대 1024자이지만, 파일 시스템 호환성을 위해 255자 이내로 보통 권장.
    # 여기서는 max_length를 150으로 설정했으므로 이보다 짧게 나옵니다.
    filename = final_base[:max_length].strip('_')
    
    # 혹시 모든 문자가 제거되어 파일명이 비어지는 경우를 대비 (매우 드뭄)
    if not filename:
        filename = f"generic_article_{url_hash}"

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