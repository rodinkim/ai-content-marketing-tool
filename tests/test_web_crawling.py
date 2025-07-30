import pytest
from unittest.mock import Mock, patch, MagicMock
from services.web_crawling.web_content_extractor import extract_text_from_url, get_specific_extractor
from services.web_crawling.driver_manager import ChromeDriverManager
from services.web_crawling.extractors.base_extractor import BaseExtractor


class TestWebContentExtractor:
    """웹 콘텐츠 추출기 테스트 클래스"""

    def test_get_specific_extractor_itworld(self):
        """ITWorld 추출기 선택 테스트"""
        url = "https://www.itworld.co.kr/news/12345"
        extractor = get_specific_extractor(url)
        
        assert extractor is not None
        assert "ITWorld" in str(type(extractor))

    def test_get_specific_extractor_fashionbiz(self):
        """Fashionbiz 추출기 선택 테스트"""
        url = "https://www.fashionbiz.co.kr/article/67890"
        extractor = get_specific_extractor(url)
        
        assert extractor is not None
        assert "Fashionbiz" in str(type(extractor))

    def test_get_specific_extractor_hidoc(self):
        """Hidoc 추출기 선택 테스트"""
        url = "https://news.hidoc.co.kr/healthstory/news-12345"
        extractor = get_specific_extractor(url)
        
        assert extractor is not None
        assert "Hidoc" in str(type(extractor))

    def test_get_specific_extractor_beautynury(self):
        """Beautynury 추출기 선택 테스트"""
        url = "https://www.beautynury.com/news/54321"
        extractor = get_specific_extractor(url)
        
        assert extractor is not None
        assert "Beautynury" in str(type(extractor))

    def test_get_specific_extractor_tlnews(self):
        """TLNews 추출기 선택 테스트"""
        url = "https://www.tlnews.co.kr/travel/98765"
        extractor = get_specific_extractor(url)
        
        assert extractor is not None
        assert "TLNews" in str(type(extractor))

    def test_get_specific_extractor_unknown_domain(self):
        """알 수 없는 도메인 테스트"""
        url = "https://www.unknown-site.com/article/123"
        extractor = get_specific_extractor(url)
        
        # 알 수 없는 도메인은 None 반환
        assert extractor is None

    def test_get_specific_extractor_with_www(self):
        """www가 포함된 도메인 테스트"""
        url = "https://www.itworld.co.kr/news/12345"
        extractor = get_specific_extractor(url)
        
        assert extractor is not None
        assert "ITWorld" in str(type(extractor))

    def test_get_specific_extractor_without_www(self):
        """www가 없는 도메인 테스트"""
        url = "https://itworld.co.kr/news/12345"
        extractor = get_specific_extractor(url)
        
        assert extractor is not None
        assert "ITWorld" in str(type(extractor))

    @patch('services.web_crawling.web_content_extractor.get_specific_extractor')
    def test_extract_text_from_url_with_specific_extractor(self, mock_get_extractor):
        """특정 추출기가 있는 경우 테스트"""
        # Mock 설정
        mock_extractor = Mock()
        mock_extractor.get_article_details.return_value = {
            "title": "테스트 제목",
            "content": "테스트 내용",
            "author": "테스트 작성자"
        }
        mock_get_extractor.return_value = mock_extractor

        url = "https://www.itworld.co.kr/news/12345"
        result = extract_text_from_url(url)
        
        assert result is not None
        assert result["title"] == "테스트 제목"
        assert result["content"] == "테스트 내용"
        mock_extractor.get_article_details.assert_called_once_with(url)

    @patch('services.web_crawling.web_content_extractor.get_specific_extractor')
    @patch('services.web_crawling.web_content_extractor.BaseExtractor')
    def test_extract_text_from_url_fallback_to_base(self, mock_base_extractor, mock_get_extractor):
        """특정 추출기가 없을 때 BaseExtractor로 폴백 테스트"""
        # Mock 설정
        mock_get_extractor.return_value = None  # 특정 추출기 없음
        
        mock_base_instance = Mock()
        mock_base_instance._fetch_html.return_value = "<html>테스트 HTML</html>"
        mock_base_instance._extract_main_content.return_value = {
            "title": "기본 제목",
            "content": "기본 내용"
        }
        mock_base_extractor.return_value = mock_base_instance

        url = "https://www.unknown-site.com/article/123"
        result = extract_text_from_url(url)
        
        assert result is not None
        assert result["title"] == "기본 제목"
        assert result["content"] == "기본 내용"
        mock_base_instance._fetch_html.assert_called_once_with(url)


class TestChromeDriverManager:
    """ChromeDriver 매니저 테스트 클래스"""

    @patch('services.web_crawling.driver_manager.os.path.exists')
    @patch('services.web_crawling.driver_manager.os.path.abspath')
    def test_driver_manager_initialization(self, mock_abspath, mock_exists):
        """드라이버 매니저 초기화 테스트"""
        # Mock 설정
        mock_exists.return_value = True
        mock_abspath.return_value = "/fake/path"

        with patch('services.web_crawling.driver_manager.webdriver.Chrome') as mock_chrome:
            mock_chrome.return_value = Mock()
            
            manager = ChromeDriverManager(headless=True)
            
            assert manager.headless is True
            assert manager._driver is None

    @patch('services.web_crawling.driver_manager.os.path.exists')
    def test_driver_manager_invalid_path(self, mock_exists):
        """잘못된 드라이버 경로 테스트"""
        mock_exists.return_value = False
        
        with pytest.raises(FileNotFoundError):
            ChromeDriverManager(driver_path="/invalid/path")

    @patch('services.web_crawling.driver_manager.os.path.exists')
    @patch('services.web_crawling.driver_manager.webdriver.Chrome')
    def test_get_driver_creates_new_instance(self, mock_chrome, mock_exists):
        """드라이버 인스턴스 생성 테스트"""
        mock_exists.return_value = True
        
        mock_driver = Mock()
        mock_driver.current_url = "https://example.com"
        mock_chrome.return_value = mock_driver
        
        manager = ChromeDriverManager(headless=True)
        driver = manager.get_driver()
        
        assert driver is not None
        mock_chrome.assert_called_once()

    @patch('services.web_crawling.driver_manager.os.path.exists')
    @patch('services.web_crawling.driver_manager.webdriver.Chrome')
    def test_get_driver_reuses_existing_instance(self, mock_chrome, mock_exists):
        """기존 드라이버 인스턴스 재사용 테스트"""
        mock_exists.return_value = True
        
        mock_driver = Mock()
        mock_driver.current_url = "https://example.com"
        mock_chrome.return_value = mock_driver
        
        manager = ChromeDriverManager(headless=True)
        driver1 = manager.get_driver()
        driver2 = manager.get_driver()
        
        assert driver1 is driver2
        # Chrome은 한 번만 호출되어야 함
        mock_chrome.assert_called_once()


class TestBaseExtractor:
    """기본 추출기 테스트 클래스"""

    @pytest.fixture
    def base_extractor(self):
        """기본 추출기 인스턴스 생성"""
        return BaseExtractor()

    def test_base_extractor_initialization(self, base_extractor):
        """기본 추출기 초기화 테스트"""
        assert base_extractor.driver_manager is not None
        assert base_extractor.BASE_URL == ""
        assert base_extractor.HEADERS is not None
        assert base_extractor.TIMEOUT == 15

    @patch('services.web_crawling.extractors.base_extractor.requests.get')
    def test_fetch_html_with_requests_success(self, mock_get, base_extractor):
        """requests를 사용한 HTML 가져오기 성공 테스트"""
        # Mock 설정
        mock_response = Mock()
        mock_response.raise_for_status.return_value = None
        mock_response.content = b"<html>Test HTML</html>"
        mock_response.encoding = "utf-8"
        mock_response.apparent_encoding = "utf-8"
        mock_get.return_value = mock_response

        with patch('services.web_crawling.extractors.base_extractor.HTMLDecoder.decode_html_content') as mock_decode:
            mock_decode.return_value = "<html>테스트 HTML</html>"
            
            result = base_extractor._fetch_html("https://example.com", use_selenium=False)
            
            assert result == "<html>테스트 HTML</html>"
            mock_get.assert_called_once()

    @patch('services.web_crawling.extractors.base_extractor.requests.get')
    def test_fetch_html_with_requests_error(self, mock_get, base_extractor):
        """requests를 사용한 HTML 가져오기 오류 테스트"""
        # Mock 설정
        mock_get.side_effect = Exception("Network error")
        
        result = base_extractor._fetch_html("https://example.com", use_selenium=False)
        
        assert result is None

    @patch('services.web_crawling.extractors.base_extractor.webdriver.Chrome')
    def test_fetch_html_with_selenium_success(self, mock_chrome, base_extractor):
        """Selenium을 사용한 HTML 가져오기 성공 테스트"""
        # Mock 설정
        mock_driver = Mock()
        mock_driver.page_source = "<html>Selenium HTML</html>"
        mock_chrome.return_value = mock_driver
        
        with patch.object(base_extractor.driver_manager, 'get_driver') as mock_get_driver:
            mock_get_driver.return_value = mock_driver
            
            result = base_extractor._fetch_html("https://example.com", use_selenium=True)
            
            assert result == "<html>Selenium HTML</html>"
            mock_driver.get.assert_called_once_with("https://example.com")

    def test_extract_main_content(self, base_extractor):
        """메인 콘텐츠 추출 테스트"""
        html_content = """
        <html>
            <head><title>테스트 제목</title></head>
            <body>
                <h1>메인 제목</h1>
                <p>메인 내용입니다.</p>
            </body>
        </html>
        """
        
        with patch('services.web_crawling.extractors.base_extractor.extract') as mock_extract:
            mock_extract.return_value = "추출된 텍스트 내용"
            
            result = base_extractor._extract_main_content(html_content, "https://example.com")
            
            assert result is not None
            mock_extract.assert_called_once() 