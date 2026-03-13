import logging
from fastapi import APIRouter, HTTPException
from fastapi.params import Depends
from sqlalchemy import select
from sqlalchemy.orm import joinedload
from app.config import SessionDep
from app.crypto.models import AlertModel, CoinModel
from app.crypto.schemas import AlertInputSchema, AlertOutputSchema
from app.users.models import UsersModel
from app.users.utils.auth_utils import ACCESS_TOKEN_FIELD
from app.users.utils.users_utils import UserGetterFromTokenType


logger = logging.getLogger(__name__)
router = APIRouter(tags=['Alert'], prefix='/alert')


@router.post('/', response_model=AlertOutputSchema)
async def subscription_to_alert(data: AlertInputSchema,
                                session: SessionDep,
                                user: UsersModel =
                                Depends(UserGetterFromTokenType(ACCESS_TOKEN_FIELD))):
    logger.info(f"Start create alert for {data.coin_name} by {user.email}")

    query = select(CoinModel).where(CoinModel.name == data.coin_name)
    result = await session.execute(query)
    coin: CoinModel = result.scalars().one_or_none()

    if coin is None:
        logger.info(f"Not foun coin with {data.coin_name}")
        raise HTTPException(404, "Coin not found")

    new_alert = AlertModel(
        user_id=user.id,
        coin_id=coin.id,
        target_price=data.target_price,
        conditions=data.conditions
    )

    session.add(new_alert)
    await session.commit()
    logger.info(f"User {user.email} success "
                "create new alert for coin {data.coin_name}")

    new_alert.coin = coin
    return new_alert


@router.get("/", response_model=list[AlertOutputSchema])
async def get_my_alert(session: SessionDep, user: UsersModel =
                       Depends(UserGetterFromTokenType(ACCESS_TOKEN_FIELD))):

    query = (select(AlertModel)
             .options(joinedload(AlertModel.coin))
             .where(AlertModel.user_id == user.id))

    result = await session.execute(query)
    return result.scalars().all()
