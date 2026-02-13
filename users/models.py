import enum

from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import Index
from settings import Base, intpk, created_at


class UserRoleEnum(enum.Enum):
    admin="admin"
    regular="regular"

class UsersModel(Base):
    __tablename__ = 'users'

    id: Mapped[intpk]
    email: Mapped[str] = mapped_column(unique=True)
    username: Mapped[str]
    age: Mapped[int | None]
    role: Mapped[UserRoleEnum] = mapped_column(default=UserRoleEnum.regular)
    password: Mapped[str]
    created_at: Mapped[created_at]

    __table_args__ = (
        Index("email_index", "email"),
    )
