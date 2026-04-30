import uvicorn
from fastapi import FastAPI

from src.core.config import settings

app = FastAPI(
    title=settings.APP_NAME,
    description="AI Agent for technical and financial real estate analysis.",
    version="0.1.0",
)


@app.get("/", tags=["General"])
async def root():
    """
    Root endpoint providing a welcome message.
    """
    return {"message": f"Welcome to {settings.APP_NAME} API"}


@app.get("/health", tags=["Monitoring"])
async def health_check():
    """
    Health check endpoint for monitoring service status.
    """
    return {"status": "healthy"}


if __name__ == "__main__":
    uvicorn.run(
        "src.main:app", host="127.0.0.1", port=settings.PORT, reload=settings.DEBUG
    )
