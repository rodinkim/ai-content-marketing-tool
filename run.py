# ai-content-marketing-tool/run.py

from __init__ import create_app 
from services.app_core.app_factory_utils import initialize_full_app 

# 1. 앱 인스턴스 생성 (최소화된 팩토리 함수 호출)
app = create_app()

# 2. 앱의 나머지 모든 초기화 단계를 수행 (로깅, 설정, 클라이언트, RAG, 블루프린트, 스케줄러 등)
initialize_full_app(app) 

# 3. 개발 서버 실행
if __name__ == '__main__':
    # initialize_full_app 내에서 이미 로깅이 설정되어 있으므로, 
    # 여기서 다시 app.logger를 설정할 필요는 없습니다.
    app.logger.info("Starting Flask development server...")
    app.run(debug=app.config.get('DEBUG', False), host='0.0.0.0', port=5000)