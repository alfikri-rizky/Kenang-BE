import structlog
from celery import shared_task

logger = structlog.get_logger(__name__)


@shared_task
def send_push_notification(user_id: str, title: str, body: str) -> dict:
    logger.info(
        "push_notification_placeholder",
        user_id=user_id,
        title=title,
    )
    return {
        "status": "pending",
        "message": "Notifikasi akan diimplementasi di fase selanjutnya",
    }


@shared_task
def send_bulk_notifications(user_ids: list[str], title: str, body: str) -> dict:
    logger.info(
        "bulk_notification_placeholder",
        user_count=len(user_ids),
        title=title,
    )
    return {
        "status": "pending",
        "message": "Notifikasi bulk akan diimplementasi di fase selanjutnya",
    }
