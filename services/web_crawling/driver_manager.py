import os
import logging
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import WebDriverException

logger = logging.getLogger(__name__)

class ChromeDriverManager:
    """
    Selenium ChromeDriver의 생명주기를 관리하는 클래스입니다.
    드라이버 초기화, 옵션 설정, 종료 등을 담당합니다.
    """
    _instance = None # 싱글톤 패턴을 위한 인스턴스 변수

    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            cls._instance = super(ChromeDriverManager, cls).__new__(cls)
        return cls._instance

    def __init__(self, driver_path: str = None, headless: bool = True):
        # 이미 초기화된 경우 다시 초기화하지 않음 (싱글톤)
        if hasattr(self, '_initialized') and self._initialized:
            return

        self._driver = None
        self.driver_path = self._resolve_driver_path(driver_path)
        self.headless = headless
        self._initialized = True # 초기화 완료 플래그

    def _resolve_driver_path(self, driver_path: str | None) -> str:
        """
        드라이버 경로를 결정합니다. 인자로 주어지지 않으면 기본 경로를 계산합니다.
        """
        if driver_path:
            if not os.path.exists(driver_path):
                logger.error(f"Provided driver path does not exist: {driver_path}")
                raise FileNotFoundError(f"ChromeDriver not found at: {driver_path}")
            return driver_path
        
        # 기본 경로 계산 (프로젝트 루트의 drivers 폴더)
        current_file_abs_path = os.path.abspath(__file__)
        web_crawling_dir = os.path.dirname(current_file_abs_path) # services/web_crawling
        project_root_abs_path = os.path.abspath(os.path.join(web_crawling_dir, '..', '..')) # ai-content-marketing-tool
        default_driver_path = os.path.join(project_root_abs_path, 'drivers', 'chromedriver.exe')

        if not os.path.exists(default_driver_path):
            logger.error(f"Default ChromeDriver path does not exist: {default_driver_path}")
            raise FileNotFoundError(f"ChromeDriver not found at: {default_driver_path}. Please ensure it's in your project's 'drivers' folder.")
        
        return default_driver_path

    def get_driver(self) -> webdriver.Chrome:
        """
        ChromeDriver 인스턴스를 반환합니다. 이미 초기화되어 있으면 기존 인스턴스를 반환합니다.
        """
        if self._driver is None or not self._is_driver_alive():
            logger.info(f"Initializing new ChromeDriver instance. Headless: {self.headless}")
            try:
                chrome_options = Options()
                if self.headless:
                    chrome_options.add_argument("--headless")
                chrome_options.add_argument("--no-sandbox")
                chrome_options.add_argument("--disable-dev-shm-usage")
                chrome_options.add_argument("--window-size=1920,1080") # Headless 시 화면 크기 설정
                chrome_options.add_argument("--disable-gpu") # 일부 환경에서 필요
                chrome_options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36")
                chrome_options.add_experimental_option('excludeSwitches', ['enable-logging'])
                chrome_options.add_argument("--ignore-certificate-errors")
                chrome_options.add_argument("--allow-insecure-localhost")
                chrome_options.add_argument("--ignore-ssl-errors")
                chrome_options.add_argument("--disable-features=NetworkService") # 네트워크 서비스 비활성화

                service = Service(executable_path=self.driver_path)
                self._driver = webdriver.Chrome(service=service, options=chrome_options)
                logger.debug("ChromeDriver initialized successfully.")
            except WebDriverException as e:
                logger.critical(f"Failed to initialize ChromeDriver: {e}")
                raise
            except FileNotFoundError as e:
                logger.critical(f"ChromeDriver executable not found: {e}")
                raise
            except Exception as e:
                logger.critical(f"An unexpected error occurred during ChromeDriver initialization: {e}")
                raise
        return self._driver

    def _is_driver_alive(self) -> bool:
        """드라이버가 여전히 유효한지 확인합니다."""
        if self._driver:
            try:
                # 간단한 명령을 실행하여 드라이버가 살아있는지 확인
                self._driver.current_url 
                return True
            except WebDriverException:
                logger.warning("Existing ChromeDriver instance is no longer alive.")
                return False
        return False

    def quit_driver(self):
        """현재 ChromeDriver 인스턴스를 종료합니다."""
        if self._driver:
            try:
                self._driver.quit()
                logger.info("ChromeDriver instance quit successfully.")
            except Exception as e:
                logger.warning(f"Error quitting ChromeDriver: {e}")
            finally:
                self._driver = None # 종료 후 인스턴스 초기화

    def __enter__(self):
        """with 문 사용을 위한 컨텍스트 매니저 진입점."""
        return self.get_driver()

    def __exit__(self, exc_type, exc_val, exc_tb):
        """with 문 사용을 위한 컨텍스트 매니저 종료점."""
        self.quit_driver()