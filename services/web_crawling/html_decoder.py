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
        initial_encoding_hint: str = None, # response_encoding 대신 더 일반적인 힌트
        apparent_encoding: str = None,
        url: str = None # 로깅을 위해 URL 추가
    ) -> str | None:
        """
        주어진 바이트 콘텐츠를 여러 인코딩 방식을 시도하여 HTML 문자열로 디코딩합니다.
        
        Args:
            content_bytes: 디코딩할 바이트 콘텐츠.
            initial_encoding_hint: requests.response.encoding 또는 강제 인코딩과 같은 초기 인코딩 힌트.
            apparent_encoding: requests.response.apparent_encoding (콘텐츠 기반 추론).
            url: 디코딩 실패 시 로깅을 위한 원본 URL.
            
        Returns:
            디코딩된 HTML 문자열 또는 실패 시 None.
        """
        
        decoding_attempts = []

        # 1. 초기 인코딩 힌트 (HTTP 헤더, 사용자 강제 등)
        if initial_encoding_hint:
            decoding_attempts.append((initial_encoding_hint, 'initial_hint'))

        # 2. requests의 response.apparent_encoding (콘텐츠 기반 추론)
        #    초기 힌트와 중복되지 않는 경우에만 추가
        if apparent_encoding and apparent_encoding.lower() != (initial_encoding_hint or '').lower():
            decoding_attempts.append((apparent_encoding, 'apparent_encoding'))

        # 3. chardet (종합적인 바이트 분석)
        detected_by_chardet = chardet.detect(content_bytes)['encoding']
        # 이미 시도된 인코딩이 아니고 유효한 경우에만 추가
        if detected_by_chardet and detected_by_chardet.lower() not in [enc.lower() for enc, _ in decoding_attempts]:
            decoding_attempts.append((detected_by_chardet, 'chardet'))

        # 4. 일반적인 폴백 인코딩 (UTF-8 우선, 한국어 웹사이트에서 흔히 사용되는 것들)
        for enc in ['utf-8', 'euc-kr', 'cp949']:
            if enc.lower() not in [enc_try.lower() for enc_try, _ in decoding_attempts]:
                decoding_attempts.append((enc, 'fallback'))
        
        html_content = None
        final_encoding_used = None # 실제로 디코딩에 사용된 인코딩 저장
        
        for encoding_name, source in decoding_attempts:
            if not encoding_name: # None이거나 빈 문자열인 경우 건너뛰기
                continue
            try:
                decoded_content = content_bytes.decode(encoding_name, errors='replace')
                
                # 유니코드 대체 문자('�')가 없으면 최상으로 간주하고 바로 종료
                if '�' not in decoded_content:
                    logger.debug(f"Successfully decoded with {encoding_name} (Source: {source}).")
                    html_content = decoded_content
                    final_encoding_used = encoding_name
                    break 
                else:
                    # 대체 문자가 있지만, 아직 더 나은 결과가 없다면 현재 결과를 임시 저장
                    # (더 나은 결과: 대체 문자가 없거나 더 적은 경우)
                    if html_content is None: # 아직 성공한 디코딩이 없으면 일단 이걸 저장
                        html_content = decoded_content
                        final_encoding_used = encoding_name # 임시 저장된 인코딩
                    # logger.debug(f"Decoding with {encoding_name} (Source: {source}) still contains replacement characters. Trying next.")
            except (UnicodeDecodeError, LookupError):
                logger.debug(f"Decoding with {encoding_name} (Source: {source}) failed. Trying next.")
        
        # 모든 시도 후 최적의 결과 반환 및 로깅
        if html_content is None or ('�' in (html_content or '') and len(html_content) < 500):
            # 내용이 없거나 짧고 깨진 경우 실패로 간주
            logger.error(f"Failed to decode HTML content for '{url if url else 'N/A'}' after all attempts. Returning None.")
            return None
        elif '�' in html_content:
            # 대체 문자가 여전히 남아있는 경우 경고
            # final_encoding_used 변수를 사용하여 더 정확한 인코딩 정보 제공
            logger.warning(f"Decoded content for '{url if url else 'N/A'}' still contains some replacement characters. (Final encoding attempted: {final_encoding_used})")
        
        return html_content