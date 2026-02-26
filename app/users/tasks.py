import logging

from app.celery_config import c_app
from fastapi_mail import MessageSchema, NameEmail, MessageType
from app.mail_config import mail
from asgiref.sync import async_to_sync

logger = logging.getLogger(__name__)

@c_app.task
def sending_email_message(recipients: list[NameEmail],
                          subject: str, body: str) -> bool:
    logger.info(f"Start sending email to {recipients}")
    message = MessageSchema(recipients=recipients, body=body,
                            subject=subject,
                            subtype=MessageType.plain)
    try:
        async_to_sync(mail.send_message)(message)
        logger.info(f"Success sending email to {recipients}")
        return True
    except Exception as e:
        logger.exception(f"Email send error: {e}")
        return False