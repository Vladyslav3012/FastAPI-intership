import logging
from fastapi import APIRouter, Depends, HTTPException

from ..utils.auth_utils import validate_user_otp_state
from ..utils.security_password import check_password
from app.config import SessionDep, create_otp_arg, otp_expired_minutes, email_request_limit
from app.users.models import UsersModel
from app.users.schemas import UserResetPasswordSchema, UserOnlyEmailSchema, UserResetPasswordWithOTPSchema
from app.users.utils import permission, auth_utils, users_utils
from ..utils.users_utils import get_user_by_email
from app.users.tasks import sending_email_message


router = APIRouter(tags=["Password changes"], prefix='/users')
logger = logging.getLogger(__name__)


@router.post('/change-password', dependencies=[permission.AnyVerified])
async def reset_user_password_auth(
        session: SessionDep,
        user_password: UserResetPasswordSchema,
        user: UsersModel =
        Depends(users_utils.UserGetterFromTokenType(auth_utils.ACCESS_TOKEN_FIELD)),
) -> dict:
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
        logging.info(f"User {user.email} succes change his password")
        return {"msg": "Success reset password"}

    raise HTTPException(400, "User not active or not verify")


@router.post('/request-reset-password', dependencies=[email_request_limit])
async def request_otp_for_reset_user_password_unauth(
        session: SessionDep,
        email_data: UserOnlyEmailSchema
) -> dict:
    email = email_data.email

    user_db = await get_user_by_email(email, session)

    if not user_db.is_verified or not user_db.active:
        logger.info(f"User with {email=} inactive or not verify")
        raise HTTPException(403, "You need verify you account")

    otp, otp_expire, otp_try = create_otp_arg()

    user_db.otp = otp
    user_db.otp_expire = otp_expire
    user_db.otp_try = otp_try
    logger.info(f"Success generate otp, start sending email to {email}")
    
    # sending email with otp
    subject = "You email ask to reset password"
    body = ("If you do not ask this code, ignore this email."
            f" You code is: {otp}"
            f" You have {otp_expired_minutes} minutes to activate with this code")
    sending_email_message.delay([email], subject, body)

    logger.info(f"Success sending otp for reset password to {email=}")

    session.add(user_db)
    await session.commit()

    return {"msg": "Code for reset password has been sending to your email"}


@router.post('/reset-password')
async def reset_user_password_unauth(
        session: SessionDep,
        user_data: UserResetPasswordWithOTPSchema
) -> dict:
    email = user_data.email
    user_otp = user_data.otp
    new_password = user_data.new_password

    user_db = await get_user_by_email(email, session)
    logger.info(f"User with {email=} start reset his password")
    
    if check_password(new_password, user_db.password):
        logger.info(f'User {email=} sent two similar password')
        raise HTTPException(400, "Passwords must be different than old")
    
    otp_in_db = user_db.otp
    otp_expire_in_db = user_db.otp_expire
    otp_try_in_db = user_db.otp_try
    
    validate_otp = validate_user_otp_state(user_db=user_db, otp_in_db=otp_in_db,
                            otp_try_in_db=otp_try_in_db,
                            otp_expire_in_db=otp_expire_in_db,
                            user_provided_otp=user_otp,
                            email=email)

    if validate_otp:
        user_db.password = new_password

        user_db.otp = None
        user_db.otp_expire = None
        user_db.otp_try = None

        session.add(user_db)
        await session.commit()
        logger.info(f"User with {email=} success reset his password")
        return {"msg": "Success reset you password"}

    user_db.otp_try -= 1
    session.add(user_db)
    await session.commit()
    raise HTTPException(400, "You send incorrect code, please try again"
                             f"try left {user_db.otp_try}")
