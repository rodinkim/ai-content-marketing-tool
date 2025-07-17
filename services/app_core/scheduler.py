# app_core/scheduler.py

import logging
from flask import Flask
from flask_apscheduler import APScheduler
from extensions import scheduler
from models import User
from services.web_crawling.crawler_tasks import perform_marketing_crawl_task

logger = logging.getLogger(__name__)

def _start_and_clean_scheduler():
    """스케줄러를 시작하고 기존 작업을 정리합니다."""
    if not scheduler.running:
        scheduler.start()
        logger.info("Scheduler started.")

    if scheduler.get_job('scheduled_marketing_crawl'):
        scheduler.remove_job('scheduled_marketing_crawl')
        logger.info("Existing 'scheduled_marketing_crawl' job removed.")

def _get_system_crawler_user(app: Flask) -> User | None:
    """시스템 크롤러 사용자를 데이터베이스에서 조회합니다."""
    system_crawler_username = app.config.get('CRAWLER_UPLOADER_USERNAME', 'system_crawler_default')
    user = User.query.filter_by(username=system_crawler_username).first()
    
    if not user:
        logger.error(f"시스템 크롤러 사용자 '{system_crawler_username}'를 DB에서 찾을 수 없습니다. 스케줄링된 크롤링 작업을 등록할 수 없습니다.")
        logger.error(f"데이터 무결성을 위해 '{system_crawler_username}'와 같은 이름으로 User를 생성하거나 config에 올바른 사용자명을 설정해주세요.")
    
    return user

def _add_marketing_crawl_job(user_id: int):
    """주간 마케팅 뉴스 크롤링 작업을 스케줄러에 등록합니다."""
    # Flask-APScheduler는 scheduler.app을 통해 Flask 앱 컨텍스트에 접근 가능
    def _perform_task_wrapper(system_user_id: int):
        with scheduler.app.app_context(): # 스케줄러 인스턴스에 연결된 앱 컨텍스트 사용
            perform_marketing_crawl_task(system_user_id=system_user_id)

    scheduler.add_job(
        id='scheduled_marketing_crawl',
        func=lambda: _perform_task_wrapper(user_id),
        trigger='cron',
        day_of_week='tue',
        hour=11,
        minute=20,
        timezone='Asia/Seoul',
        misfire_grace_time=3600
    )
    logger.info("Scheduler: Weekly marketing news crawling job registered with system user ID.")

def initialize_scheduler_tasks(app: Flask):
    """
    애플리케이션 스케줄러의 모든 작업을 초기화하고 등록합니다.
    이 함수는 app_factory_utils.py에서 호출됩니다.
    """
    _start_and_clean_scheduler()

    with app.app_context(): # 사용자 조회는 DB 접근이므로 app_context 필요
        system_crawler_user = _get_system_crawler_user(app)
    
    if not system_crawler_user:
        return # 사용자 없으면 작업 등록 안 함

    _add_marketing_crawl_job(system_crawler_user.id)
    logger.info("Scheduler tasks initialized.")