import logging
import datetime

from fastapi import APIRouter, HTTPException, Depends
from watchfiles import awatch

from settings import SessionDep, settings
from users.models import UsersModel, RefreshTokenModel
from users.schemas import UserInputSchema, UserOutputSchema
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from users.utils import auth_utils, users_utils
from users.utils.auth_utils import create_refresh_token

logger = logging.getLogger(__name__)
router = APIRouter(tags=["Auth"], prefix='/users')


@router.get('/', response_model=dict[str, list[UserOutputSchema]])
async def get_all_user(session: SessionDep) -> dict:
    query = select(UsersModel)
    res = await session.execute(query)
    return {"Users": res.scalars().all()}


@router.post('/sign', response_model=UserOutputSchema)
async def signup_user(user: UserInputSchema, session: SessionDep):
    try:
        new_user = UsersModel(
            email=user.email,
            username=user.username,
            age=user.age,
            password=user.password
        )
        session.add(new_user)
        await session.commit()
        logger.info(f"Success sign up with {user.email=}")
        return new_user
    except IntegrityError:
        logger.error(f"{user.email=} has been used")
        await session.rollback()
        raise HTTPException(409, "This email has been used")



@router.post('/login')
async def login_user(session: SessionDep, user: UserOutputSchema = Depends(users_utils.check_auth_user_in_db)):
    access_token = auth_utils.create_access_token(user)
    _, refresh_token = await auth_utils.create_refresh_token(session, user)

    return auth_utils.TokenInfo(
        access_token=access_token,
        refresh_token=refresh_token,
    )


@router.get('/me')
async def get_active_auth_user(
        user: UserOutputSchema =
        Depends(users_utils.UserGetterFromTokenType(auth_utils.ACCESS_TOKEN_FIELD))
):
    return {
        "email": user.email,
        "username": user.username
    }


@router.post('/refresh', response_model=auth_utils.TokenInfo,
             response_model_exclude_none=True)
async def refresh_jwt(
        session: SessionDep,
        payload: dict = Depends(auth_utils.get_payload_from_token),
        user: UserOutputSchema =
        Depends(users_utils.UserGetterFromTokenType(auth_utils.REFRESH_TOKEN_FIELD)),
):
    jti = payload.get('jti')
    if not jti:
        logger.error("Token has not jti")
        raise HTTPException(401, "Invalid token")

    query = select(RefreshTokenModel).where(RefreshTokenModel.jti == jti)
    result = await session.execute(query)
    token_db = result.scalars().one_or_none()

    if not token_db:
        logger.error(f"Token {jti=} not found in db")
        raise HTTPException(401, "Invalid token")

    await session.delete(token_db)

    access_token = auth_utils.create_access_token(user)
    _, refresh_token = await create_refresh_token(session, user)

    return auth_utils.TokenInfo(
        access_token=access_token,
        refresh_token=refresh_token
    )
