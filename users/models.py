import datetime
import enum

from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import Index, DateTime, ForeignKey
from settings import Base, settings
from users.utils.security_password import hash_password


class UserRoleEnum(enum.Enum):
    admin="admin"
    regular="regular"

class UsersModel(Base):
    __tablename__ = 'users'

    id: Mapped[settings.database_shortcut.intpk]
    email: Mapped[str] = mapped_column(unique=True)
    username: Mapped[str]
    age: Mapped[int | None]
    role: Mapped[UserRoleEnum] = mapped_column(default=UserRoleEnum.regular)
    _hashed_password_: Mapped[bytes]
    created_at: Mapped[settings.database_shortcut.created_at]
    active: Mapped[bool] = mapped_column(default=True)
    refresh_tokens: Mapped[list['RefreshTokenModel']] = relationship(back_populates="user")

    @property
    def password(self):
        return self._hashed_password_

    @password.setter
    def password(self, text_password):
        self._hashed_password_ = hash_password(text_password)

    __table_args__ = (
        Index("email_index", "email"),
    )


class RefreshTokenModel(Base):
    __tablename__ = "refresh_tokens"

    id: Mapped[settings.database_shortcut.intpk]
    jti: Mapped[str] = mapped_column(unique=True, index=True)
    expire_at: Mapped[datetime.datetime] = mapped_column(DateTime(timezone=True))
    user_id: Mapped[int] = mapped_column(ForeignKey('users.id', ondelete="CASCADE"))
    user: Mapped["UsersModel"] = relationship(back_populates='refresh_tokens')

