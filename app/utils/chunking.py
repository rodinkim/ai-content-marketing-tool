def simple_chunk_text(text, max_chunk_size=1000):
    """
    텍스트를 약 max_chunk_size 길이로 청킹.
    문단 단위로 자르되, 너무 짧은 경우 인접 문단과 병합
    """
    import re

    paragraphs = re.split(r'\n{2,}', text.strip())  # 2줄 이상 줄바꿈 기준
    chunks = []
    current_chunk = ""

    for para in paragraphs:
        if len(current_chunk) + len(para) < max_chunk_size:
            current_chunk += para + "\n\n"
        else:
            chunks.append(current_chunk.strip())
            current_chunk = para + "\n\n"

    if current_chunk.strip():
        chunks.append(current_chunk.strip())

    return chunks
