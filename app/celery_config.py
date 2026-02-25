import datetime
import logging
from celery import Celery
from fastapi_mail import MessageSchema, NameEmail, MessageType
import httpx
from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.orm import joinedload

from app.config import sync_new_session
from app.crypto.models import CoinModel, AlertModel, ConditionsEnum
from app.crypto.utils import api_crypto_url
from app.mail_config import mail
from asgiref.sync import async_to_sync


logger = logging.getLogger(__name__)
c_app = Celery()
c_app.config_from_object('app.config')


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


@c_app.task
def update_coin_price():
    url = api_crypto_url

    with httpx.Client() as client:
        response = client.get(url)
        data = response.json()

    logger.info(f"Got from api {data=}")

    coin_data = []
    for coin_name, coin_detail in data.items():
        price = coin_detail.get('usd')

        if price is None:
            logger.error(f"Not found price for {coin_name=}")
            continue

        coin_data.append({"name": coin_name, "current_price": coin_detail.get('usd')})

    logger.info(f"Coin data preview call func upsert {coin_data}")

    if not coin_data:
        logger.error(f"Does not exist coin data")
        return

    with sync_new_session() as session:
        query = pg_insert(CoinModel).values(coin_data)
        update_query = query.on_conflict_do_update(
            index_elements=['name'],
            set_={
                "current_price": query.excluded.current_price,
                "last_updated": func.now()
            }
        )
        session.execute(update_query)
        session.commit()
        logger.info("Success update coins price")

        check_alert_after_update.delay()



@c_app.task
def check_alert_after_update():
    with sync_new_session() as session:
        query = select(AlertModel).options(
            joinedload(AlertModel.coin), joinedload(AlertModel.user)
        ).where(AlertModel.is_active == True)

        alerts: list[AlertModel] = session.execute(query).scalars().all()


        for alert in alerts:
            now = datetime.datetime.now(datetime.timezone.utc)

            coin = alert.coin
            current_price = coin.current_price
            coin_name = coin.name

            target_price = alert.target_price
            conditions = alert.conditions

            current_user = alert.user
            current_user_email = current_user.email

            is_true = False
            if conditions == ConditionsEnum.above and current_price >= target_price:
                is_true = True
            elif conditions == ConditionsEnum.below and current_price <= target_price:
                is_true = True

            if is_true:
                alert.is_active = False

                # sending email
                subject = f"[ACTION REQUIRED] {coin_name} reached your target of ${target_price}!"
                body = f"""
                Hello {current_user.username}
                The market is moving! Your price alert for {coin_name} has just been triggered.
                Detail:
                Asset: {coin_name} (Alert: #{alert.id})

                Condition: Price went {conditions.value} ${target_price}

                Current Market Price: ${current_price}

                Time of Alert: {now} (UTC)
                """
                sending_email_message.delay([current_user_email], subject, body)


        session.commit()



c_app.conf.beat_schedule = {
    'update_coin_price': {
        'task': 'app.celery_config.update_coin_price',
        'schedule': 10.0
    },
}
