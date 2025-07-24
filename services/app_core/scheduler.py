# app_core/scheduler.py
import logging
from flask import Flask
from flask_apscheduler import APScheduler
from extensions import scheduler
from models import User
from services.web_crawling.crawler_tasks import perform_marketing_crawl_task
from services.ai_rag.rag_system import get_rag_system

logger = logging.getLogger(__name__)

def add_cron_job(job_id, func, trigger_kwargs, description=None):
    """공통 cron job 등록 함수."""
    if scheduler.get_job(job_id):
        scheduler.remove_job(job_id)
        logger.info(f"Existing job '{job_id}' removed.")
    scheduler.add_job(
        id=job_id,
        func=func,
        trigger='cron',
        **trigger_kwargs,
        timezone='Asia/Seoul',
        misfire_grace_time=3600
    )
    logger.info(f"Scheduler: {description or job_id} job registered.")

def _start_and_clean_scheduler():
    """스케줄러를 시작하고 기존 작업을 정리합니다."""
    if not scheduler.running:
        scheduler.start()
        logger.info("Scheduler started.")

def _get_system_crawler_user(app: Flask) -> User | None:
    """시스템 크롤러 사용자를 데이터베이스에서 조회합니다."""
    system_crawler_username = app.config.get('CRAWLER_UPLOADER_USERNAME', 'system_crawler_default')
    user = User.query.filter_by(username=system_crawler_username).first()
    
    if not user:
        logger.error(f"시스템 크롤러 사용자 '{system_crawler_username}'를 DB에서 찾을 수 없습니다. 스케줄링된 크롤링 작업을 등록할 수 없습니다.")
        logger.error(f"데이터 무결성을 위해 '{system_crawler_username}'와 같은 이름으로 User를 생성하거나 config에 올바른 사용자명을 설정해주세요.")
    
    return user

def _marketing_crawl_job(user_id: int):
    with scheduler.app.app_context():
        perform_marketing_crawl_task(system_user_id=user_id)

def _faiss_reload_job():
    with scheduler.app.app_context():
        rag_system = get_rag_system()
        if rag_system:
            rag_system._load_faiss_from_pgvector()
            logger.info("Scheduler: FAISS 인덱스가 PgVector DB로부터 재로드되었습니다.")
        else:
            logger.error("Scheduler: RAGSystem 인스턴스를 가져올 수 없어 FAISS 인덱스 재로드 실패.")

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

    add_cron_job(
        job_id='scheduled_marketing_crawl',
        func=lambda: _marketing_crawl_job(system_crawler_user.id),
        trigger_kwargs={
            'day_of_week': 'thu',
            'hour': 15,
            'minute': 4
        },
        description='Weekly marketing news crawling'
    )
    add_cron_job(
        job_id='scheduled_faiss_reload',
        func=_faiss_reload_job,
        trigger_kwargs={
            'hour': 3,
            'minute': 0
        },
        description='Daily FAISS reload'
    )
    logger.info("Scheduler tasks initialized.")