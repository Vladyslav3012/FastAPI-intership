import datetime
import logging
import uuid
import jwt
from jwt.exceptions import InvalidTokenError
from fastapi import Depends, HTTPException
from fastapi.security import (HTTPAuthorizationCredentials, HTTPBearer)
from pydantic import BaseModel
from app.config import settings, SessionDep
from app.redis_config import check_token_in_blacklist
from app.users.models import RefreshTokenModel
from app.users.schemas import UserOutputSchema


http_bearer = HTTPBearer()
logger = logging.getLogger(__name__)


"""
JWT token
"""

TOKEN_TYPE_FIELD = "type"
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
    to_encode.update(iat=now ,exp=expire)

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
    jwt_payload = {TOKEN_TYPE_FIELD: token_type}
    jwt_payload.update(token_data)
    return encode_jwt(payload=jwt_payload, expire_minutes=expire_minutes)


async def create_token_pair(session: SessionDep, user: UserOutputSchema) -> dict:

    #create refresh token
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
    refresh_token = create_jwt(REFRESH_TOKEN_FIELD, jwt_refresh_payload,
                           settings.auth_jwt.refresh_token_expire_minutes)

    #access token
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

    await session.commit()

    return {
        "access_token": access_token,
        "refresh_token": refresh_token
    }



"""
HELPERS FUNC
"""

async def get_payload_from_token(
        credentials: HTTPAuthorizationCredentials = Depends(http_bearer)
):
    token = credentials.credentials
    try:
        payload = decode_jwt(token=token, )
    except InvalidTokenError as e:
        logger.error(f"Token error: {e}")
        raise HTTPException(401, 'Invalid token')

    jti = payload.get("jti")
    if not jti:
        logger.error("Token has not jti")
        raise HTTPException(401, "Invalid token")

    return payload


#check type token if need to refresh token allow only refresh
async def validate_token_by_type(payload: dict, token_type_to_check: str):
    current_token_type = payload.get('type')
    if current_token_type != token_type_to_check:
        logger.error(f"Token {current_token_type=} error, expected {token_type_to_check}")
        raise HTTPException(401, "Invalid token")

    jti = payload.get('jti')
    check = await check_token_in_blacklist(jti)
    if check:
        logger.error("Token in blacklist")
        raise HTTPException(401, "Invalid token")
