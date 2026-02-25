import datetime
from typing import TYPE_CHECKING

from app.config import Base
from app.config import settings
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import ForeignKey, func, DateTime
from enum import Enum
if TYPE_CHECKING:
    from app.users.models import UsersModel


shortcut = settings.database_shortcut


class CoinModel(Base):
    __tablename__ = "coins"

    id: Mapped[shortcut.intpk]
    name: Mapped[str] = mapped_column(unique=True, index=True)
    current_price: Mapped[float]
    last_updated: Mapped[datetime.datetime] = (
        mapped_column(DateTime(timezone=True),
                      server_default=func.now(),
                      onupdate=func.now()))

    alerts: Mapped[list["AlertModel"]] = relationship(back_populates='coin')


class ConditionsEnum(Enum):
    above = "above"
    below = "below"


class AlertModel(Base):
    __tablename__ = "alerts"

    id: Mapped[shortcut.intpk]
    user_id: Mapped[int] = mapped_column(ForeignKey('users.id', ondelete="CASCADE"))
    coin_id: Mapped[int] = mapped_column(ForeignKey('coins.id', ondelete="CASCADE"))
    target_price: Mapped[float]
    conditions: Mapped[ConditionsEnum]
    is_active: Mapped[bool] = mapped_column(default=True)
    created_at: Mapped[shortcut.created_at]

    coin: Mapped["CoinModel"] = relationship(back_populates='alerts')
    user: Mapped['UsersModel'] = relationship(back_populates='alerts')
