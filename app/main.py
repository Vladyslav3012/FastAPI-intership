from contextlib import asynccontextmanager
import uvicorn
from fastapi import FastAPI
from fastapi.params import Depends

from app.users.utils import auth_utils, users_utils
from app.config import engine, Base, setup_logging
from app.users.schemas import UserOutputSchema
from app.users.views.admin_view import router as users_admin_router
from app.users.views.view_activate import router as user_activate_router
from app.users.views.view_auth import router as user_auth_router


setup_logging()


@asynccontextmanager
async def lifespan(app: FastAPI):
    async with engine.begin() as connections:
        await connections.run_sync(Base.metadata.create_all)
    yield
    await engine.dispose()

app = FastAPI(lifespan=lifespan)
app.include_router(users_admin_router)
app.include_router(user_activate_router)
app.include_router(user_auth_router)


@app.get('/', tags=['Main'], summary='Main root')
def main(
        user: UserOutputSchema =
        Depends(users_utils.UserGetterFromTokenType(auth_utils.ACCESS_TOKEN_FIELD))
) -> str:
    return f"Hello {user.username}"

if __name__ == '__main__':
    uvicorn.run("app.main:app", reload=True, reload_excludes=["*.log"])