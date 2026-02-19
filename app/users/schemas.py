import datetime
from fastapi import HTTPException
from pydantic import BaseModel, EmailStr, Field, ConfigDict, model_validator


class UserBase(BaseModel):
    email: EmailStr
    username: str = Field(min_length=3, max_length=20)
    age: int | None = Field(default=None, ge=0, le=120)
    model_config = ConfigDict(extra='forbid')


class UserOutputSchema(UserBase):
    id: int
    created_at: datetime.datetime


class UserInputSchema(UserBase):
    password: str = Field(min_length=8, max_length=20)
    check_password: str = Field(min_length=8, max_length=20)

    @model_validator(mode='after')
    def check_password_match(self):
        p1 = self.password
        p2 = self.check_password
        if p1 != p2:
            raise HTTPException(422, "Passwords do not match")
        return self


class UserLogInSchema(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=20)
    model_config = ConfigDict(extra='forbid')


class UserActivateWithOTPSchema(BaseModel):
    email: EmailStr
    otp: str
    model_config = ConfigDict(extra='forbid')


class UserPasswordBaseSchema(BaseModel):
    new_password: str = Field(min_length=8, max_length=20)
    check_new_password: str = Field(min_length=8, max_length=20)

    @model_validator(mode='after')
    def check_password_match(self):
        p1 = self.new_password
        p2 = self.check_new_password
        if p1 != p2:
            raise HTTPException(422, "Passwords do not match")
        return self


class UserResetPasswordSchema(UserPasswordBaseSchema):
    old_password: str = Field(min_length=8, max_length=20)


class UserResetPasswordWithOTPSchema(UserPasswordBaseSchema):
    email: EmailStr
    otp: str


class UserOnlyEmailSchema(BaseModel):
    email: EmailStr
