import logging
from fastapi import APIRouter
from app.config import SessionDep
from app.users.models import UsersModel
from app.users.schemas import UserOutputSchema
from sqlalchemy import select
from app.users.utils import permission


logger = logging.getLogger(__name__)
router = APIRouter(tags=["Only admin"], prefix='/users')


@router.get('/',
            response_model=dict[str, list[UserOutputSchema]],
            dependencies=[permission.IsAdmin]
)
async def get_all_user(session: SessionDep) -> dict:
    query = select(UsersModel)
    res = await session.execute(query)
    return {"Users": res.scalars().all()}
