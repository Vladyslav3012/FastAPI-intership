import datetime
import logging
import uuid
import jwt
from jwt.exceptions import InvalidTokenError
from fastapi import Depends, HTTPException
from fastapi.security import (HTTPAuthorizationCredentials, HTTPBearer)
from pydantic import BaseModel, EmailStr
from app.config import settings, SessionDep
from app.redis_config import check_token_in_blacklist
from app.users.models import RefreshTokenModel, UsersModel
from app.users.schemas import UserOutputSchema
from sqlalchemy import select


http_bearer = HTTPBearer()
logger = logging.getLogger(__name__)


"""
JWT token
"""

ACCESS_TOKEN_FIELD = "access"
REFRESH_TOKEN_FIELD = "refresh"


class TokenInfo(BaseModel):
    access_token: str
    refresh_token: str | None = None
    token_type: str = "Bearer"


"""
CREATE TOKEN AND DECODE
"""


def encode_jwt(payload: dict,
               expire_minutes: int,
               private_key: str = settings.auth_jwt.private_key_path.read_text(),
               algorithm: str = settings.auth_jwt.algorithm):

    now = datetime.datetime.now(datetime.UTC)
    expire = now + datetime.timedelta(minutes=expire_minutes)

    to_encode = payload.copy()
    to_encode.update(iat=now, exp=expire)

    token = jwt.encode(payload=to_encode,
                       key=private_key,
                       algorithm=algorithm)
    return token


def decode_jwt(token: str | bytes,
               public_key: str = settings.auth_jwt.public_key_path.read_text(),
               algorithm: str = settings.auth_jwt.algorithm
               ):
    decode_token = jwt.decode(jwt=token,
                              key=public_key,
                              algorithms=[algorithm])
    return decode_token


def create_jwt(token_type: str, token_data: dict, expire_minutes: int) -> str:
    jwt_payload = {"type": token_type}
    jwt_payload.update(token_data)
    return encode_jwt(payload=jwt_payload, expire_minutes=expire_minutes)


async def create_token_pair(session: SessionDep, user: UserOutputSchema) -> dict:

    # create refresh token
    jti_refresh = str(uuid.uuid4())

    now = datetime.datetime.now(datetime.UTC)
    expire = now + datetime.timedelta(minutes=settings.auth_jwt.refresh_token_expire_minutes)

    db_token = RefreshTokenModel(
        jti=jti_refresh,
        expire_at=expire,
        user_id=user.id
    )
    session.add(db_token)

    jwt_refresh_payload = {
        "sub": str(user.id),
        'jti': jti_refresh

    }
    refresh_token = create_jwt(REFRESH_TOKEN_FIELD,
                               jwt_refresh_payload,
                               settings.auth_jwt.refresh_token_expire_minutes)

    # access token
    jti_access = str(uuid.uuid4())

    jwt_access_payload = {
        "sub": str(user.id),
        "username": user.username,
        "email": user.email,
        "jti": jti_access,
        "refresh_jti": jti_refresh
    }
    access_token = create_jwt(ACCESS_TOKEN_FIELD, jwt_access_payload,
                              settings.auth_jwt.access_token_expire_minutes)

    return {
        "access_token": access_token,
        "refresh_token": refresh_token
    }


"""
HELPERS FUNC
"""


async def get_payload_from_token(
        credentials: HTTPAuthorizationCredentials = Depends(http_bearer)
) -> dict:
    token = credentials.credentials
    try:
        payload = decode_jwt(token=token, )
    except InvalidTokenError as e:
        logger.info(f"User enter invalid token: {e}")
        raise HTTPException(401, 'Invalid token')

    jti = payload.get("jti")
    if not jti:
        logger.info("User send token without jti")
        raise HTTPException(401, "Invalid token")

    return payload


# check type token, when need to refresh token allow only refresh
async def validate_token_by_type(payload: dict, token_type_to_check: str) -> None:
    current_token_type = payload.get('type')
    if current_token_type != token_type_to_check:
        logger.info(f"Token {current_token_type=} get, expected {token_type_to_check}")
        raise HTTPException(401, "Invalid token")

    jti = payload.get('jti')
    check = await check_token_in_blacklist(jti)
    if check:
        logger.info("Token in blacklist")
        raise HTTPException(401, "Invalid token")


# clear old session with refresh token
async def clean_old_sessions(user_id: int, session, limit: int = 5) -> None:
    query = (select(RefreshTokenModel).
             where(RefreshTokenModel.user_id == user_id)
             .order_by(RefreshTokenModel.expire_at.asc()))

    result = await session.execute(query)
    tokens = result.scalars().all()

    if len(tokens) >= limit:
        to_delete_count = len(tokens) - limit + 1
        tokens_to_delete = tokens[:to_delete_count]

        for t in tokens_to_delete:
            await session.delete(t)


def validate_user_otp_state(user_db: UsersModel, otp_in_db: str,
                            otp_try_in_db: int,
                            otp_expire_in_db: datetime.datetime,
                            user_provided_otp: str,
                            email: EmailStr):

    logger.info(
    f"DEBUG user state before validate_user_otp_state: "
    f"{email=}, is_verified={user_db.is_verified}, active={user_db.active}"
)
    if user_db.is_verified or not user_db.active:
        logger.info(f"User {email=} inactivate or inactive")
        raise HTTPException(400, "User already activated or inactive")

    if otp_in_db is None or otp_try_in_db is None:
        logger.info(f'OTP or otp try in user with {email=} == None')
        raise HTTPException(400, "No active otp, resend request to activate")

    if otp_try_in_db <= 0:
        raise HTTPException(400, "You have no more attempts. "
                                 "Please request a new code")

    if otp_expire_in_db < datetime.datetime.now(datetime.timezone.utc):
        raise HTTPException(400, "Your code expired. Please request a new code")

    return user_provided_otp == otp_in_db
