import datetime
from fastapi import HTTPException
from pydantic import BaseModel, EmailStr, Field, ConfigDict, model_validator


class UserBase(BaseModel):
    email: EmailStr
    username: str = Field(min_length=3, max_length=20)
    age: int | None = Field(default=None, ge=0, le=120)
    model_config = ConfigDict(extra='forbid')


class UserOutputSchema(UserBase):
    created_at: datetime.datetime


class UserInputSchema(UserBase):
    password: str = Field(min_length=8, max_length=20)
    check_password: str = Field(min_length=8, max_length=20)

    @model_validator(mode='after')
    def check_password(self):
        p1 = self.password
        p2 = self.check_password
        if p1 != p2:
            raise HTTPException(422, "Passwords do not match")
        return self


