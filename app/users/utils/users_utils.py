import logging
from fastapi import Form, HTTPException, Depends
from pydantic import EmailStr
from app.config import SessionDep
from sqlalchemy import select
from app.users.utils import auth_utils
from app.users.models import UsersModel
from app.users.utils.security_password import check_password

logger = logging.getLogger(__name__)

"""
HELPERS FUNC
"""

async def check_auth_user_in_db(
        session: SessionDep,
        email: EmailStr = Form(),
        password: str = Form(min_length=8, max_length=20)
):
    unauth_exception = HTTPException(status_code=401, detail="Invalid email or password")

    query = select(UsersModel).where(UsersModel.email == email)
    res = await session.execute(query)
    user_db = res.scalars().one_or_none()

    if user_db is None:
        logger.error(f"User with {email=} not found")
        raise unauth_exception
    if not check_password(password=password, hashed_password=user_db._hashed_password_):
        logger.error("Password did not match")
        raise unauth_exception
    if not user_db.active:
        logger.error(f"User {email=} inactive")
        raise HTTPException(status_code=403, detail="User inactive")
    return user_db


async def get_current_user_from_payload(payload: dict, session: SessionDep):
    email = payload.get('email')
    if email is None:
        email = payload.get('sub')

    unauth_exception = HTTPException(status_code=401, detail="Invalid email or password")

    query = select(UsersModel).where(UsersModel.email == email)
    res = await session.execute(query)
    user_db = res.scalars().one_or_none()

    if user_db is None:
        logger.error(f"User with {email=} not found")
        raise unauth_exception
    if not user_db.active:
        logger.error(f"{email=} inactive")
        raise HTTPException(status_code=403, detail="User inactive")
    return user_db


class UserGetterFromTokenType:
    def __init__(self, token_type):
        self.token_type = token_type

    async def __call__(self, session: SessionDep,
                       payload: dict = Depends(auth_utils.get_payload_from_token)):
        auth_utils.validate_token_by_type(payload, self.token_type)
        return await get_current_user_from_payload(payload, session)
