import chardet
import logging

logger = logging.getLogger(__name__)

class HTMLDecoder:
    """
    HTTP 응답 본문(바이트)을 적절한 인코딩으로 디코딩하는 유틸리티 클래스입니다.
    여러 인코딩 방식을 시도하여 최적의 결과를 찾습니다.
    """
    
    @staticmethod
    def decode_html_content(
        content_bytes: bytes, 
        initial_encoding_hint: str = None,
        apparent_encoding: str = None,
        url: str = None
    ) -> str | None:
        """
        주어진 바이트 콘텐츠를 여러 인코딩 방식을 시도하여 HTML 문자열로 디코딩합니다.
        Args:
            content_bytes: 디코딩할 바이트 콘텐츠.
            initial_encoding_hint: HTTP 헤더 등에서 추정된 인코딩 힌트.
            apparent_encoding: requests.response.apparent_encoding 등 콘텐츠 기반 추론값.
            url: 디코딩 실패 시 로깅을 위한 원본 URL.
        Returns:
            디코딩된 HTML 문자열 또는 실패 시 None.
        """
        decoding_attempts = []
        # 1. 초기 인코딩 힌트 (HTTP 헤더, 사용자 강제 등)
        if initial_encoding_hint:
            decoding_attempts.append((initial_encoding_hint, 'initial_hint'))
        # 2. requests의 apparent_encoding (중복 방지)
        if apparent_encoding and apparent_encoding.lower() != (initial_encoding_hint or '').lower():
            decoding_attempts.append((apparent_encoding, 'apparent_encoding'))
        # 3. chardet (바이트 분석)
        detected_by_chardet = chardet.detect(content_bytes)['encoding']
        if detected_by_chardet and detected_by_chardet.lower() not in [enc.lower() for enc, _ in decoding_attempts]:
            decoding_attempts.append((detected_by_chardet, 'chardet'))
        # 4. 일반적인 폴백 인코딩 (UTF-8, EUC-KR, CP949)
        for enc in ['utf-8', 'euc-kr', 'cp949']:
            if enc.lower() not in [enc_try.lower() for enc_try, _ in decoding_attempts]:
                decoding_attempts.append((enc, 'fallback'))
        html_content = None
        final_encoding_used = None
        for encoding_name, source in decoding_attempts:
            if not encoding_name:
                continue
            try:
                decoded_content = content_bytes.decode(encoding_name, errors='replace')
                # 유니코드 대체 문자('')가 없으면 바로 성공 반환
                if '' not in decoded_content:
                    logger.debug(f"Successfully decoded with {encoding_name} (Source: {source}).")
                    html_content = decoded_content
                    final_encoding_used = encoding_name
                    break 
                else:
                    # 대체 문자가 있지만, 아직 더 나은 결과가 없다면 임시 저장
                    if html_content is None:
                        html_content = decoded_content
                        final_encoding_used = encoding_name
            except (UnicodeDecodeError, LookupError):
                logger.debug(f"Decoding with {encoding_name} (Source: {source}) failed. Trying next.")
        # 모든 시도 후 최적의 결과 반환 및 로깅
        if html_content is None or ('' in (html_content or '') and len(html_content) < 500):
            # 내용이 없거나 짧고 깨진 경우 실패로 간주
            logger.error(f"Failed to decode HTML content for '{url if url else 'N/A'}' after all attempts. Returning None.")
            return None
        elif '' in html_content:
            # 대체 문자가 남아있는 경우 경고
            logger.warning(f"Decoded content for '{url if url else 'N/A'}' still contains some replacement characters. (Final encoding attempted: {final_encoding_used})")
        return html_content