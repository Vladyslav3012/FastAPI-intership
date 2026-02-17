import datetime
import logging
import uuid
import jwt
from jwt.exceptions import InvalidTokenError
from fastapi import Depends, HTTPException
from fastapi.security import (HTTPAuthorizationCredentials, HTTPBearer)
from pydantic import BaseModel
from app.config import settings, SessionDep
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
               expire_at: int,
               private_key: str = settings.auth_jwt.private_key_path.read_text(),
               algorithm: str = settings.auth_jwt.algorithm):

    now = datetime.datetime.now(datetime.UTC)
    expire = now + datetime.timedelta(minutes=expire_at)

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


def create_jwt(token_type: str, token_data: dict, expired_at: int) -> str:
    jwt_payload = {TOKEN_TYPE_FIELD: token_type}
    jwt_payload.update(token_data)
    return encode_jwt(payload=jwt_payload, expire_at=expired_at)


def create_access_token(user: UserOutputSchema) -> str:
    jwt_payload = {
        "sub": user.email,
        "id": user.id,
        "username": user.username,
        "email": user.email
    }
    return create_jwt(ACCESS_TOKEN_FIELD, jwt_payload,
                      settings.auth_jwt.access_token_expire_minutes)


async def create_refresh_token(session: SessionDep, user: UserOutputSchema):
    jti = str(uuid.uuid4())
    jwt_payload = {
        "sub": user.email,
        'jti': jti

    }
    now = datetime.datetime.now(datetime.UTC)
    expire = now + datetime.timedelta(minutes=settings.auth_jwt.refresh_token_expire_minutes)

    db_token = RefreshTokenModel(
        jti=jti,
        expire_at=expire,
        user_id=user.id
    )
    session.add(db_token)
    await session.commit()

    return jti, create_jwt(REFRESH_TOKEN_FIELD, jwt_payload,
                      settings.auth_jwt.refresh_token_expire_minutes)


"""
HELPERS FUNC
"""

def get_payload_from_token(
        credentials: HTTPAuthorizationCredentials = Depends(http_bearer)
):
    token = credentials.credentials
    try:
        payload = decode_jwt(token=token, )
    except InvalidTokenError as e:
        logger.error(f"Token error: {e}")
        raise HTTPException(401, 'Invalid token ')
    return payload


#check type token if need to refresh token allow only refresh
def validate_token_by_type(payload: dict, token_type_to_check: str):
    current_token_type = payload.get('type')
    if current_token_type != token_type_to_check:
        logger.error(f"Token {current_token_type=} error, expected {token_type_to_check}")
        raise HTTPException(401, "Invalid token")
