import datetime
import random
from datetime import timedelta
from logging.config import dictConfig
from pathlib import Path
from typing import Annotated
from fastapi import Depends
from sqlalchemy import func
from sqlalchemy.ext.asyncio import (create_async_engine, async_sessionmaker,
                                    AsyncSession)
from sqlalchemy.orm import DeclarativeBase, mapped_column
from pydantic import computed_field, PostgresDsn, BaseModel, EmailStr
from pydantic_settings import BaseSettings, SettingsConfigDict


BASE_DIR = Path(__file__).parent.parent

#shortcut for database tables
class DatabaseShortcut:
    intpk = Annotated[int, mapped_column(primary_key=True)]
    created_at = Annotated[datetime.datetime, mapped_column(server_default=func.now())]

#jwt settings
class AuthJWT(BaseModel):
    private_key_path: Path = BASE_DIR / "app" / "certs" / "jwt-private.pem"
    public_key_path: Path = BASE_DIR / "app" / "certs" / "jwt-public.pem"
    algorithm: str = "RS256"
    access_token_expire_minutes: int = 15
    refresh_token_expire_minutes: int = 60 * 24 * 30


class Settings(BaseSettings):
    DB_HOST: str
    DB_PORT: int
    DB_USER: str
    DB_PASS: str
    DB_NAME: str

    TEST_DB_HOST: str
    TEST_DB_PORT: int
    TEST_DB_USER: str
    TEST_DB_PASS: str
    TEST_DB_NAME: str

    REDIS_URL: str = 'redis://localhost:6379/0'

    EMAIL_HOST: str
    EMAIL_HOST_USER: str
    EMAIL_HOST_PASSWORD: str
    EMAIL_PORT: int
    EMAIL_FROM: EmailStr


    model_config = SettingsConfigDict(env_file=BASE_DIR / '.env', extra='ignore')

    # for database connections with, and for pull out keys of .env
    @computed_field
    @property
    def database_url(self) -> str:
        return str(PostgresDsn.build(
            scheme="postgresql+asyncpg",
            username=self.DB_USER,
            password=self.DB_PASS,
            host=self.DB_HOST,
            port=self.DB_PORT,
            path=self.DB_NAME,
        ))

    @computed_field
    @property
    def test_database_url(self) -> str:
        return str(PostgresDsn.build(
            scheme="postgresql+asyncpg",
            username=self.TEST_DB_USER,
            password=self.TEST_DB_PASS,
            host=self.TEST_DB_HOST,
            port=self.TEST_DB_PORT,
            path=self.TEST_DB_NAME,
        ))

    auth_jwt: AuthJWT = AuthJWT()

    database_shortcut: DatabaseShortcut = DatabaseShortcut()


settings = Settings()

"""
DATABASE SETTINGS SESSION
"""

engine = create_async_engine(settings.database_url, echo=True)

new_session = async_sessionmaker(engine, expire_on_commit=False)


async def get_session():
    async with new_session() as session:
        yield session


SessionDep = Annotated[AsyncSession, Depends(get_session)]


class Base(DeclarativeBase):
    pass


"""
LOGGER
"""

LOGGING_CONFIG = {
    "version": 1,
    "disable_existing_loggers": False,

    "formatters": {
        "simple": {
            "format": "[{levelname}] {message}",
            "style": "{",
        },
        "verbose": {
            "format": "[{asctime}] {levelname} {name} ({module}:{funcName}) :: {message}",
            "style": "{",
        },
    },

    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "simple",
        },
        "file": {
            "class": "logging.FileHandler",
            "filename": BASE_DIR / "app.log",
            "formatter": "verbose",
            "encoding": "utf-8",
        },
    },

    "root": {
        "handlers": ["console", "file"],
        "level": "INFO",
    },

    "loggers": {
        "uvicorn": {
            "handlers": ["console", "file"],
            "level": "INFO",
            "propagate": False,
        },
        "uvicorn.access": {
            "handlers": ["console", "file"],
            "level": "INFO",
            "propagate": False,
        },
        "sqlalchemy.engine": {
            "handlers": ["console"],
            "level": "INFO",
            "propagate": False,
        }
    },
}

def setup_logging():
    dictConfig(LOGGING_CONFIG)


"""
CELERY 
"""
broker_url = settings.REDIS_URL
result_backend = settings.REDIS_URL

"""
OTP SETTINGS
"""
otp_expired_minutes = 5
otp_try_conf = 3

def create_otp_arg():
    otp = str(random.randint(10000, 99999))
    now = datetime.datetime.now(datetime.timezone.utc)
    otp_expire = now + timedelta(minutes=otp_expired_minutes)
    otp_try = otp_try_conf
    return otp, otp_expire, otp_try
