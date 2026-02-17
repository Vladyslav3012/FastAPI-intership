import logging

from fastapi_mail import FastMail, ConnectionConfig, MessageSchema, MessageType
from pydantic import NameEmail, BaseModel

from .config import settings


logger = logging.getLogger(__name__)

class EmailSchema(BaseModel):
    emails: list[NameEmail]


mail_config = ConnectionConfig(
    MAIL_USERNAME=settings.EMAIL_HOST_USER,
    MAIL_PASSWORD=settings.EMAIL_HOST_PASSWORD,
    MAIL_FROM=settings.EMAIL_FROM,
    MAIL_PORT=settings.EMAIL_PORT,
    MAIL_SERVER=settings.EMAIL_HOST,
    MAIL_STARTTLS=True,
    MAIL_SSL_TLS=False,
    USE_CREDENTIALS=True,
    VALIDATE_CERTS=True
)

mail = FastMail(
    config=mail_config
)

async def send_email_message(recipients: list[NameEmail], body: str, subject: str) -> None:
    logger.info(f"Start sending email to {recipients}")
    message = MessageSchema(recipients=recipients, body=body,
                            subject=subject,
                            subtype=MessageType.plain)
    try:
        await mail.send_message(message=message)
        logger.info(f"Success sending email to {recipients}")
    except Exception as e:
        logger.exception(f"Email send error: {e}")
