from fastapi import APIRouter, HTTPException
from settings import SessionDep
from users.models import UsersModel
from users.schemas import UserInputSchema, UserOutputSchema
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError


router = APIRouter(tags=["User"], prefix='/users')


@router.post('/', response_model=UserOutputSchema)
async def create_user(user: UserInputSchema, session: SessionDep):
    try:
        new_user = UsersModel(
            email=user.email,
            username=user.username,
            age=user.age,
            password=user.password
        )
        session.add(new_user)
        await session.commit()
        return new_user
    except IntegrityError:
        await session.rollback()
        raise HTTPException(409, "This email has been used")

@router.get('/', response_model=dict[str, list[UserOutputSchema]])
async def get_all_user(session: SessionDep) -> dict:
    query = select(UsersModel)
    res = await session.execute(query)
    return {"Users": res.scalars().all()}


