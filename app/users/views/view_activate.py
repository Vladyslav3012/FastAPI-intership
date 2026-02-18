import datetime
import logging
from fastapi import APIRouter, HTTPException
from app.config import SessionDep, create_otp_arg, otp_expired_minutes, email_request_limit
from app.users.schemas import UserActivateWithOTPSchema, UserLogInSchema
from app.users.utils.security_password import check_password
from app.celery_config import create_email_message
from app.users.utils.users_utils import get_user_by_email

logger = logging.getLogger(__name__)
router = APIRouter(tags=["Activate"], prefix='/users/activate')


@router.post('/')
async def activate_user_with_otp(input_data: UserActivateWithOTPSchema,
                                 session: SessionDep
) -> dict:
    user_email = input_data.email
    user_otp = input_data.otp

    user_db = await get_user_by_email(user_email, session)

    otp_in_db = user_db.otp
    otp_expire_in_db = user_db.otp_expire
    otp_try_in_db = user_db.otp_try

    if user_db.is_verified or not user_db.active:
        logger.info(f"User {user_email=} already activate or inactive")
        raise HTTPException(400, "User already activated or inactive")

    if otp_in_db is None or otp_try_in_db is None:
        logger.info(f'OTP or otp try in user with {user_email=} == None')
        raise HTTPException(400, "No active otp, resend request to activate")

    if otp_try_in_db <= 0:
        raise HTTPException(400, "You have no more attempts."
                                 " Please request a new code")
    if otp_expire_in_db < datetime.datetime.now(datetime.timezone.utc):
        raise HTTPException(400, "You code expired. Please request a new code")

    if otp_in_db == user_otp:
        user_db.is_verified = True

        user_db.otp = None
        user_db.otp_expire = None
        user_db.otp_try = None

        session.add(user_db)
        await session.commit()
        return {"msg": "Success verify you email address"}

    user_db.otp_try -= 1
    session.add(user_db)
    await session.commit()
    raise HTTPException(400, "You send incorrect code, please try again"
                             f"try left {user_db.otp_try}")


@router.post('/refresh', dependencies=[email_request_limit])
async def activate_refresh_otp(
        session: SessionDep,
        user_data: UserLogInSchema
) -> dict:
    email = user_data.email
    password = user_data.password

    user_db = await get_user_by_email(email, session)

    if user_db.is_verified or not user_db.active:
        logger.info(f"User with {email=} already verified or inactive")
        raise HTTPException(400, "User already verified or inactive")

    if check_password(password, user_db._hashed_password_):

        otp, otp_expire, otp_try = create_otp_arg()

        user_db.otp = otp
        user_db.otp_expire = otp_expire
        user_db.otp_try = otp_try

        #sending email with otp
        subject = "You email ask to refresh code for verifi account"
        body = ("If you do not ask this code, ignore this email."
                f" You code is: {otp}"
                f" You have {otp_expired_minutes} minutes to activate with this code")
        create_email_message.delay([email], subject, body)

        logger.info(f"Success sending new otp to {email=}")

        session.add(user_db)
        await session.commit()

        return {"msg": "New code send to you email"}

    logger.info("User send invalid password")
    raise HTTPException(400, "Invalid credentials")



