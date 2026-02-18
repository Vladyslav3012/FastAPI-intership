import datetime
import logging
from fastapi import APIRouter, Depends, HTTPException
from ..utils.security_password import check_password
from app.config import SessionDep, create_otp_arg, otp_expired_minutes
from app.users.models import UsersModel
from app.users.schemas import UserResetPasswordSchema, UserOnlyEmailSchema, UserResetPasswordWithOTPSchema
from app.users.utils import permission, auth_utils, users_utils
from ..utils.users_utils import get_user_by_email
from app.celery_config import create_email_message


router = APIRouter(tags=["Password changes"], prefix='/users')
logger = logging.getLogger(__name__)


@router.post('/change-password', dependencies=[permission.AnyVerified])
async def reset_user_password_auth(
        session: SessionDep,
        user_password: UserResetPasswordSchema,
        user: UsersModel =
        Depends(users_utils.UserGetterFromTokenType(auth_utils.ACCESS_TOKEN_FIELD)),
):
    old_password = user_password.old_password
    new_password = user_password.new_password

    if not check_password(old_password, user._hashed_password_):
        logger.info(f"User {user.email=} send invalid password")
        raise HTTPException(400, "You send incorrect password")

    if old_password == new_password:
        logger.info(f'User {user.email=} sent two similar password')
        raise HTTPException(400, "Passwords must be different than old")

    if user.active and user.is_verified:
        user.password = new_password
        session.add(user)
        await session.commit()

        return {"msg": "Success reset password"}

    raise HTTPException(400, "User not active or not verify")


@router.post('/request-reset-password')
async def request_otp_for_reset_user_password_unauth(
        session: SessionDep,
        email_data: UserOnlyEmailSchema
):
    email = email_data.email

    user_db = await get_user_by_email(email, session)

    if not user_db.is_verified or not user_db.active:
        logger.info(f"User with {email=} inactive or not verify")
        raise HTTPException(403, "You need verify you account")

    otp, otp_expire, otp_try = create_otp_arg()

    user_db.otp = otp
    user_db.otp_expire = otp_expire
    user_db.otp_try = otp_try

    # sending email with otp
    subject = "You email ask to reset password"
    body = ("If you do not ask this code, ignore this email."
            f" You code is: {otp}"
            f" You have {otp_expired_minutes} minutes to activate with this code")
    create_email_message.delay([email], subject, body)

    logger.info(f"Success sending otp for reset password to {email=}")

    session.add(user_db)
    await session.commit()

    return {"msg": "Code for reset password has been sending to your email"}


@router.post('/reset-password')
async def reset_user_password_unauth(
        session: SessionDep,
        user_data: UserResetPasswordWithOTPSchema
):
    email = user_data.email
    user_otp = user_data.otp
    new_password = user_data.new_password

    user_db = await get_user_by_email(email, session)

    otp_in_db = user_db.otp
    otp_expire_in_db = user_db.otp_expire
    otp_try_in_db = user_db.otp_try

    if not user_db.is_verified or not user_db.active:
        logger.info(f"User {email=} inactivate or inactive")
        raise HTTPException(400, "User already activated or inactive")

    if otp_in_db is None or otp_try_in_db is None:
        logger.info(f'OTP or otp try in user with {email=} == None')
        raise HTTPException(400, "No active otp, resend request to activate")

    if otp_try_in_db <= 0:
        raise HTTPException(400, "You have no more attempts."
                                 " Please request a new code")
    if otp_expire_in_db < datetime.datetime.now(datetime.timezone.utc):
        raise HTTPException(400, "You code expired. Please request a new code")

    if check_password(new_password, user_db.password):
        logger.info(f'User {email=} sent two similar password')
        raise HTTPException(400, "Passwords must be different than old")

    if otp_in_db == user_otp:
        user_db.password = new_password

        user_db.otp = None
        user_db.otp_expire = None
        user_db.otp_try = None

        session.add(user_db)
        await session.commit()
        return {"msg": "Success reset you password"}

    user_db.otp_try -= 1
    session.add(user_db)
    await session.commit()
    raise HTTPException(400, "You send incorrect code, please try again"
                             f"try left {user_db.otp_try}")


