import datetime
import logging
from fastapi import APIRouter, HTTPException, Form
from pydantic import EmailStr
from sqlalchemy import select
from app.config import SessionDep, create_otp_arg, otp_expired_minutes
from app.users.models import UsersModel
from app.users.schemas import UserActivateWithOTPSchema
from app.users.utils.security_password import check_password
from app.celery_config import create_email_message


logger = logging.getLogger(__name__)
router = APIRouter(tags=["Activate"], prefix='/users/activate')


@router.post('/')
async def activate_user_with_otp(input_data: UserActivateWithOTPSchema,
                                 session: SessionDep
):
    user_email = input_data.email
    user_otp = input_data.otp

    query = select(UsersModel).where(UsersModel.email == user_email)
    res = await session.execute(query)
    user_db: UsersModel = res.scalars().one_or_none()

    if user_db is None:
        logger.info(f"User with {user_email=} not found")
        raise HTTPException(400, f"Not found any user with this email")

    otp_in_db = user_db.otp
    otp_expire_in_db = user_db.otp_expire
    otp_try_in_db = user_db.otp_try

    if user_db.is_verified or not user_db.active:
        logger.info(f"User {user_email=} already activate ot inactive")
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


@router.post('/refresh')
async def activate_refresh_otp(
        session: SessionDep,
        email: EmailStr = Form(),
        password: str = Form(min_length=8, max_length=20)
):

    query = select(UsersModel).where(UsersModel.email == email)
    res = await session.execute(query)
    user_db: UsersModel = res.scalars().one_or_none()

    if user_db is None:
        logger.info(f"User with {email=} not found")
        raise HTTPException(400, "Invalid credentials")
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



