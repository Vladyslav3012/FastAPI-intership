import uvicorn
from fastapi import FastAPI


app = FastAPI()


@app.get('/', tags=['Main'], summary='Main root')
def main():
    return "Hello world"


if __name__ == '__main__':
    uvicorn.run("main:app", reload=True)