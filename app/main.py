import uvicorn
from fastapi import FastAPI
from fastapi.params import Depends
from app.users.utils import auth_utils
from app.config import setup_logging
from app.users.schemas import UserOutputSchema
from app.users.utils.users_utils import UserGetterFromTokenType
from app.users.views.admin_view import router as users_admin_router
from app.users.views.view_activate import router as user_activate_router
from app.users.views.view_auth import router as user_auth_router
from app.users.views.view_reset_password import (router as
                                                 user_password_reset_router)
from app.crypto.view import router as alert_router
from app.parsing.views import router as web_parsing_router


setup_logging()


app = FastAPI()
app.include_router(users_admin_router)
app.include_router(user_activate_router)
app.include_router(user_auth_router)
app.include_router(user_password_reset_router)
app.include_router(alert_router)
app.include_router(web_parsing_router)


@app.get('/', tags=['Main'], summary='Main root')
def main(
        user: UserOutputSchema =
        Depends(UserGetterFromTokenType(auth_utils.ACCESS_TOKEN_FIELD))
) -> str:
    return f"Hello {user.username}"


if __name__ == '__main__':
    uvicorn.run("app.main:app", reload=True, reload_excludes=["*.log"])
