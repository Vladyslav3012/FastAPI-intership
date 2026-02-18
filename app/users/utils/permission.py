import logging

from fastapi import Depends, HTTPException
from app.users.models import UsersModel
from app.users.utils import users_utils, auth_utils


logger = logging.getLogger(__name__)


class UserCheckRole:
    def __init__(self, allowed_roles: list[str]):
        self.allowed_roles = allowed_roles

    def __call__(self,
                 current_user: UsersModel =
                 Depends(users_utils.UserGetterFromTokenType(auth_utils.ACCESS_TOKEN_FIELD))
                 ):
        if not current_user.is_verified:
            logger.info(f"{current_user.email=} not verified")
            raise HTTPException(403, 'Account not verified')
        if current_user.role.value not in self.allowed_roles:
            logger.info(f"Forbidden {current_user.role.value}"
                        f" not in {self.allowed_roles}")
            raise HTTPException(403, 'Insufficient permission')
        return True


AnyVerified = Depends(UserCheckRole(['admin', 'regular']))
IsAdmin = Depends(UserCheckRole(['admin']))