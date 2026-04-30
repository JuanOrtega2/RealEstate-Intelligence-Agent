import uvicorn
from fastapi import FastAPI

from src.core.config import settings

app = FastAPI(title=settings.APP_NAME)


@app.get("/")
async def root():
    return {"message": f"Welcome to {settings.APP_NAME} API"}


@app.get("/health")
async def health_check():
    return {"status": "healthy"}


if __name__ == "__main__":
    uvicorn.run(
        "src.main:app", host="127.0.0.1", port=settings.PORT, reload=settings.DEBUG
    )
