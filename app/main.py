from contextlib import asynccontextmanager
import uvicorn
from fastapi import FastAPI
from app.config import engine, Base, setup_logging
from app.users.view import router as users_router

setup_logging()


@asynccontextmanager
async def lifespan(app: FastAPI):
    async with engine.begin() as connections:
        await connections.run_sync(Base.metadata.create_all)
    yield
    await engine.dispose()

app = FastAPI(lifespan=lifespan)
app.include_router(users_router)


@app.get('/', tags=['Main'], summary='Main root')
def main() -> str:
    return "Hello world"

if __name__ == '__main__':
    uvicorn.run("app.main:app", reload=True, reload_excludes=["*.log"])