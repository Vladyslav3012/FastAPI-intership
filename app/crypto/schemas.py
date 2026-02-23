import datetime
from pydantic import BaseModel, Field, ConfigDict
from app.crypto.models import ConditionsEnum

class CoinSchema(BaseModel):
    id: int
    short_name: str
    name: str
    current_price: float
    last_updated: datetime.datetime

    model_config = ConfigDict(from_attributes=True)


class AlertInputSchema(BaseModel):
    coin_short_name: str = Field(min_length=2, max_length=5)
    target_price: float = Field(gt=0.0)
    conditions: ConditionsEnum


class AlertOutputSchema(BaseModel):
    id: int
    target_price: float
    conditions: ConditionsEnum
    is_active: bool
    created_at: datetime.datetime

    coin: CoinSchema

    model_config = ConfigDict(from_attributes=True)