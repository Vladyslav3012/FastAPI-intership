import logging
from sqlalchemy import delete, select
from sqlalchemy.exc import IntegrityError
from fastapi import APIRouter, HTTPException, Depends
from app.users.tasks import sending_email_message
from app.config import SessionDep, create_otp_arg, otp_expired_minutes, login_request_limit
from app.redis_config import add_jti_to_blocklist, check_token_in_blacklist
from app.users.models import UsersModel, RefreshTokenModel
from app.users.schemas import UserOutputSchema, UserInputSchema
from app.users.utils import users_utils, auth_utils
from app.users.utils.auth_utils import clean_old_sessions


logger = logging.getLogger(__name__)
router = APIRouter(tags=["Auth"], prefix='/users/auth')


@router.post('/sign', response_model=UserOutputSchema)
async def signup_user(user: UserInputSchema, session: SessionDep) -> UsersModel:
    # create args for otp verify
    otp, otp_expire, otp_try = create_otp_arg()

    try:
        new_user = UsersModel(
            email=user.email,
            username=user.username,
            age=user.age,
            password=user.password,
            # add otp args in model
            otp=otp,
            otp_expire=otp_expire,
            otp_try=otp_try
        )
        session.add(new_user)
        await session.commit()
        logger.info(f"Success sign up new user. {user.email=}")

        # sending email with otp
        logger.info(f"Start sending welcome email to new user with {user.email=}")
        subject = "Welcome on our website"
        body = ("Now you need to verify you account with otp"
                f" You code is: {otp}"
                f" You have {otp_expired_minutes} minutes to activate with this code")
        sending_email_message.delay([user.email], subject, body)

        logger.info(f"Success sending welcome letter to {user.email}")
        return new_user
    except IntegrityError:
        logger.info(f"{user.email=} has been used")
        await session.rollback()
        raise HTTPException(409, "This email has been used")


@router.post('/login', dependencies=[login_request_limit])
async def login_user(session: SessionDep,
                     user: UserOutputSchema =
                     Depends(users_utils.check_auth_user_in_db)) -> auth_utils.TokenInfo:

    tokens = await auth_utils.create_token_pair(session, user)
    access_token = tokens.get('access_token')
    refresh_token = tokens.get('refresh_token')

    await clean_old_sessions(user.id, session)

    await session.commit()
    logger.info(f"Success login {user.email=}")

    return auth_utils.TokenInfo(
        access_token=access_token,
        refresh_token=refresh_token,
    )


@router.post('/logout')
async def logout_user(
        session: SessionDep,
        payload: dict = Depends(auth_utils.get_payload_from_token)
):
    jti = payload.get('jti')
    exp = payload.get('exp')
    refresh_jti = payload.get('refresh_jti')

    if await check_token_in_blacklist(jti):
        logger.warning(f"Token with {jti=} already in black list")
        raise HTTPException(401, "Invalid token")

    await add_jti_to_blocklist(jti=jti, exp=exp)
    logger.info(f"Logout: add token with {jti=} to blacklist")

    if refresh_jti:
        query = delete(RefreshTokenModel).where(RefreshTokenModel.jti == refresh_jti)
        await session.execute(query)
        await session.commit()
        logger.info(f"Logout: success delete refersh token with {jti=} from database")
        return {"msg": "Success logout from this device only"}

    logger.info("Token has not refresh_jti")
    raise HTTPException(401, "Invalid token")


@router.get('/me')
async def get_active_auth_user(
        user: UserOutputSchema =
        Depends(users_utils.UserGetterFromTokenType(auth_utils.ACCESS_TOKEN_FIELD))
) -> dict:
    return {
        "email": user.email,
        "username": user.username
    }


@router.post('/refresh', response_model=auth_utils.TokenInfo,
             response_model_exclude_none=True, dependencies=[login_request_limit])
async def refresh_jwt(
        session: SessionDep,
        payload: dict = Depends(auth_utils.get_payload_from_token),
        user: UserOutputSchema =
        Depends(users_utils.UserGetterFromTokenType(auth_utils.REFRESH_TOKEN_FIELD)),
) -> auth_utils.TokenInfo:
    logging.info(f"Refresh token: start refresh for {user.email=}")
    jti = payload.get('jti')
    if not jti:
        logger.error("Refresh token: Token has not jti")
        raise HTTPException(401, "Invalid token")

    query = select(RefreshTokenModel).where(RefreshTokenModel.jti == jti)
    result = await session.execute(query)
    token_db = result.scalars().one_or_none()

    if not token_db:
        logger.info(f"Refresh  token: Token {jti=} not found in db")
        raise HTTPException(401, "Invalid token")

    await session.delete(token_db)
    logger.info(f"Refresh token: Success delete old token from database with {jti=}")

    tokens = await auth_utils.create_token_pair(session, user)
    access_token = tokens.get('access_token')
    refresh_token = tokens.get('refresh_token')

    await session.commit()
    logger.info(f"Refresh token: success refres tokens for {user.email=}")

    return auth_utils.TokenInfo(
        access_token=access_token,
        refresh_token=refresh_token
    )
