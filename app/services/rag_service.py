def perform_rag_search(query, industry=None):
    # OpenSearch 연동 전: 모의 데이터 반환
    return {
        'query': query,
        'industry': industry,
        'results': [
            {
                'score': 0.91,
                'content': f'이 문서는 [{industry}] 업종에서 "{query}"와 관련된 마케팅 트렌드를 설명합니다.'
            }
        ]
    }
